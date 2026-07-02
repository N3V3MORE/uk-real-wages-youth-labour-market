from __future__ import annotations

from pathlib import Path

import pandas as pd

from uk_wages.ashe_composition import build_ashe_composition_outputs


def _ashe_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    values = {
        ("18-21", "All", "All", 2019): 238.9,
        ("18-21", "All", "All", 2025): 300.2,
        ("18-21", "All", "Full-Time", 2019): 390.0,
        ("18-21", "All", "Full-Time", 2025): 520.0,
        ("18-21", "All", "Part-Time", 2019): 120.0,
        ("18-21", "All", "Part-Time", 2025): 145.0,
        ("18-21", "Male", "All", 2019): 250.0,
        ("18-21", "Male", "All", 2025): 315.0,
        ("18-21", "Female", "All", 2019): 225.0,
        ("18-21", "Female", "All", 2025): 285.0,
        ("22-29", "All", "All", 2019): 448.4,
        ("22-29", "All", "All", 2025): 594.3,
        ("22-29", "All", "Full-Time", 2019): 520.0,
        ("22-29", "All", "Full-Time", 2025): 680.0,
        ("22-29", "All", "Part-Time", 2019): 170.0,
        ("22-29", "All", "Part-Time", 2025): 210.0,
        ("22-29", "Male", "All", 2019): 470.0,
        ("22-29", "Male", "All", 2025): 610.0,
        ("22-29", "Female", "All", 2019): 430.0,
        ("22-29", "Female", "All", 2025): 570.0,
        ("30-39", "All", "All", 2019): 537.7,
        ("30-39", "All", "All", 2025): 716.0,
        ("30-39", "All", "Full-Time", 2019): 610.0,
        ("30-39", "All", "Full-Time", 2025): 790.0,
        ("30-39", "All", "Part-Time", 2019): 200.0,
        ("30-39", "All", "Part-Time", 2025): 245.0,
        ("30-39", "Male", "All", 2019): 560.0,
        ("30-39", "Male", "All", 2025): 740.0,
        ("30-39", "Female", "All", 2019): 510.0,
        ("30-39", "Female", "All", 2025): 690.0,
    }
    for (age_group, sex, work_status, year), value in values.items():
        rows.append(
            {
                "year": year,
                "age_group": age_group,
                "sex": sex,
                "work_status": work_status,
                "earnings_measure": "median_weekly_gross",
                "nominal_earnings": value,
                "unit": "GBP per week",
                "source_file": f"ashe{year}.zip",
                "source_release": f"{year}release",
            }
        )
    return rows


def test_composition_report_documents_available_and_missing_fields(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame(_ashe_rows()).to_parquet(processed / "ashe_age_annual.parquet", index=False)
    pd.DataFrame(
        [
            {
                "year": 2019,
                "age_group": "18-21",
                "total_paid_hours": 29.9,
                "hours_index_2019_100": 100.0,
            },
            {
                "year": 2025,
                "age_group": "18-21",
                "total_paid_hours": 23.8,
                "hours_index_2019_100": 79.6,
            },
            {
                "year": 2019,
                "age_group": "22-29",
                "total_paid_hours": 37.5,
                "hours_index_2019_100": 100.0,
            },
            {
                "year": 2025,
                "age_group": "22-29",
                "total_paid_hours": 37.3,
                "hours_index_2019_100": 99.5,
            },
            {
                "year": 2019,
                "age_group": "30-39",
                "total_paid_hours": 37.4,
                "hours_index_2019_100": 100.0,
            },
            {
                "year": 2025,
                "age_group": "30-39",
                "total_paid_hours": 37.4,
                "hours_index_2019_100": 100.0,
            },
        ]
    ).to_parquet(processed / "ashe_age_hours_decomposition.parquet", index=False)

    composition, summary = build_ashe_composition_outputs(
        processed_root=processed,
        output_root=tmp_path / "outputs",
        raw_root=None,
    )

    assert {"18-21", "22-29", "30-39"}.issubset(set(summary["age_group"]))
    assert not composition.empty
    assert not summary["job_count_proxy_available"].any()
    assert "full_time_weekly_pct_change" in summary.columns
    text = (tmp_path / "outputs" / "evidence" / "ashe_composition_audit.md").read_text(
        encoding="utf-8"
    )
    assert "employee job counts or sample-size proxies were not available" in text
    assert "not causal" in text
