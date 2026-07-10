from __future__ import annotations

from pathlib import Path

import pandas as pd

from uk_wages.claim_confidence import build_claim_confidence
from uk_wages.claims import assess_claims, verdict_from_scores
from uk_wages.fragility_diagnostics import (
    build_fragility_diagnostics,
    build_minimal_flip_specs,
    build_one_way_sensitivity,
    classify_materiality,
    material_disagreement,
)
from uk_wages.robustness import compute_fragility_scores
from uk_wages.utils import load_yaml


def _matrix() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "experiment_name": [
                "baseline",
                "sensitivity_cpi",
                "sensitivity_base_2020",
                "sensitivity_full_time_only",
            ],
            "spec_tier": ["core", "core", "core", "stress"],
            "age_group": ["18-21", "18-21", "18-21", "18-21"],
            "baseline_year": [2019, 2019, 2020, 2019],
            "deflator": ["cpih", "cpi", "cpih", "cpih"],
            "inflation_period": ["april", "april", "april", "april"],
            "wage_measure": ["median_weekly", "median_weekly", "median_weekly", "median_weekly"],
            "work_status": ["all", "all", "all", "full_time"],
            "real_pct_change": [0.2, -0.1, -2.0, -1.6],
            "baseline_real_pct_change": [0.2, 0.2, 0.2, 0.2],
            "difference_from_baseline": [0.0, -0.3, -2.2, -1.8],
            "sign_flip_vs_baseline": [False, True, True, True],
            "supports_main_claim": [True, False, False, False],
            "rank_vs_other_age_groups": [3.0, 3.0, 4.0, 4.0],
            "baseline_rank": [3.0, 3.0, 3.0, 3.0],
            "rank_change_by_age_group": [0.0, 0.0, 1.0, 1.0],
            "young_worker_gap_vs_25_34": [-2.0, -2.1, -4.0, -3.8],
            "young_worker_gap_vs_30_39": [-3.0, -3.1, -5.0, -4.8],
            "evidence_strength": ["supports", "weak", "contradicts", "contradicts"],
            "notes": ["", "", "", ""],
        }
    )


def _baseline_and_six_core_alternatives() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "experiment_name": ["baseline", "alt_1", "alt_2", "alt_3", "alt_4", "alt_5", "alt_6"],
            "spec_tier": ["core"] * 7,
            "age_group": ["22-29"] * 7,
            "supports_main_claim": [True, False, False, False, True, True, True],
            "material_disagreement": [False, True, True, True, False, False, False],
        }
    )


def test_materiality_classification_separates_near_zero_flips() -> None:
    assert classify_materiality(1.1, threshold_pp=1.0) == "positive_material"
    assert classify_materiality(-1.1, threshold_pp=1.0) == "negative_material"
    assert classify_materiality(0.2, threshold_pp=1.0) == "near_zero_or_inconclusive"
    assert not material_disagreement(0.2, -0.1, threshold_pp=1.0)
    assert material_disagreement(0.2, -2.0, threshold_pp=1.0)


def test_fragility_scores_are_reported_by_core_and_stress_tier() -> None:
    scores = compute_fragility_scores(_matrix())

    core = scores[(scores["age_group"].eq("18-21")) & (scores["spec_tier"].eq("core"))].iloc[0]
    stress = scores[(scores["age_group"].eq("18-21")) & (scores["spec_tier"].eq("stress"))].iloc[0]
    assert core["specifications_tested"] == 2
    assert core["material_disagreements"] == 1
    assert stress["specifications_tested"] == 1


def test_fragility_scores_count_only_alternative_specifications() -> None:
    scores = compute_fragility_scores(_baseline_and_six_core_alternatives())

    core = scores.loc[scores["spec_tier"].eq("core")].iloc[0]
    assert core["specifications_tested"] == 6
    assert core["material_disagreements"] == 3
    assert core["fragility_score"] == 0.5
    assert core["assessment"] == "not robust"


def test_baseline_only_fragility_group_is_inconclusive() -> None:
    matrix = pd.DataFrame(
        {
            "experiment_name": ["baseline"],
            "spec_tier": ["core"],
            "age_group": ["18-21"],
            "supports_main_claim": [True],
            "material_disagreement": [False],
        }
    )

    score = compute_fragility_scores(matrix).iloc[0]

    assert score["specifications_tested"] == 0
    assert pd.isna(score["fragility_score"])
    assert pd.isna(score["material_fragility_score"])
    assert score["assessment"] == "inconclusive"
    assert score["material_assessment"] == "inconclusive"


def test_claim_can_scope_scoring_to_exact_experiment_names(tmp_path: Path) -> None:
    age_groups = ["16-17", "18-21", "22-29", "30-39", "40-49", "50-59", "60+"]
    experiments = ["baseline", "sensitivity_cpi"] + [f"unrelated_{index}" for index in range(8)]
    matrix = pd.DataFrame(
        [
            {
                "experiment_name": experiment,
                "spec_tier": "core" if experiment != "unrelated_7" else "stress",
                "age_group": age_group,
                "material_disagreement": experiment.startswith("unrelated_"),
                "sign_flip_vs_baseline": experiment.startswith("unrelated_"),
                "difference_from_baseline": -2.0 if experiment.startswith("unrelated_") else 0.2,
            }
            for experiment in experiments
            for age_group in age_groups
        ]
    )
    claims = [
        {
            "claim_id": "c3_inflation_deflator_sensitivity",
            "text": "The headline conclusion is not driven only by choosing CPIH instead of CPI.",
            "population": "all age groups",
            "outcome": "real earnings",
            "robustness_required": True,
            "spec_tier": "all",
            "experiment_names": ["sensitivity_cpi"],
        }
    ]

    output_root = tmp_path / "outputs"
    evidence_root = output_root / "evidence"
    output = assess_claims(claims, matrix, evidence_root)
    result = pd.read_csv(output).iloc[0]

    assert result["specifications_tested"] == 7
    assert result["material_disagreements"] == 0
    assert result["verdict"] == "robust"
    assert "holds across the configured robustness experiments" in result["recommended_wording"]

    confidence_path, _ = build_claim_confidence(output_root=output_root)
    confidence = pd.read_csv(confidence_path).iloc[0]
    assert confidence["confidence_label"] == "medium confidence"
    assert confidence["recommended_public_wording"] == result["recommended_wording"]


def test_cpi_claim_config_selects_only_the_cpi_sensitivity_experiment() -> None:
    claims = load_yaml(Path("config/claims.yaml"))["claims"]
    cpi_claim = next(
        claim for claim in claims if claim["claim_id"] == "c3_inflation_deflator_sensitivity"
    )

    assert cpi_claim["experiment_names"] == ["sensitivity_cpi"]


def test_one_way_sensitivity_output_has_required_columns(tmp_path: Path) -> None:
    output = build_one_way_sensitivity(_matrix(), tmp_path, age_groups=["18-21"], threshold_pp=1.0)
    result = pd.read_csv(output)

    assert {
        "changed_assumption",
        "baseline_value",
        "alternative_value",
        "baseline_real_pct_change",
        "alternative_real_pct_change",
        "difference_pp",
        "sign_flip",
        "material_disagreement",
        "interpretation",
    }.issubset(result.columns)
    assert result[result["changed_assumption"].eq("baseline_year")]["material_disagreement"].iloc[0]


def test_minimal_flip_specs_identifies_smallest_material_flip(tmp_path: Path) -> None:
    output = build_minimal_flip_specs(_matrix(), tmp_path, threshold_pp=1.0)
    result = pd.read_csv(output)

    row = result[result["age_group"].eq("18-21")].iloc[0]
    assert row["number_of_assumptions_changed"] == 1
    assert row["material_flip"]


def test_claim_assessment_verdict_logic_and_recommended_wording(tmp_path: Path) -> None:
    claims = [
        {
            "claim_id": "c1_youngest_real_wages",
            "text": "Workers aged 18-21 became better off in real earnings terms since 2019.",
            "population": "18-21",
            "outcome": "real earnings",
            "robustness_required": True,
        }
    ]

    output = assess_claims(claims, _matrix(), tmp_path)
    result = pd.read_csv(output)

    assert verdict_from_scores(0.4, 0.25) == "fragile"
    assert result.loc[0, "claim_id"] == "c1_youngest_real_wages"
    assert result.loc[0, "verdict"] == "not robust"
    assert "sensitive" in result.loc[0, "recommended_wording"]


def test_comparison_claim_uses_metric_once_per_experiment(tmp_path: Path) -> None:
    matrix = pd.DataFrame(
        [
            {
                "experiment_name": experiment,
                "spec_tier": "core",
                "age_group": age_group,
                "young_worker_gap_vs_30_39": gap,
            }
            for experiment, gap in [
                ("baseline", -3.0),
                ("sensitivity_cpi", -3.1),
                ("sensitivity_base_2020", 2.0),
            ]
            for age_group in ["18-21", "30-39"]
        ]
    )
    claims = [
        {
            "claim_id": "c2_young_workers_vs_prime_age",
            "text": "Workers aged 18-21 underperformed the 30-39 ASHE comparator.",
            "population": "18-21 compared with 30-39",
            "outcome": "relative real earnings",
            "robustness_required": True,
            "spec_tier": "core",
            "comparison_metric": "young_worker_gap_vs_30_39",
        }
    ]

    output = assess_claims(claims, matrix, tmp_path)
    result = pd.read_csv(output)

    assert result.loc[0, "specifications_tested"] == 2
    assert result.loc[0, "material_disagreements"] == 1
    assert "young_worker_gap_vs_30_39" in result.loc[0, "recommended_wording"]


def test_fragility_diagnostics_report_is_created(tmp_path: Path) -> None:
    build_one_way_sensitivity(_matrix(), tmp_path, age_groups=["18-21"], threshold_pp=1.0)
    build_minimal_flip_specs(_matrix(), tmp_path, threshold_pp=1.0)

    report = build_fragility_diagnostics(_matrix(), tmp_path, threshold_pp=1.0)

    text = report.read_text(encoding="utf-8")
    assert "Fragility diagnostics for 18-21" in text
    assert "Materiality" in text
