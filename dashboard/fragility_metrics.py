from __future__ import annotations

import pandas as pd


def _bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.fillna(False).map(
        lambda value: str(value).strip().lower() in {"true", "1", "yes"}
        if isinstance(value, str)
        else bool(value)
    )


def fragility_card_counts(
    matrix: pd.DataFrame,
    *,
    age_group: str = "18-21",
    baseline_experiment: str = "baseline",
) -> dict[str, int]:
    focus = matrix[matrix["age_group"].eq(age_group)]
    alternatives = focus[~focus["experiment_name"].eq(baseline_experiment)]
    if alternatives.empty:
        return {
            "alternative_specifications": 0,
            "supporting": 0,
            "material_disagreements": 0,
            "weakening": 0,
            "reversing": 0,
        }

    supporting = int(_bool_series(alternatives["supports_main_claim"]).sum())
    reversing = int(_bool_series(alternatives["sign_flip_vs_baseline"]).sum())
    material_disagreements = (
        int(_bool_series(alternatives["material_disagreement"]).sum())
        if "material_disagreement" in alternatives.columns
        else 0
    )
    weakening = max(0, len(alternatives) - supporting - reversing)
    return {
        "alternative_specifications": int(alternatives["experiment_name"].nunique()),
        "supporting": supporting,
        "material_disagreements": material_disagreements,
        "weakening": weakening,
        "reversing": reversing,
    }
