from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from uk_wages.final_claims import build_final_claims
from uk_wages.source_validation import (
    REQUIRED_SOURCE_CHECKS,
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
    assert "Toy audit tolerance." in audit_path.read_text(encoding="utf-8")


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
                "claim_text": "Workers aged 18-21 became better off in real earnings terms since 2019.",
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
        "ASHE and EARN01 measure different things.",
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


def test_final_claims_requires_evidence_inputs(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_final_claims(output_root=tmp_path, processed_root=tmp_path / "processed")


def test_source_value_collector_reads_current_raw_data_when_available() -> None:
    required_paths = [
        Path("data/raw/inflation"),
        Path("data/raw/ashe_age"),
        Path("data/raw/a05"),
        Path("data/raw/earn01"),
        Path("data/processed/inflation_annual.parquet"),
        Path("data/processed/ashe_age_annual.parquet"),
        Path("data/processed/a05_age_labour_market.parquet"),
        Path("data/processed/awe_real_monthly.parquet"),
    ]
    if not all(path.exists() for path in required_paths):
        pytest.skip("Raw and processed source data are not present in this checkout.")

    records = collect_source_value_checks()

    assert set(REQUIRED_SOURCE_CHECKS).issubset({record["check_name"] for record in records})
    assert {record["status"] for record in records} == {"pass"}
    a05_latest = next(record for record in records if record["check_name"] == "a05_16_24_unemployment_latest")
    assert "Independent raw derivation" in str(a05_latest["note"])
    assert "component cells" in str(a05_latest["note"])
