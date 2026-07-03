from __future__ import annotations

from pathlib import Path

import pandas as pd

from uk_wages.triangulation import build_triangulation_report


def test_triangulation_report_compares_latest_overlapping_ashe_and_earn01(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    output = tmp_path / "outputs"

    pd.DataFrame(
        {
            "year": [2019, 2025],
            "age_group": ["18-21", "18-21"],
            "real_earnings_index_2019_100": [100.0, 98.5],
        }
    ).to_parquet(processed / "age_group_real_earnings.parquet", index=False)
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "sector": ["Whole Economy", "Whole Economy"],
            "real_regular_pay_index_jan2019_100": [105.0, 107.0],
            "real_total_pay_index_jan2019_100": [106.0, 108.0],
        }
    ).to_parquet(processed / "awe_real_monthly.parquet", index=False)

    path = build_triangulation_report(processed_root=processed, output_root=output)
    text = path.read_text(encoding="utf-8")

    assert "Latest overlapping year: 2025." in text
    assert "ASHE age-group average real index: 98.50." in text
    assert "EARN01 real regular pay annual average index: 106.00." in text
    assert "EARN01 is not age-specific" in text
