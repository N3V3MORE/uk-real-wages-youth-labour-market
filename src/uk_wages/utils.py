from __future__ import annotations

import calendar
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def project_path(*parts: str | Path) -> Path:
    return PROJECT_ROOT.joinpath(*map(Path, parts))


def ensure_dir(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def load_yaml(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read project config.") from exc

    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}.")
    return data


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "value"


def clean_numeric_value(value: Any) -> float | pd.NA:
    if pd.isna(value):
        return pd.NA
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "x", "..", ":", "-", "na", "n/a"}:
        return pd.NA
    text = text.replace(",", "").replace("GBP", "").replace("£", "").replace("%", "")
    text = re.sub(r"^\((.*)\)$", r"-\1", text)
    try:
        return float(text)
    except ValueError:
        return pd.NA


def normalise_age_label(value: Any) -> str:
    text = str(value).strip()
    text = re.sub(r"^Aged?\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAge\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<=\d)[a-z]$", "", text)
    text = text.replace(" and over", "+")
    text = text.replace(" to ", "-")
    text = text.replace(" ", "")
    return text


def parse_ons_month_period(period: Any) -> pd.Timestamp:
    if isinstance(period, (dt.date, dt.datetime, pd.Timestamp)):
        return pd.Timestamp(period).replace(day=1)

    text = str(period).strip().upper()
    match = re.fullmatch(r"(\d{4})\s+([A-Z]{3})", text)
    if not match:
        raise ValueError(f"Cannot parse ONS monthly period: {period!r}")
    year = int(match.group(1))
    month = MONTHS[match.group(2)]
    return pd.Timestamp(year=year, month=month, day=1)


def parse_rolling_period_end(period: Any) -> pd.Timestamp:
    if isinstance(period, (dt.date, dt.datetime, pd.Timestamp)):
        return pd.Timestamp(period)

    text = str(period).strip()
    match = re.fullmatch(r"([A-Za-z]{3})-([A-Za-z]{3})\s+(\d{4})", text)
    if not match:
        raise ValueError(f"Cannot parse rolling period: {period!r}")
    end_month = MONTHS[match.group(2).upper()]
    year = int(match.group(3))
    end_day = calendar.monthrange(year, end_month)[1]
    return pd.Timestamp(year=year, month=end_month, day=end_day)


def latest_matching_file(root: str | Path, patterns: Iterable[str]) -> Path:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(Path(root).glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files found under {root} matching {list(patterns)}")
    return max(files, key=lambda path: path.stat().st_mtime)


def single_matching_file(root: str | Path, patterns: Iterable[str]) -> Path:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(Path(root).glob(pattern))
    files = sorted(files)
    if not files:
        raise FileNotFoundError(f"No files found under {root} matching {list(patterns)}")
    current_files = [path for path in files if "current" in path.parts]
    candidates = current_files or files
    if len(candidates) != 1:
        raise ValueError(
            f"Expected exactly one source file under {root}; found {[str(path) for path in candidates]}"
        )
    return candidates[0]


def write_dataframe(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    if path.suffix == ".csv":
        df.to_csv(path, index=False)
        return
    if path.suffix == ".parquet":
        df.to_parquet(path, index=False)
        return
    raise ValueError(f"Unsupported dataframe output: {path}")
