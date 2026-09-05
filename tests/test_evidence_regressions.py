from pathlib import Path

import pandas as pd
import pytest

from uk_wages.claim_confidence import _confidence_label
from uk_wages.claims import assess_claims, verdict_from_scores
from uk_wages.robustness import build_contrarian_report, fragility_label, robustness_count_summary
from uk_wages import source_validation


@pytest.mark.parametrize("verdict", ["not robust", "inconclusive", "fragile"])
def test_weak_verdict_never_gets_medium_confidence(verdict: str) -> None:
    assert _confidence_label("c2_22_29_real_wages", verdict, verdict, "precise") == "low confidence"


def test_zero_disagreements_do_not_disqualify_a_robust_youngest_claim() -> None:
    assert _confidence_label(
        "c1_youngest_real_wages", "robust", "0 of 7 specifications materially disagree", "precise"
    ) == "medium confidence"


@pytest.mark.parametrize("score", [.1, .3, .5])
def test_claim_and_fragility_labels_agree_at_boundaries(score: float) -> None:
    assert fragility_label(score) == verdict_from_scores(score, score)


@pytest.mark.parametrize("claim", [
    {"population": "25-34"},
    {"population": "18-21 compared with 25-34", "comparison_metric": "missing_gap"},
])
def test_missing_claim_population_or_metric_is_inconclusive(tmp_path: Path, claim: dict) -> None:
    matrix = pd.DataFrame({"age_group": ["18-21"], "spec_tier": ["core"]})
    path = assess_claims([{"claim_id": "missing", "text": "Missing evidence", **claim}], matrix, tmp_path)
    result = pd.read_csv(path).iloc[0]
    assert result["verdict"] == "inconclusive"
    assert result["specifications_tested"] == 0


def test_robustness_counts_partition_experiments_across_age_rows() -> None:
    matrix = pd.DataFrame({
        "experiment_name": ["baseline", "baseline", "sensitivity", "sensitivity"],
        "sign_flip_vs_baseline": ["False", "False", "False", "True"],
        "material_disagreement": ["False", "False", "True", "True"],
    })
    assert robustness_count_summary(matrix) == {
        "specifications_tested": 2, "supporting": 1, "weakening": 0, "reversing": 1,
    }


def test_contrarian_report_does_not_treat_false_text_as_true(tmp_path: Path) -> None:
    matrix = pd.DataFrame({
        "sign_flip_vs_baseline": ["False"], "supports_main_claim": ["True"],
        "material_disagreement": ["False"], "difference_from_baseline": [0.],
    })
    path = build_contrarian_report(matrix, tmp_path, threshold_pp=1.)
    assert "No specifications materially weakened" in path.read_text(encoding="utf-8")


def test_failed_source_check_stops_pipeline_but_keeps_diagnostics(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(source_validation, "collect_source_value_checks", lambda **kwargs: [
        {"check_name": "broken_source", "status": "fail"},
    ])
    with pytest.raises(ValueError, match="Source validation failed: broken_source"):
        source_validation.build_source_value_audit(output_root=tmp_path)
    assert (tmp_path / "source_value_checks.csv").exists()
    assert "fail" in (tmp_path / "manual_validation_audit.md").read_text(encoding="utf-8")
