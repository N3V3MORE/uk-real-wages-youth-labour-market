from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pandas as pd

from .utils import parse_ons_month_period, project_path, write_dataframe


RAW_ROOT = project_path("data", "raw", "inflation")
PROCESSED_ROOT = project_path("data", "processed")


def read_ons_timeseries_csv(path: str | Path, value_name: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for raw in reader:
            if len(raw) < 2:
                continue
            period = raw[0].strip()
            value = raw[1].strip()
            if not re.fullmatch(r"\d{4}\s+[A-Z]{3}", period.upper()):
                continue
            rows.append({"date": parse_ons_month_period(period), value_name: float(value)})
    if not rows:
        raise ValueError(f"No monthly rows found in {path}")
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def build_inflation_outputs(raw_root: str | Path = RAW_ROOT) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_root = Path(raw_root)
    cpih_file = max(raw_root.glob("**/*l522.csv"), key=lambda path: path.stat().st_mtime)
    cpi_file = max(raw_root.glob("**/*d7bt.csv"), key=lambda path: path.stat().st_mtime)

    cpih = read_ons_timeseries_csv(cpih_file, "cpih_index")
    cpi = read_ons_timeseries_csv(cpi_file, "cpi_index")
    monthly = cpih.merge(cpi, on="date", how="inner")
    monthly["year"] = monthly["date"].dt.year
    monthly["month"] = monthly["date"].dt.month

    jan_2019 = monthly.loc[monthly["date"].eq(pd.Timestamp("2019-01-01"))].iloc[0]
    monthly["cpih_index_jan2019_100"] = monthly["cpih_index"] / jan_2019["cpih_index"] * 100
    monthly["cpi_index_jan2019_100"] = monthly["cpi_index"] / jan_2019["cpi_index"] * 100
    monthly["cpih_index_2019_100"] = monthly["cpih_index_jan2019_100"]
    monthly["cpi_index_2019_100"] = monthly["cpi_index_jan2019_100"]

    april = monthly.loc[monthly["month"].eq(4), ["year", "cpih_index", "cpi_index"]].rename(
        columns={"cpih_index": "cpih_april_index", "cpi_index": "cpi_april_index"}
    )
    annual_avg = (
        monthly.groupby("year", as_index=False)[["cpih_index", "cpi_index"]]
        .mean()
        .rename(
            columns={
                "cpih_index": "cpih_calendar_year_avg",
                "cpi_index": "cpi_calendar_year_avg",
            }
        )
    )
    annual = april.merge(annual_avg, on="year", how="inner")
    base = annual.loc[annual["year"].eq(2019)].iloc[0]
    annual["cpih_index_2019_100"] = annual["cpih_april_index"] / base["cpih_april_index"] * 100
    annual["cpi_index_2019_100"] = annual["cpi_april_index"] / base["cpi_april_index"] * 100
    annual["cpih_calendar_index_2019_100"] = (
        annual["cpih_calendar_year_avg"] / base["cpih_calendar_year_avg"] * 100
    )
    annual["cpi_calendar_index_2019_100"] = (
        annual["cpi_calendar_year_avg"] / base["cpi_calendar_year_avg"] * 100
    )
    return monthly, annual


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Clean ONS MM23 CPIH/CPI time series.")
    parser.parse_args(argv)
    monthly, annual = build_inflation_outputs()
    write_dataframe(monthly, PROCESSED_ROOT / "inflation_monthly.parquet")
    write_dataframe(annual, PROCESSED_ROOT / "inflation_annual.parquet")
    print(PROCESSED_ROOT / "inflation_monthly.parquet")
    print(PROCESSED_ROOT / "inflation_annual.parquet")


if __name__ == "__main__":
    main()

