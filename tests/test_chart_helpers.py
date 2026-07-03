from __future__ import annotations

import pandas as pd

from uk_wages.charts import _date_range, _year_range


def test_chart_helpers_format_year_and_month_ranges() -> None:
    annual = pd.DataFrame({"year": [2025, 2019, 2021]})
    monthly = pd.DataFrame({"date": pd.to_datetime(["2026-06-30", "2026-04-30"])})

    assert _year_range(annual) == "2019-2025"
    assert _date_range(monthly) == "Apr 2026-Jun 2026"
