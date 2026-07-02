from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .utils import ensure_dir, load_yaml, project_path, sha256_file, slugify, write_json


CONFIG_PATH = project_path("config", "sources.yaml")
RAW_ROOT = project_path("data", "raw")
USER_AGENT = "uk-real-wages-youth-labour-market/0.1 (+https://www.ons.gov.uk)"


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


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


def _download_html_page(
    session: requests.Session,
    source_key: str,
    source: dict,
    *,
    force: bool,
) -> list[Path]:
    url = source["download_url"]
    destination = RAW_ROOT / source_key / "current" / f"{source_key}.html"
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
            _download_html_page(session, "minimum_wage", config["minimum_wage"], force=force)
        )

    return outputs


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download and cache official ONS source files.")
    parser.add_argument("--force", action="store_true", help="Overwrite cached raw files.")
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
    outputs = download_all(force=args.force, only=args.sources)
    for path in outputs:
        print(path.relative_to(project_path()))


if __name__ == "__main__":
    main()
