from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from uk_wages.evidence import build_evidence_report
from uk_wages.final_claims import build_final_claims
from uk_wages.source_validation import (
    REQUIRED_SOURCE_CHECKS,
    _record,
    collect_source_value_checks,
    write_source_validation_outputs,
)


def _check_record(name: str) -> dict[str, object]:
    return {
        "check_name": name,
        "source_dataset": "toy",
        "raw_file_path": "data/raw/toy.csv",
        "sheet_or_table": "toy sheet",
        "row_or_series_identifier": name,
        "raw_value": 100.0,
        "processed_value": 100.0,
        "absolute_difference": 0.0,
        "status": "pass",
        "note": "toy value within documented tolerance",
    }


def test_source_value_audit_outputs_required_check_names(tmp_path: Path) -> None:
    csv_path, audit_path = write_source_validation_outputs(
        [_check_record(name) for name in REQUIRED_SOURCE_CHECKS],
        tmp_path,
        tolerance_note="Toy audit tolerance.",
    )

    checks = pd.read_csv(csv_path)

    assert csv_path.exists()
    assert audit_path.exists()
    assert set(REQUIRED_SOURCE_CHECKS).issubset(set(checks["check_name"]))
    assert {
        "source_dataset",
        "raw_file_path",
        "sheet_or_table",
        "row_or_series_identifier",
        "raw_value",
        "processed_value",
        "absolute_difference",
        "status",
        "note",
    }.issubset(checks.columns)
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "Toy audit tolerance." in audit_text
    assert "official source files, including ONS/HMRC and GOV.UK inputs" in audit_text


def test_source_value_records_use_repo_relative_paths() -> None:
    record = _record(
        check_name="toy",
        source_dataset="toy",
        raw_file_path=Path.cwd() / "data" / "raw" / "toy.csv",
        sheet_or_table="toy sheet",
        row_or_series_identifier="toy",
        raw_value=1.0,
        processed_value=1.0,
        note="toy check",
    )

    assert record["raw_file_path"] == "data/raw/toy.csv"


def test_final_claims_freeze_fragile_youngest_and_earn01_limits(tmp_path: Path) -> None:
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
                "population": "18-21",
                "verdict": "fragile",
                "recommended_wording": (
                    "Treat this claim as sensitive to defensible specification choices."
                ),
            },
            {
                "claim_id": "c2_22_29_real_wages",
                "claim_text": "Workers aged 22-29 saw real earnings gains since 2019.",
                "population": "22-29",
                "verdict": "moderately robust",
                "recommended_wording": "Describe the 22-29 result with robustness caveats.",
            },
        ]
    ).to_csv(evidence_root / "claim_assessment.csv", index=False)
    (evidence_root / "fragility_diagnostics.md").write_text(
        "18-21 material disagreements are driven by baseline_year and wage_measure.",
        encoding="utf-8",
    )
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
                "fragility_score": 0.0,
            },
        ]
    ).to_csv(evidence_root / "fragility_scores.csv", index=False)
    (evidence_root / "triangulation_report.md").write_text(
        "ASHE and EARN01 measure different things. EARN01 is not age-specific. Directional concordance is reported.",
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "age_group": "18-21",
                "regular_direction_concordance": 0.8333,
                "yoy_comparison_years": 6,
                "latest_regular_level_gap_pp": -6.96,
            }
        ]
    ).to_csv(evidence_root / "triangulation_summary.csv", index=False)
    (evidence_root / "rti_ashe_triangulation.md").write_text(
        "RTI is a monthly PAYE check and does not replace ASHE. April-to-April overlap is reported.",
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "rti_age_group": "18-24",
                "ashe_age_group": "18-21",
                "directional_concordance": 1.0,
                "comparison_years": 6,
                "latest_level_gap_pp": -7.95,
            }
        ]
    ).to_csv(evidence_root / "rti_ashe_annual_summary.csv", index=False)
    (evidence_root / "ashe_uncertainty_bands.md").write_text(
        "18-21 approximate two-CV band -6.37% to 2.75% includes zero.",
        encoding="utf-8",
    )
    (evidence_root / "option_b_ds_report.md").write_text(
        "Option B Modelling Diagnostics with structural break, event framing, and forecast baseline.",
        encoding="utf-8",
    )
    (evidence_root / "ashe_decomposition_report.md").write_text(
        "The decomposition uses hourly pay, hours, and a residual.",
        encoding="utf-8",
    )
    (evidence_root / "minimum_wage_context.md").write_text(
        "Minimum wage rates are policy context. They do not prove causality.",
        encoding="utf-8",
    )
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
    assert "## Claim 1: 18-21 real earnings" in text
    assert "Verdict: fragile / ambiguous" in text
    assert "does not support a simple claim" in text
    assert "## Claim 4: Current monthly wage trend" in text
    assert "whole-economy wage trend" in text
    assert "EARN01 is not age-specific" in text
    assert "not be interpreted as age-specific evidence" in text
    assert "Directional concordance with EARN01 regular pay" in text
    assert "## Claim 5: RTI monthly age-pay triangulation" in text
    assert "not a replacement for ASHE" in text
    assert "April-to-April RTI-ASHE concordance" in text
    assert "approximate two-CV band" in text
    assert "## Claim 8: Option B modelling diagnostics" in text
    assert "structural break, event framing, and forecast baseline" in text
    assert "## Claim 6: Hourly pay versus hours" in text
    assert "## Claim 7: Minimum wage context" in text


def test_evidence_report_lists_new_analytical_pillars(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    experiments = tmp_path / "experiments"
    evidence_root.mkdir(parents=True)
    experiments.mkdir()
    for filename in [
        "triangulation_report.md",
        "rti_ashe_triangulation.md",
        "ashe_decomposition_report.md",
        "minimum_wage_context.md",
        "ashe_quality_availability.md",
        "ashe_uncertainty_bands.md",
        "ashe_composition_audit.md",
        "claim_confidence.md",
        "headline_number_lineage.md",
        "option_b_ds_report.md",
    ]:
        (evidence_root / filename).write_text(f"{filename} content", encoding="utf-8")
    pd.DataFrame([{"age_group": "18-21"}]).to_csv(
        evidence_root / "triangulation_summary.csv", index=False
    )
    pd.DataFrame([{"rti_age_group": "18-24"}]).to_csv(
        evidence_root / "rti_ashe_annual_summary.csv", index=False
    )

    path = build_evidence_report(output_root=tmp_path)

    text = path.read_text(encoding="utf-8")
    assert "ASHE-EARN01 triangulation metrics" in text
    assert "RTI-ASHE annual concordance" in text
    assert "ASHE approximate CV bands" in text
    assert "Option B modelling diagnostics" in text


def test_final_claims_requires_evidence_inputs(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_final_claims(output_root=tmp_path, processed_root=tmp_path / "processed")


def test_source_value_collector_reads_current_raw_data_when_available() -> None:
    required_paths = [
        Path("data/raw/inflation"),
        Path("data/raw/ashe_age"),
        Path("data/raw/a05"),
        Path("data/raw/earn01"),
        Path("data/raw/rti"),
        Path("data/raw/minimum_wage"),
        Path("data/processed/inflation_annual.parquet"),
        Path("data/processed/ashe_age_annual.parquet"),
        Path("data/processed/a05_age_labour_market.parquet"),
        Path("data/processed/awe_real_monthly.parquet"),
        Path("data/processed/rti_age_monthly.parquet"),
        Path("data/processed/minimum_wage_rates.parquet"),
    ]
    if not all(path.exists() for path in required_paths):
        pytest.skip("Raw and processed source data are not present in this checkout.")

    records = collect_source_value_checks()

    assert set(REQUIRED_SOURCE_CHECKS).issubset({record["check_name"] for record in records})
    assert {record["status"] for record in records} == {"pass"}
    a05_latest = next(record for record in records if record["check_name"] == "a05_16_24_unemployment_latest")
    assert "Independent raw derivation" in str(a05_latest["note"])
    assert "component cells" in str(a05_latest["note"])
