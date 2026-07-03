from __future__ import annotations

from zipfile import ZipFile

import pandas as pd
import pytest

from uk_wages.clean_region_ashe import (
    _parse_region_age,
    assert_unique_region_keys,
    find_region_weekly_gross_workbook,
)


def test_parse_region_age_normalises_region_and_age_group() -> None:
    assert _parse_region_age("North East, Age 18 to 21") == ("North East", "18-21")
    assert _parse_region_age("not a region row") is None


def test_find_region_weekly_gross_workbook_ignores_cv_files(tmp_path) -> None:
    archive_path = tmp_path / "region.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("Weekly pay - Gross CV.xls", "ignored")
        archive.writestr("nested/Weekly pay - Gross.xlsx", "matched")

    assert find_region_weekly_gross_workbook(archive_path) == "nested/Weekly pay - Gross.xlsx"


def test_assert_unique_region_keys_reports_duplicate_rows() -> None:
    rows = [
        {
            "year": 2025,
            "region": "North East",
            "age_group": "18-21",
            "sex": "All",
            "work_status": "All",
            "earnings_measure": "median_weekly_gross",
        },
        {
            "year": 2025,
            "region": "North East",
            "age_group": "18-21",
            "sex": "All",
            "work_status": "All",
            "earnings_measure": "median_weekly_gross",
        },
    ]

    with pytest.raises(ValueError, match="Duplicate region ASHE rows"):
        assert_unique_region_keys(pd.DataFrame(rows))
