from __future__ import annotations

from pathlib import Path

import pandas as pd

from uk_wages.claim_confidence import build_claim_confidence
from uk_wages.lineage import build_headline_number_lineage


def _seed_evidence(root: Path) -> None:
    evidence = root / "evidence"
    tables = root / "tables"
    evidence.mkdir(parents=True)
    tables.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "claim_id": "c1_youngest_real_wages",
                "claim_text": "18-21 workers clearly became worse off in real weekly earnings.",
                "verdict": "fragile",
                "recommended_wording": "The 18-21 result is fragile and source-dependent.",
            },
            {
                "claim_id": "c2_22_29_real_wages",
                "claim_text": "22-29 real weekly earnings increased after inflation.",
                "verdict": "moderately robust",
                "recommended_wording": "The 22-29 result is more stable, with caveats.",
            },
        ]
    ).to_csv(evidence / "claim_assessment.csv", index=False)
    pd.DataFrame(
        [
            {
                "age_group": "18-21",
                "spec_tier": "core",
                "specifications_tested": 7,
                "material_disagreements": 3,
                "fragility_score": 0.429,
            },
            {
                "age_group": "22-29",
                "spec_tier": "core",
                "specifications_tested": 7,
                "material_disagreements": 1,
                "fragility_score": 0.143,
            },
        ]
    ).to_csv(evidence / "fragility_scores.csv", index=False)
    pd.DataFrame(
        [{"check_name": "toy", "status": "pass"}, {"check_name": "toy2", "status": "pass"}]
    ).to_csv(evidence / "source_value_checks.csv", index=False)
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
            },
            {
                "age_group": "22-29",
                "measure": "weekly_gross",
                "estimate": "median",
                "latest_year": 2025,
                "latest_quality_status": "precise",
                "latest_cv_percent": 0.4,
                "missing_quality_evidence": False,
            },
        ]
    ).to_csv(tables / "ashe_quality_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "age_group": "18-21",
                "all_employee_weekly_pct_change": 25.66,
                "full_time_weekly_pct_change": 33.33,
                "part_time_weekly_pct_change": 20.83,
                "hours_pct_change": -20.40,
                "composition_note": "Full-time and part-time rows are descriptive; counts unavailable.",
            }
        ]
    ).to_csv(tables / "ashe_composition_change_by_age.csv", index=False)
    (evidence / "rti_ashe_triangulation.md").write_text(
        "RTI 18-24 points differently from ASHE 18-21.", encoding="utf-8"
    )
    (evidence / "ashe_decomposition_report.md").write_text(
        "18-21 hourly pay rose while hours fell.", encoding="utf-8"
    )
    (evidence / "minimum_wage_context.md").write_text(
        "Minimum wage rates are wage-floor context only.", encoding="utf-8"
    )


def _seed_headline_tables(root: Path) -> None:
    tables = root / "tables"
    evidence = root / "evidence"
    tables.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"age_group": "18-21", "latest_year": 2025, "real_pct_change": -1.81},
            {"age_group": "22-29", "latest_year": 2025, "real_pct_change": 3.57},
        ]
    ).to_csv(tables / "age_group_real_earnings_change.csv", index=False)
    pd.DataFrame(
        [
            {
                "age_group": "18-24",
                "real_pay_pct_change_since_jan2019": 6.22,
                "latest_available_month": "2026-05-01",
            }
        ]
    ).to_csv(tables / "rti_age_real_pay_change.csv", index=False)
    pd.DataFrame(
        [
            {
                "age_group": "18-21",
                "hourly_pct_change": 15.33,
                "hours_pct_change": -20.40,
                "latest_year": 2025,
            }
        ]
    ).to_csv(tables / "ashe_hours_decomposition.csv", index=False)
    pd.DataFrame(
        [
            {
                "effective_year": 2026,
                "policy_series": "18 to 20",
                "real_statutory_wage_index_2019_100": 118.0,
            }
        ]
    ).to_csv(tables / "minimum_wage_real_rates.csv", index=False)
    pd.DataFrame(
        [
            {
                "date": "2026-04-30",
                "youth_unemployment_gap_change_since_2019": 3.70,
            }
        ]
    ).to_csv(tables / "youth_labour_market_gaps.csv", index=False)
    pd.DataFrame(
        [
            {"check_name": "one", "status": "pass"},
            {"check_name": "two", "status": "pass"},
            {"check_name": "three", "status": "fail"},
        ]
    ).to_csv(evidence / "source_value_checks.csv", index=False)


def test_claim_confidence_ladder_combines_evidence_inputs(tmp_path: Path) -> None:
    _seed_evidence(tmp_path / "outputs")

    csv_path, md_path = build_claim_confidence(output_root=tmp_path / "outputs")
    ladder = pd.read_csv(csv_path)
    text = md_path.read_text(encoding="utf-8")

    assert {
        "claim_id",
        "claim_text",
        "baseline_result",
        "robustness_status",
        "quality_status",
        "triangulation_status",
        "confidence_label",
        "recommended_public_wording",
        "what_would_change_this_assessment",
    }.issubset(ladder.columns)
    claim_18 = ladder[ladder["claim_id"].eq("c1_youngest_real_wages")].iloc[0]
    assert claim_18["confidence_label"] == "not supported"
    assert "RTI" in claim_18["triangulation_status"]
    assert "would strengthen" in claim_18["what_would_change_this_assessment"]
    assert "# Claim Confidence Ladder" in text


def test_headline_number_lineage_maps_required_outputs(tmp_path: Path) -> None:
    _seed_headline_tables(tmp_path / "outputs")

    csv_path, md_path = build_headline_number_lineage(output_root=tmp_path / "outputs")
    lineage = pd.read_csv(csv_path)

    required = {
        "18-21 ASHE real weekly earnings change",
        "22-29 ASHE real weekly earnings change",
        "RTI 18-24 real monthly PAYE pay change",
        "18-21 real hourly pay change",
        "18-21 paid hours change",
        "18-20 real minimum wage index",
        "A05 youth unemployment gap change",
        "source audit pass count",
    }
    assert required.issubset(set(lineage["headline_number"]))
    assert {"source_dataset", "raw_file", "processed_file", "analysis_module"}.issubset(
        lineage.columns
    )
    assert "fragile" in lineage.loc[
        lineage["headline_number"].eq("18-21 ASHE real weekly earnings change"), "caveat"
    ].iloc[0]
    assert "source audit pass count" in md_path.read_text(encoding="utf-8")
