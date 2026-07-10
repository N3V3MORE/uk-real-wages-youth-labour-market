from __future__ import annotations

import pandas as pd

from .fragility_diagnostics import alternative_specifications


def _boolean_values(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).map(
        lambda value: str(value).strip().lower() in {"true", "1", "yes"}
    )


def robustness_headline_metrics(
    matrix: pd.DataFrame,
    scores: pd.DataFrame,
    *,
    age_group: str = "18-21",
    spec_tier: str = "core",
) -> dict[str, int | str]:
    required_matrix = {
        "experiment_name",
        "age_group",
        "spec_tier",
        "supports_main_claim",
        "sign_flip_vs_baseline",
    }
    missing_matrix = required_matrix.difference(matrix.columns)
    if missing_matrix:
        raise ValueError(f"Robustness matrix is missing columns: {sorted(missing_matrix)}")
    required_scores = {
        "age_group",
        "spec_tier",
        "specifications_tested",
        "material_disagreements",
        "assessment",
    }
    missing_scores = required_scores.difference(scores.columns)
    if missing_scores:
        raise ValueError(f"Fragility scores are missing columns: {sorted(missing_scores)}")

    focus = matrix[
        matrix["age_group"].astype(str).eq(age_group)
        & matrix["spec_tier"].astype(str).eq(spec_tier)
    ].copy()
    focus = alternative_specifications(focus).drop_duplicates(subset=["experiment_name"])
    score_rows = scores[
        scores["age_group"].astype(str).eq(age_group)
        & scores["spec_tier"].astype(str).eq(spec_tier)
    ]
    if score_rows.empty:
        raise ValueError(f"Missing {age_group} {spec_tier} fragility score")
    score = score_rows.iloc[0]
    alternatives_tested = int(score["specifications_tested"])
    if alternatives_tested != len(focus):
        raise ValueError(
            f"Fragility score counts {alternatives_tested} alternatives but matrix has {len(focus)}"
        )

    reversing = _boolean_values(focus["sign_flip_vs_baseline"])
    supporting = _boolean_values(focus["supports_main_claim"]) & ~reversing
    weakening = ~supporting & ~reversing
    return {
        "alternatives_tested": alternatives_tested,
        "supporting_alternatives": int(supporting.sum()),
        "weakening_alternatives": int(weakening.sum()),
        "reversing_alternatives": int(reversing.sum()),
        "material_disagreements": int(score["material_disagreements"]),
        "assessment": str(score["assessment"]),
    }
