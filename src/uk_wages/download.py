from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from pathlib import Path, PurePosixPath, PureWindowsPath
from zipfile import ZipFile
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .utils import ensure_dir, load_yaml, project_path, sha256_file, slugify, write_json


CONFIG_PATH = project_path("config", "sources.yaml")
LOCK_PATH = project_path("config", "sources.lock.yaml")
RAW_ROOT = project_path("data", "raw")
USER_AGENT = "uk-real-wages-youth-labour-market/2.0.0 (+https://www.ons.gov.uk)"


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _request_with_rate_limit_retry(
    session: requests.Session,
    url: str,
    *,
    source_key: str,
) -> requests.Response:
    response = None
    for attempt in range(5):
        response = session.get(url, timeout=60)
        if response.status_code != 429:
            break
        retry_after = response.headers.get("Retry-After")
        retry_after_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 0
        delay = max(retry_after_seconds, min(120, 20 * (attempt + 1)))
        print(f"ONS rate limit for {source_key}; waiting {delay}s before retry.")
        time.sleep(delay)
    assert response is not None
    return response


def _filename_from_url(url: str, fallback: str) -> str:
    parsed = urlparse(url)
    query_match = re.search(r"/([^/?]+\.(?:csv|xlsx|xls|zip))", parsed.query)
    if query_match:
        return query_match.group(1)
    name = Path(parsed.path).name
    return name or fallback


def _download_file(
    session: requests.Session,
    url: str,
    destination: Path,
    *,
    force: bool,
    source_key: str,
    source_name: str,
    release: str,
) -> Path:
    ensure_dir(destination.parent)
    metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")
    if destination.exists() and not force:
        validate_cached_file(destination, url)
        return destination

    response = _request_with_rate_limit_retry(session, url, source_key=source_key)
    if response.status_code == 404 and "/current/" in url:
        raise FileNotFoundError(
            f"ONS current alias returned 404 for {source_key}. Use a concrete edition URL."
        )
    response.raise_for_status()
    destination.write_bytes(response.content)
    write_json(
        metadata_path,
        {
            "source_key": source_key,
            "source_name": source_name,
            "source_url": url,
            "download_date": dt.datetime.now(dt.UTC).isoformat(),
            "release_date": release,
            "file_name": destination.name,
            "sha256": sha256_file(destination),
        },
    )
    return destination


def validate_cached_file(destination: str | Path, expected_url: str) -> None:
    destination = Path(destination)
    metadata_path = destination.with_suffix(destination.suffix + ".metadata.json")
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Cached file exists without metadata: {destination}. Re-run with --force."
        )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    actual_hash = sha256_file(destination)
    expected_hash = metadata.get("sha256")
    if expected_hash != actual_hash:
        raise ValueError(f"Cached file hash mismatch for {destination}. Re-run with --force.")
    if metadata.get("source_url") != expected_url:
        raise ValueError(f"Cached file URL does not match config for {destination}. Re-run with --force.")


def _source_path_from_metadata(metadata_path: Path) -> Path:
    suffix = ".metadata.json"
    if not metadata_path.name.endswith(suffix):
        raise ValueError(f"Unexpected metadata file name: {metadata_path}")
    return metadata_path.with_name(metadata_path.name[: -len(suffix)])


def _shape_summary(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path)
        return f"{len(frame)} rows x {len(frame.columns)} columns"
    if suffix in {".xls", ".xlsx"}:
        workbook = pd.ExcelFile(path)
        first = pd.read_excel(workbook, sheet_name=workbook.sheet_names[0], header=None)
        return (
            f"{len(workbook.sheet_names)} sheets; "
            f"first sheet {len(first)} rows x {len(first.columns)} columns"
        )
    if suffix == ".zip":
        with ZipFile(path) as archive:
            return f"{len(archive.namelist())} files in zip"
    if suffix in {".html", ".htm"}:
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        return f"{len(soup.find_all('table'))} html tables"
    return f"{path.stat().st_size} bytes"


def build_sources_lock(
    *,
    raw_root: str | Path = RAW_ROOT,
    lock_path: str | Path = LOCK_PATH,
) -> dict[str, object]:
    raw_root = Path(raw_root)
    sources: dict[str, dict[str, object]] = {}
    for metadata_path in sorted(raw_root.glob("**/*.metadata.json")):
        source_path = _source_path_from_metadata(metadata_path)
        if not source_path.exists():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        source_key = str(metadata["source_key"])
        release = str(metadata.get("release_date") or metadata.get("release") or "")
        entry_key = slugify(f"{source_key}_{release}_{source_path.stem}")
        sources[entry_key] = {
            "source_key": source_key,
            "source_url": metadata["source_url"],
            "downloaded_file": source_path.relative_to(raw_root).as_posix(),
            "release": release,
            "sha256": sha256_file(source_path),
            "downloaded_at": metadata.get("download_date", ""),
            "row_count_or_shape": _shape_summary(source_path),
        }
    lock = {
        "version": 1,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "sources": sources,
    }
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to write the source lockfile.") from exc

    lock_path = Path(lock_path)
    ensure_dir(lock_path.parent)
    with lock_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(lock, handle, sort_keys=False)
    return lock


def _load_sources_lock(lock_path: str | Path) -> dict[str, object]:
    lock = load_yaml(lock_path)
    sources = lock.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError(f"No locked sources found in {lock_path}.")
    return lock


def _verify_locked_hash(path: Path, expected_hash: str) -> None:
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise ValueError(
            f"Locked file hash mismatch for {path}: expected {expected_hash}, got {actual_hash}."
        )


def verify_locked_sources(
    *,
    lock_path: str | Path = LOCK_PATH,
    raw_root: str | Path = RAW_ROOT,
) -> list[Path]:
    """Verify every locked raw source locally without downloading anything."""
    lock = _load_sources_lock(lock_path)
    sources = lock["sources"]
    assert isinstance(sources, dict)
    resolved_raw_root = Path(raw_root).resolve()
    verified: list[Path] = []
    for entry_name, entry in sources.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid locked source entry: {entry_name}")
        downloaded_file = entry.get("downloaded_file")
        if not isinstance(downloaded_file, str) or not downloaded_file.strip():
            raise ValueError(f"Invalid downloaded_file for locked source: {entry_name}")
        posix_path = PurePosixPath(downloaded_file)
        windows_path = PureWindowsPath(downloaded_file)
        if (
            posix_path.is_absolute()
            or windows_path.is_absolute()
            or bool(windows_path.drive)
            or ".." in posix_path.parts
            or ".." in windows_path.parts
        ):
            raise ValueError(
                f"Locked downloaded_file must stay under the raw root: {downloaded_file}"
            )
        destination = (resolved_raw_root / downloaded_file).resolve()
        if not destination.is_relative_to(resolved_raw_root):
            raise ValueError(
                f"Locked downloaded_file must stay under the raw root: {downloaded_file}"
            )
        if not destination.is_file():
            raise FileNotFoundError(f"Missing locked raw source: {downloaded_file}")
        expected_hash = entry.get("sha256")
        if not isinstance(expected_hash, str) or not expected_hash:
            raise ValueError(f"Invalid sha256 for locked source: {entry_name}")
        _verify_locked_hash(destination, expected_hash)
        verified.append(destination)
    return verified


def download_locked(
    *,
    lock_path: str | Path = LOCK_PATH,
    raw_root: str | Path = RAW_ROOT,
    force: bool = False,
    only: list[str] | None = None,
) -> list[Path]:
    lock = _load_sources_lock(lock_path)
    sources = lock["sources"]
    assert isinstance(sources, dict)
    selected = set(only or [])
    session = _session()
    outputs: list[Path] = []
    for entry_name, entry in sources.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid locked source entry: {entry_name}")
        source_key = str(entry["source_key"])
        if selected and source_key not in selected and entry_name not in selected:
            continue
        destination = Path(raw_root) / str(entry["downloaded_file"])
        expected_hash = str(entry["sha256"])
        if destination.exists() and not force:
            _verify_locked_hash(destination, expected_hash)
            outputs.append(destination)
            continue
        ensure_dir(destination.parent)
        response = _request_with_rate_limit_retry(
            session, str(entry["source_url"]), source_key=source_key
        )
        response.raise_for_status()
        destination.write_bytes(response.content)
        _verify_locked_hash(destination, expected_hash)
        write_json(
            destination.with_suffix(destination.suffix + ".metadata.json"),
            {
                "source_key": source_key,
                "source_name": source_key,
                "source_url": entry["source_url"],
                "download_date": dt.datetime.now(dt.UTC).isoformat(),
                "release_date": entry.get("release", ""),
                "file_name": destination.name,
                "sha256": expected_hash,
            },
        )
        outputs.append(destination)
    return outputs


def _download_inflation(session: requests.Session, config: dict, *, force: bool) -> list[Path]:
    outputs: list[Path] = []
    source = config["inflation"]
    for series in source["series"]:
        release = "latest"
        filename = f"mm23_{series['name']}_{series['series_id'].lower()}.csv"
        destination = RAW_ROOT / "inflation" / release / filename
        outputs.append(
            _download_file(
                session,
                series["url"],
                destination,
                force=force,
                source_key="inflation",
                source_name=source["source_name"],
                release=release,
            )
        )
    return outputs


def _download_edition_series(
    session: requests.Session,
    source_key: str,
    source: dict,
    *,
    force: bool,
) -> list[Path]:
    outputs: list[Path] = []
    for edition in source["editions"]:
        url = edition.get("download_url")
        if not url:
            url = find_edition_file_url(session, source["page_url"], edition["edition"])
        filename = _filename_from_url(url, fallback=f"{source_key}_{edition['edition']}.zip")
        destination = RAW_ROOT / source_key / edition["edition"] / filename
        outputs.append(
            _download_file(
                session,
                url,
                destination,
                force=force,
                source_key=source_key,
                source_name=source["source_name"],
                release=edition["edition"],
            )
        )
    return outputs


def find_edition_file_url(session: requests.Session, page_url: str, edition: str) -> str:
    response = session.get(page_url, timeout=60)
    response.raise_for_status()
    matches = re.findall(r"/file\?uri=[^\"<> ]+\.zip", response.text)
    for href in matches:
        if f"/{edition}/" in href:
            return f"https://www.ons.gov.uk{href}"
    raise RuntimeError(f"No ONS zip link for edition {edition} on {page_url}")


def discover_latest_file_url(session: requests.Session, page_url: str, extension: str) -> str:
    response = session.get(page_url, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    hrefs: list[str] = []
    for anchor in soup.find_all("a"):
        href = anchor.get("href") or ""
        if "/file?uri=" in href and href.lower().endswith(extension.lower()):
            hrefs.append(href)
    if not hrefs:
        raise RuntimeError(f"No {extension} download link found on {page_url}")

    concrete = [href for href in hrefs if "/current/" not in href]
    href = concrete[0] if concrete else hrefs[0]
    return href if href.startswith("http") else f"https://www.ons.gov.uk{href}"


def _download_single_workbook(
    session: requests.Session,
    source_key: str,
    source: dict,
    *,
    force: bool,
) -> list[Path]:
    url = source.get("download_url")
    if not url:
        url = discover_latest_file_url(session, source["page_url"], ".xls")
    filename = _filename_from_url(url, fallback=f"{source_key}.xls")
    release = "current"
    destination = RAW_ROOT / source_key / release / filename
    return [
        _download_file(
            session,
            url,
            destination,
            force=force,
            source_key=source_key,
            source_name=source["source_name"],
            release=release,
        )
    ]


def _download_minimum_wage_document(
    session: requests.Session,
    source_key: str,
    source: dict,
    *,
    force: bool,
) -> list[Path]:
    url = source["download_url"]
    destination = RAW_ROOT / source_key / "current" / f"{source_key}.json"
    return [
        _download_file(
            session,
            url,
            destination,
            force=force,
            source_key=source_key,
            source_name=source["source_name"],
            release="current",
        )
    ]


def download_all(force: bool = False, only: list[str] | None = None) -> list[Path]:
    config = load_yaml(CONFIG_PATH)
    selected = set(
        only
        or ["inflation", "ashe_age", "ashe_region_age", "a05", "earn01", "rti", "minimum_wage"]
    )
    session = _session()
    outputs: list[Path] = []

    if "inflation" in selected:
        outputs.extend(_download_inflation(session, config, force=force))
    if "ashe_age" in selected:
        outputs.extend(_download_edition_series(session, "ashe_age", config["ashe_age"], force=force))
    if "ashe_region_age" in selected:
        outputs.extend(
            _download_edition_series(
                session, "ashe_region_age", config["ashe_region_age"], force=force
            )
        )
    if "a05" in selected:
        outputs.extend(_download_single_workbook(session, "a05", config["a05"], force=force))
    if "earn01" in selected:
        outputs.extend(_download_single_workbook(session, "earn01", config["earn01"], force=force))
    if "rti" in selected:
        outputs.extend(_download_single_workbook(session, "rti", config["rti"], force=force))
    if "minimum_wage" in selected:
        outputs.extend(
            _download_minimum_wage_document(
                session, "minimum_wage", config["minimum_wage"], force=force
            )
        )

    return outputs


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download and cache official ONS source files.")
    parser.add_argument("--force", action="store_true", help="Overwrite cached raw files.")
    parser.add_argument(
        "--locked",
        action="store_true",
        help="Download only URLs from config/sources.lock.yaml and verify locked SHA256 hashes.",
    )
    parser.add_argument(
        "--write-lock",
        action="store_true",
        help="Write config/sources.lock.yaml from the currently downloaded source metadata.",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=[
            "inflation",
            "ashe_age",
            "ashe_region_age",
            "a05",
            "earn01",
            "rti",
            "minimum_wage",
        ],
        help="Optional subset of sources to download.",
    )
    args = parser.parse_args(argv)
    if args.write_lock:
        lock = build_sources_lock()
        print(LOCK_PATH.relative_to(project_path()))
        print(f"locked_sources={len(lock['sources'])}")
        return
    if args.locked:
        outputs = download_locked(force=args.force, only=args.sources)
    else:
        outputs = download_all(force=args.force, only=args.sources)
    for path in outputs:
        print(path.relative_to(project_path()))


if __name__ == "__main__":
    main()
