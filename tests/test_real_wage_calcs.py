from __future__ import annotations

import pandas as pd
import pytest

from uk_wages.analysis import _approx_two_cv_band, compute_real_earnings_by_age, real_wage_index, summarise_age_changes
from uk_wages.utils import parse_ons_month_period


def test_real_wage_formula_matches_project_definition() -> None:
    assert round(real_wage_index(120, 110), 2) == 109.09


def test_2019_real_earnings_index_is_100_for_each_age_group() -> None:
    ashe = pd.DataFrame(
        {
            "year": [2019, 2020, 2019, 2020],
            "age_group": ["18-21", "18-21", "22-29", "22-29"],
            "nominal_earnings": [100.0, 110.0, 200.0, 220.0],
        }
    )
    inflation = pd.DataFrame(
        {
            "year": [2019, 2020],
            "cpih_index_2019_100": [100.0, 105.0],
            "cpi_index_2019_100": [100.0, 106.0],
        }
    )

    result = compute_real_earnings_by_age(ashe, inflation)

    baseline = result[result["year"].eq(2019)]
    assert set(baseline["age_group"]) == {"18-21", "22-29"}
    assert baseline["real_earnings_index_2019_100"].tolist() == [100.0, 100.0]


def test_summary_table_required_fields_are_not_missing() -> None:
    real_age = pd.DataFrame(
        {
            "year": [2019, 2021],
            "age_group": ["18-21", "18-21"],
            "nominal_earnings": [100.0, 125.0],
            "nominal_pct_change_since_2019": [0.0, 25.0],
            "inflation_pct_change_since_2019": [0.0, 10.0],
            "real_pct_change_since_2019": [0.0, 13.64],
            "real_pct_change_cpi_since_2019": [0.0, 12.5],
        }
    )

    summary = summarise_age_changes(real_age)

    assert summary[["age_group", "latest_year", "real_pct_change"]].isna().sum().sum() == 0
    assert summary.loc[0, "real_gain_or_loss"] == "gain"


def test_monthly_cpih_dates_parse_to_first_of_month() -> None:
    assert parse_ons_month_period("2019 JAN") == pd.Timestamp("2019-01-01")


@pytest.mark.parametrize("problem", ["missing_price", "duplicate_age", "zero_baseline", "missing_baseline"])
def test_real_earnings_rejects_invalid_inputs(problem: str) -> None:
    ashe = pd.DataFrame({"year": [2019, 2020], "age_group": ["18-21"] * 2, "nominal_earnings": [100., 110.]})
    inflation = pd.DataFrame({"year": [2019, 2020], "cpih_index_2019_100": [100., 105.], "cpi_index_2019_100": [100., 106.]})
    if problem == "missing_price":
        inflation = inflation.iloc[:1]
    elif problem == "duplicate_age":
        ashe = pd.concat([ashe, ashe.iloc[:1]])
    elif problem == "zero_baseline":
        ashe.loc[0, "nominal_earnings"] = 0
    else:
        ashe = ashe.iloc[1:]
    with pytest.raises(ValueError):
        compute_real_earnings_by_age(ashe, inflation)


def test_fixed_2019_output_names_reject_other_baselines() -> None:
    with pytest.raises(ValueError, match="experiment runner"):
        compute_real_earnings_by_age(pd.DataFrame(), pd.DataFrame(), baseline_year=2020)


def test_cv_band_scales_relative_error_to_percentage_points() -> None:
    # A ratio of 2 with 3% and 4% CVs has a 10 pp SE and a 20 pp two-CV margin.
    assert _approx_two_cv_band(100., 3., 4.) == (80., 120., False, 20.)
