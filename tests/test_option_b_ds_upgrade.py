from __future__ import annotations

from pathlib import Path

import pandas as pd

from uk_wages.option_b import (
    build_option_b_outputs,
    compute_minimum_wage_event_study,
    compute_structural_break_weights,
    forecast_ashe_real_earnings,
)
from uk_wages.pipeline import PIPELINE_MODULES


def _toy_real_age() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"year": 2019, "age_group": "18-21", "real_earnings_index_2019_100": 100.0},
            {"year": 2020, "age_group": "18-21", "real_earnings_index_2019_100": 101.0},
            {"year": 2021, "age_group": "18-21", "real_earnings_index_2019_100": 86.0},
            {"year": 2022, "age_group": "18-21", "real_earnings_index_2019_100": 87.0},
            {"year": 2023, "age_group": "18-21", "real_earnings_index_2019_100": 88.0},
            {"year": 2024, "age_group": "18-21", "real_earnings_index_2019_100": 89.0},
            {"year": 2025, "age_group": "18-21", "real_earnings_index_2019_100": 90.0},
            {"year": 2019, "age_group": "22-29", "real_earnings_index_2019_100": 100.0},
            {"year": 2020, "age_group": "22-29", "real_earnings_index_2019_100": 102.0},
            {"year": 2021, "age_group": "22-29", "real_earnings_index_2019_100": 104.0},
            {"year": 2022, "age_group": "22-29", "real_earnings_index_2019_100": 106.0},
            {"year": 2023, "age_group": "22-29", "real_earnings_index_2019_100": 108.0},
            {"year": 2024, "age_group": "22-29", "real_earnings_index_2019_100": 110.0},
            {"year": 2025, "age_group": "22-29", "real_earnings_index_2019_100": 112.0},
        ]
    )


def test_structural_break_weights_find_toy_shift() -> None:
    weights = compute_structural_break_weights(_toy_real_age())

    youngest = weights[weights["age_group"].eq("18-21")]
    assert round(float(youngest["relative_weight"].sum()), 6) == 1.0
    top = youngest.sort_values("relative_weight", ascending=False).iloc[0]
    assert int(top["break_year"]) == 2021
    assert float(top["relative_weight"]) > 0.9
    assert "relative likelihood" in str(top["model_note"])


def test_structural_break_weights_require_two_year_segments() -> None:
    weights = compute_structural_break_weights(_toy_real_age())

    assert set(weights["break_year"]) == {2021, 2022, 2023, 2024}
    assert weights["pre_years"].min() >= 2
    assert weights["post_years"].min() >= 2


def test_structural_break_weights_return_empty_schema_for_short_series() -> None:
    short = pd.DataFrame(
        [
            {"year": 2023, "age_group": "18-21", "real_earnings_index_2019_100": 98.0},
            {"year": 2024, "age_group": "18-21", "real_earnings_index_2019_100": 99.0},
        ]
    )

    weights = compute_structural_break_weights(short)

    assert weights.empty
    assert {"age_group", "break_year", "relative_weight"}.issubset(weights.columns)


def test_minimum_wage_event_study_computes_descriptive_did() -> None:
    real_age = pd.DataFrame(
        [
            {"year": 2023, "age_group": "18-21", "real_earnings_index_2019_100": 98.0},
            {"year": 2025, "age_group": "18-21", "real_earnings_index_2019_100": 101.0},
            {"year": 2023, "age_group": "22-29", "real_earnings_index_2019_100": 103.0},
            {"year": 2025, "age_group": "22-29", "real_earnings_index_2019_100": 104.0},
        ]
    )
    minimum_wage = pd.DataFrame(
        [
            {
                "effective_year": 2023,
                "policy_series": "18 to 20",
                "real_statutory_wage_index_2019_100": 106.0,
            },
            {
                "effective_year": 2023,
                "policy_series": "adult threshold",
                "real_statutory_wage_index_2019_100": 108.0,
            },
            {
                "effective_year": 2025,
                "policy_series": "18 to 20",
                "real_statutory_wage_index_2019_100": 116.0,
            },
            {
                "effective_year": 2025,
                "policy_series": "adult threshold",
                "real_statutory_wage_index_2019_100": 122.0,
            },
        ]
    )

    result = compute_minimum_wage_event_study(real_age, minimum_wage)

    row = result.iloc[0]
    assert row["treated_age_group"] == "18-21"
    assert row["comparison_age_group"] == "22-29"
    assert row["treated_change_pp"] == 3.0
    assert row["comparison_change_pp"] == 1.0
    assert row["descriptive_did_pp"] == 2.0
    assert row["wage_floor_18_to_20_change_pp"] == 10.0
    assert row["wage_floor_adult_threshold_change_pp"] == 14.0
    assert "mixed" in row["threshold_context"].lower()
    assert "not causal" in row["caveat"]


def test_forecast_baseline_returns_future_years_and_intervals() -> None:
    real_age = pd.DataFrame(
        [
            {"year": year, "age_group": "22-29", "real_earnings_index_2019_100": value}
            for year, value in [(2019, 100.0), (2020, 101.0), (2021, 102.0), (2022, 103.0)]
        ]
    )

    forecast = forecast_ashe_real_earnings(real_age, horizon=2)

    assert list(forecast["forecast_year"]) == [2023, 2024]
    assert list(forecast["forecast_index"]) == [104.0, 105.0]
    assert {
        "rough_residual_band_lower",
        "rough_residual_band_upper",
        "model",
        "caveat",
    }.issubset(forecast.columns)
    assert set(forecast["model"]) == {"linear_trend_baseline"}
    assert "rough residual band" in set(forecast["interval_note"])


def test_forecast_returns_empty_schema_for_short_series() -> None:
    short = pd.DataFrame(
        [
            {"year": 2023, "age_group": "18-21", "real_earnings_index_2019_100": 98.0},
            {"year": 2024, "age_group": "18-21", "real_earnings_index_2019_100": 99.0},
        ]
    )

    forecast = forecast_ashe_real_earnings(short)

    assert forecast.empty
    assert {
        "age_group",
        "forecast_year",
        "rough_residual_band_lower",
        "rough_residual_band_upper",
    }.issubset(forecast.columns)


def test_option_b_builder_writes_report_tables_and_notebook(tmp_path: Path) -> None:
    processed = tmp_path / "data" / "processed"
    tables = tmp_path / "outputs" / "tables"
    processed.mkdir(parents=True)
    tables.mkdir(parents=True)
    _toy_real_age().to_parquet(processed / "age_group_real_earnings.parquet", index=False)
    pd.DataFrame(
        [
            {
                "effective_year": 2023,
                "policy_series": "18 to 20",
                "real_statutory_wage_index_2019_100": 106.0,
            },
            {
                "effective_year": 2023,
                "policy_series": "adult threshold",
                "real_statutory_wage_index_2019_100": 108.0,
            },
            {
                "effective_year": 2025,
                "policy_series": "18 to 20",
                "real_statutory_wage_index_2019_100": 116.0,
            },
            {
                "effective_year": 2025,
                "policy_series": "adult threshold",
                "real_statutory_wage_index_2019_100": 122.0,
            },
        ]
    ).to_csv(tables / "minimum_wage_real_rates.csv", index=False)

    outputs = build_option_b_outputs(
        processed_root=processed,
        output_root=tmp_path / "outputs",
        notebook_root=tmp_path / "notebooks",
    )

    assert outputs["report"].exists()
    assert outputs["notebook"].exists()
    assert "Option B Modelling Diagnostics" in outputs["report"].read_text(encoding="utf-8")
    assert "Option B" in outputs["notebook"].read_text(encoding="utf-8")
    assert (tmp_path / "outputs" / "tables" / "structural_break_weights.csv").exists()
    assert (tmp_path / "outputs" / "tables" / "minimum_wage_event_study.csv").exists()
    assert (tmp_path / "outputs" / "tables" / "ashe_forecast_baseline.csv").exists()


def test_option_b_is_in_pipeline_before_final_claims() -> None:
    assert "uk_wages.option_b" in PIPELINE_MODULES
    assert PIPELINE_MODULES.index("uk_wages.option_b") < PIPELINE_MODULES.index(
        "uk_wages.final_claims"
    )
