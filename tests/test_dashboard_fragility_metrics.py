from __future__ import annotations

import pandas as pd

from dashboard.fragility_metrics import fragility_card_counts


def test_fragility_card_counts_exclude_baseline_from_alternative_counts() -> None:
    matrix = pd.DataFrame(
        {
            "experiment_name": [
                "baseline",
                "sensitivity_cpi",
                "sensitivity_full_time_only",
                "sensitivity_base_2020",
            ],
            "age_group": ["18-21", "18-21", "18-21", "18-21"],
            "supports_main_claim": [True, True, False, False],
            "sign_flip_vs_baseline": [False, False, False, True],
            "material_disagreement": [False, True, True, True],
        }
    )

    counts = fragility_card_counts(matrix, age_group="18-21")

    assert counts == {
        "alternative_specifications": 3,
        "supporting": 1,
        "material_disagreements": 3,
        "weakening": 1,
        "reversing": 1,
    }
