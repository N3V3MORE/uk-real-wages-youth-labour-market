from __future__ import annotations

import pandas as pd

from uk_wages.analysis import compute_real_earnings_by_age, real_wage_index, summarise_age_changes
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
