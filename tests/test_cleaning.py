from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from uk_wages.clean_a05 import _derive_16_24
from uk_wages.clean_ashe import assert_unique_ashe_keys, year_from_path
from uk_wages.clean_earn01 import normalise_sector_label
from uk_wages.download import (
    _filename_from_url,
    build_sources_lock,
    download_locked,
    validate_cached_file,
)
from uk_wages.utils import sha256_file, write_json
from uk_wages.utils import clean_numeric_value, normalise_age_label, parse_rolling_period_end


def test_clean_numeric_handles_common_ons_markers() -> None:
    assert clean_numeric_value("1,234.5") == 1234.5
    assert pd.isna(clean_numeric_value("x"))
    assert pd.isna(clean_numeric_value(".."))


def test_ashe_year_age_keys_must_be_unique() -> None:
    df = pd.DataFrame(
        {
            "year": [2025, 2025],
            "age_group": ["18-21", "18-21"],
            "sex": ["All", "All"],
            "work_status": ["All", "All"],
            "earnings_measure": ["median_weekly_gross", "median_weekly_gross"],
        }
    )

    with pytest.raises(ValueError, match="Duplicate ASHE rows"):
        assert_unique_ashe_keys(df)


def test_ashe_year_ignores_unrelated_years_in_parent_paths() -> None:
    path = Path(
        "project-cold-repro-20260702/data/raw/ashe_age/"
        "2025provisional/ashetable62025provisional.zip"
    )

    assert year_from_path(path) == 2025


def test_a05_period_end_date_uses_final_month() -> None:
    assert parse_rolling_period_end("Mar-May 2026") == pd.Timestamp("2026-05-31")


def test_age_labels_are_normalised() -> None:
    assert normalise_age_label("Aged 18-24") == "18-24"
    assert normalise_age_label("60+") == "60+"


def test_a05_derives_16_24_from_component_levels() -> None:
    source = pd.DataFrame(
        {
            "period": ["Jan-Mar 2019", "Jan-Mar 2019"],
            "date": [pd.Timestamp("2019-03-31"), pd.Timestamp("2019-03-31")],
            "age_group": ["16-17", "18-24"],
            "employment_level": [10.0, 90.0],
            "unemployment_level": [2.0, 8.0],
            "activity_level": [12.0, 98.0],
            "inactivity_level": [8.0, 22.0],
        }
    )

    result = _derive_16_24(source)

    assert result.loc[0, "age_group"] == "16-24"
    assert result.loc[0, "employment_level"] == 100.0
    assert round(result.loc[0, "unemployment_rate"], 2) == 9.09
    assert round(result.loc[0, "inactivity_rate"], 2) == 21.43


def test_earn01_sector_labels_remove_footnotes_and_newlines() -> None:
    assert normalise_sector_label("Private Sector 2 3 4 5") == "Private Sector"
    assert normalise_sector_label("Finance and\n Business Services") == "Finance and Business Services"


def test_cached_download_must_match_metadata_hash_and_url(tmp_path) -> None:
    cached = tmp_path / "source.xls"
    cached.write_text("official-data", encoding="utf-8")
    write_json(
        cached.with_suffix(cached.suffix + ".metadata.json"),
        {"source_url": "https://example.com/source.xls", "sha256": sha256_file(cached)},
    )

    validate_cached_file(cached, "https://example.com/source.xls")
    cached.write_text("corrupt-data", encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        validate_cached_file(cached, "https://example.com/source.xls")


def test_download_filename_keeps_xlsx_extension_from_query_url() -> None:
    url = (
        "https://www.ons.gov.uk/file?uri=/employmentandlabourmarket/"
        "rtisajun2026.xlsx"
    )

    assert _filename_from_url(url, "fallback.xlsx") == "rtisajun2026.xlsx"


def test_sources_lock_records_metadata_hash_and_shape(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    source = raw_root / "inflation" / "latest" / "toy.csv"
    source.parent.mkdir(parents=True)
    source.write_text("date,value\n2019-01,100\n2020-01,105\n", encoding="utf-8")
    write_json(
        source.with_suffix(source.suffix + ".metadata.json"),
        {
            "source_key": "inflation",
            "source_name": "Toy source",
            "source_url": "https://example.com/toy.csv",
            "download_date": "2026-07-02T12:00:00+00:00",
            "release_date": "latest",
            "file_name": "toy.csv",
            "sha256": sha256_file(source),
        },
    )

    lock = build_sources_lock(raw_root=raw_root, lock_path=tmp_path / "sources.lock.yaml")

    entry = lock["sources"]["inflation_latest_toy"]
    assert entry["source_key"] == "inflation"
    assert entry["source_url"] == "https://example.com/toy.csv"
    assert entry["downloaded_file"] == "inflation/latest/toy.csv"
    assert entry["release"] == "latest"
    assert entry["sha256"] == sha256_file(source)
    assert entry["downloaded_at"] == "2026-07-02T12:00:00+00:00"
    assert entry["row_count_or_shape"] == "2 rows x 2 columns"


def test_locked_download_rejects_cached_hash_mismatch(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    source = raw_root / "inflation" / "latest" / "toy.csv"
    source.parent.mkdir(parents=True)
    source.write_text("changed", encoding="utf-8")
    expected = tmp_path / "expected.csv"
    expected.write_text("official", encoding="utf-8")
    lock_path = tmp_path / "sources.lock.yaml"
    lock_path.write_text(
        "\n".join(
            [
                "version: 1",
                "sources:",
                "  inflation_latest_toy:",
                "    source_key: inflation",
                "    source_url: https://example.com/toy.csv",
                "    downloaded_file: inflation/latest/toy.csv",
                "    release: latest",
                f"    sha256: {sha256_file(expected)}",
                "    downloaded_at: '2026-07-02T12:00:00+00:00'",
                "    row_count_or_shape: 1 rows x 1 columns",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Locked file hash mismatch"):
        download_locked(lock_path=lock_path, raw_root=raw_root)
