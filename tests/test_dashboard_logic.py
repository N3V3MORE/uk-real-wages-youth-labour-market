from __future__ import annotations

import pandas as pd

from uk_wages.dashboard_logic import robustness_headline_metrics


def test_dashboard_headline_counts_only_core_alternatives_and_uses_canonical_score() -> None:
    matrix = pd.DataFrame(
        {
            "experiment_name": ["baseline", "alt_1", "alt_2", "alt_3", "alt_4", "alt_5", "alt_6", "stress"],
            "age_group": ["18-21"] * 8,
            "spec_tier": ["core"] * 7 + ["stress"],
            "supports_main_claim": [True, False, False, False, True, True, True, False],
            "sign_flip_vs_baseline": [False, True, True, False, False, False, False, True],
        }
    )
    scores = pd.DataFrame(
        [
            {
                "age_group": "18-21",
                "spec_tier": "core",
                "specifications_tested": 6,
                "material_disagreements": 3,
                "assessment": "not robust",
            }
        ]
    )

    metrics = robustness_headline_metrics(matrix, scores)

    assert metrics == {
        "alternatives_tested": 6,
        "supporting_alternatives": 3,
        "weakening_alternatives": 1,
        "reversing_alternatives": 2,
        "material_disagreements": 3,
        "assessment": "not robust",
    }
