from __future__ import annotations

from pathlib import Path

import pandas as pd

from uk_wages.analysis import compute_real_earnings_by_age, summarise_age_changes, write_policy_brief
from uk_wages.ashe_decomposition import compute_decomposition, write_decomposition_report
from uk_wages.rti_triangulation import build_rti_triangulation_report
from uk_wages.triangulation import build_triangulation_report


def test_triangulation_keeps_ashe_age_groups_and_quantifies_disagreement(
    tmp_path: Path,
) -> None:
    processed = tmp_path / "processed"
    output = tmp_path / "outputs"
    processed.mkdir()
    ashe = pd.DataFrame(
        [
            {"year": 2019, "age_group": "18-21", "real_earnings_index_2019_100": 100.0},
            {"year": 2020, "age_group": "18-21", "real_earnings_index_2019_100": 97.0},
            {"year": 2021, "age_group": "18-21", "real_earnings_index_2019_100": 101.0},
            {"year": 2019, "age_group": "22-29", "real_earnings_index_2019_100": 100.0},
            {"year": 2020, "age_group": "22-29", "real_earnings_index_2019_100": 103.0},
            {"year": 2021, "age_group": "22-29", "real_earnings_index_2019_100": 106.0},
        ]
    )
    awe = pd.DataFrame(
        [
            {
                "date": pd.Timestamp(f"{year}-04-01"),
                "sector": "Whole Economy",
                "real_regular_pay_index_jan2019_100": regular,
                "real_total_pay_index_jan2019_100": total,
            }
            for year, regular, total in [
                (2019, 100.0, 100.0),
                (2020, 102.0, 101.0),
                (2021, 104.0, 103.0),
            ]
        ]
    )
    ashe.to_parquet(processed / "age_group_real_earnings.parquet", index=False)
    awe.to_parquet(processed / "awe_real_monthly.parquet", index=False)

    path = build_triangulation_report(processed_root=processed, output_root=output)

    metrics = pd.read_csv(output / "evidence" / "triangulation_metrics.csv")
    summary = pd.read_csv(output / "evidence" / "triangulation_summary.csv")
    text = path.read_text(encoding="utf-8")

    assert set(metrics["age_group"]) == {"18-21", "22-29"}
    assert "ASHE age-group average" not in text
    assert "Directional concordance" in text
    youngest = summary[summary["age_group"].eq("18-21")].iloc[0]
    assert youngest["regular_direction_concordance"] == 0.5
    assert youngest["latest_regular_level_gap_pp"] == -3.0


def test_triangulation_yoy_requires_adjacent_years(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    output = tmp_path / "outputs"
    processed.mkdir()
    pd.DataFrame(
        [
            {"year": 2019, "age_group": "18-21", "real_earnings_index_2019_100": 100.0},
            {"year": 2021, "age_group": "18-21", "real_earnings_index_2019_100": 104.0},
        ]
    ).to_parquet(processed / "age_group_real_earnings.parquet", index=False)
    pd.DataFrame(
        [
            {
                "date": pd.Timestamp(f"{year}-04-01"),
                "sector": "Whole Economy",
                "real_regular_pay_index_jan2019_100": index,
                "real_total_pay_index_jan2019_100": index,
            }
            for year, index in [(2019, 100.0), (2021, 102.0)]
        ]
    ).to_parquet(processed / "awe_real_monthly.parquet", index=False)

    build_triangulation_report(processed_root=processed, output_root=output)

    summary = pd.read_csv(output / "evidence" / "triangulation_summary.csv")
    row = summary.iloc[0]
    assert row["yoy_comparison_years"] == 0
    assert pd.isna(row["regular_direction_concordance"])


def test_rti_triangulation_aligns_april_overlap_and_reports_concordance(
    tmp_path: Path,
) -> None:
    output = tmp_path / "outputs"
    tables = output / "tables"
    processed = tmp_path / "data" / "processed"
    tables.mkdir(parents=True)
    processed.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "age_group": "18-24",
                "latest_available_month": "2021-04-01",
                "real_pay_pct_change_since_jan2019": 6.0,
            }
        ]
    ).to_csv(tables / "rti_age_real_pay_change.csv", index=False)
    pd.DataFrame(
        [
            {"age_group": "18-21", "latest_year": 2021, "real_pct_change": 1.0},
            {"age_group": "22-29", "latest_year": 2021, "real_pct_change": 6.0},
        ]
    ).to_csv(tables / "age_group_real_earnings_change.csv", index=False)
    pd.DataFrame(
        [
            {
                "date": pd.Timestamp(f"{year}-04-01"),
                "age_group": "18-24",
                "real_pay_index_jan2019_100": index,
            }
            for year, index in [(2019, 100.0), (2020, 104.0), (2021, 108.0)]
        ]
    ).to_parquet(processed / "rti_age_real_monthly.parquet", index=False)
    pd.DataFrame(
        [
            {"year": 2019, "age_group": "18-21", "real_earnings_index_2019_100": 100.0},
            {"year": 2020, "age_group": "18-21", "real_earnings_index_2019_100": 98.0},
            {"year": 2021, "age_group": "18-21", "real_earnings_index_2019_100": 101.0},
            {"year": 2019, "age_group": "22-29", "real_earnings_index_2019_100": 100.0},
            {"year": 2020, "age_group": "22-29", "real_earnings_index_2019_100": 104.0},
            {"year": 2021, "age_group": "22-29", "real_earnings_index_2019_100": 106.0},
        ]
    ).to_parquet(processed / "age_group_real_earnings.parquet", index=False)
    mapping = tmp_path / "age_group_mapping.yaml"
    mapping.write_text(
        "\n".join(
            [
                "rti_to_ashe_comparison:",
                '  - rti_age_group: "18-24"',
                '    closest_ashe_groups: ["18-21", "22-29"]',
                '    comparison_quality: "imperfect"',
                '    note: "RTI 18-24 overlaps two ASHE age groups."',
            ]
        ),
        encoding="utf-8",
    )

    path = build_rti_triangulation_report(output_root=output, mapping_config=mapping)

    comparison = pd.read_csv(output / "evidence" / "rti_ashe_annual_comparison.csv")
    text = path.read_text(encoding="utf-8")

    assert set(comparison["ashe_age_group"]) == {"18-21", "22-29"}
    assert comparison["comparison_month"].eq("April").all()
    assert "April-to-April overlap" in text
    assert "Directional concordance" in text
    youngest = comparison[comparison["ashe_age_group"].eq("18-21")]
    assert list(youngest["direction_match"]) == [False, True]


def test_rti_triangulation_yoy_requires_adjacent_april_years(tmp_path: Path) -> None:
    output = tmp_path / "outputs"
    tables = output / "tables"
    processed = tmp_path / "data" / "processed"
    tables.mkdir(parents=True)
    processed.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "age_group": "18-24",
                "latest_available_month": "2021-04-01",
                "real_pay_pct_change_since_jan2019": 6.0,
            }
        ]
    ).to_csv(tables / "rti_age_real_pay_change.csv", index=False)
    pd.DataFrame(
        [{"age_group": "18-21", "latest_year": 2021, "real_pct_change": 4.0}]
    ).to_csv(tables / "age_group_real_earnings_change.csv", index=False)
    pd.DataFrame(
        [
            {
                "date": pd.Timestamp(f"{year}-04-01"),
                "age_group": "18-24",
                "real_pay_index_jan2019_100": index,
            }
            for year, index in [(2019, 100.0), (2021, 106.0)]
        ]
    ).to_parquet(processed / "rti_age_real_monthly.parquet", index=False)
    pd.DataFrame(
        [
            {"year": 2019, "age_group": "18-21", "real_earnings_index_2019_100": 100.0},
            {"year": 2021, "age_group": "18-21", "real_earnings_index_2019_100": 104.0},
        ]
    ).to_parquet(processed / "age_group_real_earnings.parquet", index=False)
    mapping = tmp_path / "age_group_mapping.yaml"
    mapping.write_text(
        "\n".join(
            [
                "rti_to_ashe_comparison:",
                '  - rti_age_group: "18-24"',
                '    closest_ashe_groups: ["18-21"]',
                '    comparison_quality: "imperfect"',
                '    note: "RTI 18-24 overlaps ASHE 18-21."',
            ]
        ),
        encoding="utf-8",
    )

    build_rti_triangulation_report(output_root=output, mapping_config=mapping)

    assert not (output / "evidence" / "rti_ashe_annual_comparison.csv").exists()


def test_ashe_change_summary_uses_source_cv_bands_when_available() -> None:
    ashe = pd.DataFrame(
        [
            {
                "year": 2019,
                "age_group": "18-21",
                "sex": "All",
                "work_status": "All",
                "earnings_measure": "median_weekly_gross",
                "nominal_earnings": 100.0,
            },
            {
                "year": 2025,
                "age_group": "18-21",
                "sex": "All",
                "work_status": "All",
                "earnings_measure": "median_weekly_gross",
                "nominal_earnings": 120.0,
            },
        ]
    )
    inflation = pd.DataFrame(
        [
            {"year": 2019, "cpih_index_2019_100": 100.0, "cpi_index_2019_100": 100.0},
            {"year": 2025, "cpih_index_2019_100": 125.0, "cpi_index_2019_100": 125.0},
        ]
    )
    quality_flags = pd.DataFrame(
        [
            {
                "year": 2019,
                "source_family": "ashe_age",
                "region": "United Kingdom",
                "age_group": "18-21",
                "sex": "All",
                "work_status": "All",
                "measure": "weekly_gross",
                "estimate": "median",
                "cv_percent": 1.8,
            },
            {
                "year": 2025,
                "source_family": "ashe_age",
                "region": "United Kingdom",
                "age_group": "18-21",
                "sex": "All",
                "work_status": "All",
                "measure": "weekly_gross",
                "estimate": "median",
                "cv_percent": 2.0,
            },
        ]
    )

    real = compute_real_earnings_by_age(ashe, inflation)
    summary = summarise_age_changes(real, quality_flags=quality_flags)
    row = summary.iloc[0]

    assert row["baseline_cv_percent"] == 1.8
    assert row["latest_cv_percent"] == 2.0
    assert row["approx_two_cv_margin_pp"] == 5.38
    assert row["approx_two_cv_lower_pct_change"] == -9.38
    assert row["approx_two_cv_upper_pct_change"] == 1.38
    assert bool(row["approx_two_cv_band_includes_zero"]) is True


def test_decomposition_adds_year_by_year_residual_diagnostics(tmp_path: Path) -> None:
    raw = pd.DataFrame(
        [
            {
                "year": year,
                "age_group": "18-21",
                "measure": measure,
                "median_value": value,
                "source_file": f"{year}.zip",
                "source_release": str(year),
            }
            for year, values in {
                2019: {
                    "weekly_gross": 100.0,
                    "hourly_gross": 10.0,
                    "total_paid_hours": 10.0,
                },
                2020: {
                    "weekly_gross": 103.0,
                    "hourly_gross": 11.0,
                    "total_paid_hours": 9.5,
                },
                2025: {
                    "weekly_gross": 121.0,
                    "hourly_gross": 11.0,
                    "total_paid_hours": 11.0,
                },
            }.items()
            for measure, value in values.items()
        ]
    )
    inflation = pd.DataFrame(
        [
            {"year": 2019, "cpih_index_2019_100": 100.0},
            {"year": 2020, "cpih_index_2019_100": 100.0},
            {"year": 2025, "cpih_index_2019_100": 110.0},
        ]
    )

    annual, summary = compute_decomposition(raw, inflation)
    path = write_decomposition_report(pd.DataFrame(), summary, annual=annual, evidence_root=tmp_path)
    text = path.read_text(encoding="utf-8")

    assert {
        "weekly_log_change",
        "hourly_log_contribution",
        "hours_log_contribution",
        "residual_log_contribution",
        "residual_abs_log_contribution",
    }.issubset(annual.columns)
    assert "## Residual Diagnostics" in text
    assert "maximum absolute residual" in text


def test_policy_brief_generator_preserves_robustness_wording(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import uk_wages.analysis as analysis

    monkeypatch.setattr(analysis, "project_path", lambda *parts: tmp_path.joinpath(*parts))
    (tmp_path / "reports").mkdir()
    summary = pd.DataFrame(
        [
            {"age_group": "18-21", "real_pct_change": -1.8, "real_gain_or_loss": "loss"},
            {"age_group": "22-29", "real_pct_change": 3.6, "real_gain_or_loss": "gain"},
        ]
    )

    write_policy_brief(summary, latest_year=2025)

    text = (tmp_path / "reports" / "policy_brief.md").read_text(encoding="utf-8")
    assert "## Robustness Wording" in text
    assert "Do not state it as a simple gain or loss" in text


def test_policy_brief_uses_actual_weakest_age_group(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import uk_wages.analysis as analysis

    monkeypatch.setattr(analysis, "project_path", lambda *parts: tmp_path.joinpath(*parts))
    (tmp_path / "reports").mkdir()
    summary = pd.DataFrame(
        [
            {"age_group": "18-21", "real_pct_change": 1.4, "real_gain_or_loss": "gain"},
            {"age_group": "22-29", "real_pct_change": -3.2, "real_gain_or_loss": "loss"},
        ]
    )

    write_policy_brief(summary, latest_year=2025)

    text = (tmp_path / "reports" / "policy_brief.md").read_text(encoding="utf-8")
    assert "Do not turn the weakest 22-29 result into a simple claim" in text
    assert "Do not turn the weakest 18-21 result" not in text
