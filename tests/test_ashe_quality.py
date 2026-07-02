from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from uk_wages.ashe_quality import build_ashe_quality_outputs, inspect_ashe_quality_archives
from uk_wages.final_claims import build_final_claims


def _write_cv_workbook(path: Path) -> None:
    rows = [
        ["Table 6.1b Coefficients of variation for Weekly pay - Gross", None, None, None, None, None],
        [None, None, "Number", None, None, None],
        [None, None, "of jobs", None, None, None],
        ["Description", "Code", "(thousand)", "Median", "change", "Mean"],
        ["18-21", None, 0.5, 1.8, ".", 1.0],
        ["22-29", None, 0.6, 0.4, ".", 0.5],
        ["30-39", None, 0.4, 0.4, ".", 0.4],
    ]
    notes = [
        ["Guide to quality"],
        ["These tables provide quality measures called coefficients of variation."],
        ["x = CV > 20%", "Estimates are considered unreliable for practical purposes"],
        [".. = disclosive"],
    ]
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame(notes).to_excel(writer, sheet_name="CV notes", header=False, index=False)
        pd.DataFrame(rows).to_excel(writer, sheet_name="All", header=False, index=False)


def _zip_workbook(zip_path: Path, member_name: str, workbook_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w") as archive:
        archive.write(workbook_path, arcname=member_name)


def test_cv_workbooks_are_detected_and_parsed(tmp_path: Path) -> None:
    workbook = tmp_path / "weekly_cv.xlsx"
    _write_cv_workbook(workbook)
    zip_path = tmp_path / "ashe_age" / "2025provisional" / "ashetable62025provisional.zip"
    _zip_workbook(
        zip_path,
        "PROV - Age Group Table 6.1b Weekly pay - Gross 2025 CV.xlsx",
        workbook,
    )

    inspected = inspect_ashe_quality_archives(
        age_raw_root=tmp_path / "ashe_age",
        region_age_raw_root=tmp_path / "empty_region",
    )

    assert not inspected.empty
    assert inspected["usable_quality_evidence"].any()
    assert "coefficient_of_variation" in set(inspected["evidence_type"])

    flags, summary = build_ashe_quality_outputs(
        age_raw_root=tmp_path / "ashe_age",
        region_age_raw_root=tmp_path / "empty_region",
        processed_root=tmp_path / "processed",
        output_root=tmp_path / "outputs",
    )

    median_flags = flags[
        flags["source_family"].eq("ashe_age")
        & flags["age_group"].eq("18-21")
        & flags["measure"].eq("weekly_gross")
        & flags["estimate"].eq("median")
    ]
    assert median_flags.iloc[0]["quality_status"] == "precise"
    assert median_flags.iloc[0]["cv_percent"] == 1.8
    assert "18-21" in set(summary["age_group"])
    assert (tmp_path / "outputs" / "evidence" / "ashe_quality_availability.md").exists()


def test_missing_uncertainty_fields_are_documented(tmp_path: Path) -> None:
    workbook = tmp_path / "weekly.xlsx"
    _write_cv_workbook(workbook)
    zip_path = tmp_path / "ashe_age" / "2025provisional" / "ashetable62025provisional.zip"
    _zip_workbook(zip_path, "Age Group Table 6.1a Weekly pay - Gross 2025.xlsx", workbook)

    flags, _ = build_ashe_quality_outputs(
        age_raw_root=tmp_path / "ashe_age",
        region_age_raw_root=tmp_path / "empty_region",
        processed_root=tmp_path / "processed",
        output_root=tmp_path / "outputs",
    )

    text = (tmp_path / "outputs" / "evidence" / "ashe_quality_availability.md").read_text(
        encoding="utf-8"
    )
    assert flags.empty
    assert "No usable ASHE uncertainty fields were found" in text
    assert "ashetable62025provisional.zip" in text


def test_final_claims_mentions_ashe_quality_status(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    tables_root = tmp_path / "tables"
    processed_root = tmp_path / "processed"
    evidence_root.mkdir(parents=True)
    tables_root.mkdir(parents=True)
    processed_root.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "claim_id": "c1_youngest_real_wages",
                "claim_text": "Workers aged 18-21 experienced a clear real earnings gain or loss since 2019.",
                "verdict": "fragile",
                "recommended_wording": "Treat as fragile.",
            },
            {
                "claim_id": "c2_22_29_real_wages",
                "claim_text": "Workers aged 22-29 saw real earnings gains since 2019.",
                "verdict": "moderately robust",
                "recommended_wording": "Describe with caveats.",
            },
        ]
    ).to_csv(evidence_root / "claim_assessment.csv", index=False)
    pd.DataFrame(
        [
            {
                "claim": "18-21 direction matches baseline",
                "age_group": "18-21",
                "spec_tier": "core",
                "specifications_tested": 7,
                "material_disagreements": 3,
                "fragility_score": 0.429,
            },
            {
                "claim": "22-29 direction matches baseline",
                "age_group": "22-29",
                "spec_tier": "core",
                "specifications_tested": 7,
                "material_disagreements": 1,
                "fragility_score": 0.143,
            },
        ]
    ).to_csv(evidence_root / "fragility_scores.csv", index=False)
    (evidence_root / "fragility_diagnostics.md").write_text(
        "## Fragility diagnostics for 18-21\n\nMaterial disagreements are present.",
        encoding="utf-8",
    )
    (evidence_root / "triangulation_report.md").write_text(
        "EARN01 is not age-specific.", encoding="utf-8"
    )
    (evidence_root / "rti_ashe_triangulation.md").write_text(
        "RTI is a monthly PAYE check and does not replace ASHE.", encoding="utf-8"
    )
    (evidence_root / "ashe_decomposition_report.md").write_text(
        "hourly pay, hours, and residual.", encoding="utf-8"
    )
    (evidence_root / "minimum_wage_context.md").write_text(
        "minimum wage context rates do not prove ASHE changes.", encoding="utf-8"
    )
    (evidence_root / "ashe_quality_availability.md").write_text(
        "ASHE CV workbooks were found and parsed.", encoding="utf-8"
    )
    pd.DataFrame(
        [
            {
                "age_group": "18-21",
                "measure": "weekly_gross",
                "estimate": "median",
                "latest_year": 2025,
                "latest_quality_status": "precise",
                "latest_cv_percent": 1.8,
                "missing_quality_evidence": False,
            }
        ]
    ).to_csv(tables_root / "ashe_quality_summary.csv", index=False)
    pd.DataFrame(
        [
            {"age_group": "18-21", "latest_year": 2025, "real_pct_change": -1.81},
            {"age_group": "22-29", "latest_year": 2025, "real_pct_change": 3.57},
        ]
    ).to_csv(tables_root / "age_group_real_earnings_change.csv", index=False)
    pd.DataFrame(
        [
            {
                "date": "2026-04-30",
                "youth_unemployment_gap_change_since_2019": 3.7,
                "youth_inactivity_gap_change_since_2019": 2.68,
            }
        ]
    ).to_csv(tables_root / "youth_labour_market_gaps.csv", index=False)
    pd.DataFrame(
        [
            {
                "age_group": "18-24",
                "latest_available_month": "2026-05-01",
                "latest_available_is_flash_or_provisional": True,
                "real_pay_pct_change_since_jan2019": 2.4,
            }
        ]
    ).to_csv(tables_root / "rti_age_real_pay_change.csv", index=False)
    pd.DataFrame(
        [
            {
                "age_group": "18-21",
                "baseline_year": 2019,
                "latest_year": 2025,
                "weekly_pct_change": -1.8,
                "hourly_log_contribution": 0.02,
                "hours_log_contribution": -0.03,
                "residual_log_contribution": -0.01,
            }
        ]
    ).to_csv(tables_root / "ashe_hours_decomposition.csv", index=False)
    pd.DataFrame(
        [
            {
                "effective_year": 2026,
                "policy_series": "18 to 20",
                "nominal_hourly_rate": 10.85,
                "real_statutory_wage_index_2019_100": 118.0,
            }
        ]
    ).to_csv(tables_root / "minimum_wage_real_rates.csv", index=False)
    pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2026-04-01"),
                "sector": "Whole Economy",
                "real_regular_pay_index_jan2019_100": 105.05,
                "real_total_pay_index_jan2019_100": 106.68,
            }
        ]
    ).to_parquet(processed_root / "awe_real_monthly.parquet", index=False)

    path = build_final_claims(output_root=tmp_path, processed_root=processed_root)

    text = path.read_text(encoding="utf-8")
    assert "ASHE uncertainty and quality evidence" in text
    assert "18-21 median weekly CV is 1.80%" in text
