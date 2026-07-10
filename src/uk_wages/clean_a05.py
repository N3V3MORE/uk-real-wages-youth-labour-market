from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import clean_numeric_value, parse_rolling_period_end, project_path, single_matching_file, write_dataframe


RAW_ROOT = project_path("data", "raw", "a05")
PROCESSED_ROOT = project_path("data", "processed")

AGE_LABELS = {
    "Aged 16-17": "16-17",
    "Aged 18-24": "18-24",
    "Aged 25-34": "25-34",
    "Aged 35-49": "35-49",
    "Aged 50-64": "50-64",
}
METRICS = {"Employment", "Unemployment", "Activity", "Inactivity"}


def _find_code_row(df: pd.DataFrame) -> int:
    for idx, row in df.iterrows():
        if row.astype(str).str.contains("Dataset identifier code", case=False, regex=False).any():
            return idx
    raise ValueError("Could not find A05 dataset identifier row.")


def _period_rows(df: pd.DataFrame, start_row: int) -> pd.DataFrame:
    data = df.iloc[start_row:].copy()
    mask = data.iloc[:, 0].astype(str).str.match(r"^[A-Za-z]{3}-[A-Za-z]{3}\s+\d{4}$", na=False)
    return data.loc[mask]


def _extract_long_levels(path: str | Path, sheet_name: str = "People") -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name, header=None)
    code_row = _find_code_row(df)
    age_row = df.iloc[code_row - 3].ffill()
    metric_row = df.iloc[code_row - 2].ffill()
    kind_row = df.iloc[code_row - 1]
    rows: list[dict[str, object]] = []
    for _, source_row in _period_rows(df, code_row + 1).iterrows():
        period = str(source_row.iloc[0]).strip()
        period_end = parse_rolling_period_end(period)
        for col_idx in range(1, len(source_row)):
            raw_age = str(age_row.iloc[col_idx]).strip()
            metric = str(metric_row.iloc[col_idx]).strip()
            kind = str(kind_row.iloc[col_idx]).strip()
            if raw_age not in AGE_LABELS or metric not in METRICS or kind not in {"level", "rate (%)"}:
                continue
            value = clean_numeric_value(source_row.iloc[col_idx])
            if pd.isna(value):
                continue
            rows.append(
                {
                    "period": period,
                    "date": period_end,
                    "age_group": AGE_LABELS[raw_age],
                    "metric": metric.lower(),
                    "kind": "rate" if kind == "rate (%)" else "level",
                    "value": float(value),
                }
            )
    return pd.DataFrame(rows)


def _wide_from_long(long: pd.DataFrame) -> pd.DataFrame:
    wide = (
        long.pivot_table(
            index=["period", "date", "age_group"],
            columns=["metric", "kind"],
            values="value",
            aggfunc="first",
        )
        .sort_index(axis=1)
        .reset_index()
    )
    wide.columns = [
        "_".join(part for part in column if part) if isinstance(column, tuple) else column
        for column in wide.columns
    ]
    rename = {
        "employment_rate": "employment_rate",
        "unemployment_rate": "unemployment_rate",
        "inactivity_rate": "inactivity_rate",
        "activity_rate": "activity_rate",
        "employment_level": "employment_level",
        "unemployment_level": "unemployment_level",
        "inactivity_level": "inactivity_level",
        "activity_level": "activity_level",
    }
    return wide.rename(columns=rename)


def _derive_16_24(wide: pd.DataFrame) -> pd.DataFrame:
    pieces = wide[wide["age_group"].isin(["16-17", "18-24"])].copy()
    level_cols = ["employment_level", "unemployment_level", "activity_level", "inactivity_level"]
    available = [col for col in level_cols if col in pieces.columns]
    if not available:
        return pd.DataFrame()
    aggregate = pieces.groupby(["period", "date"], as_index=False)[available].sum(min_count=1)
    aggregate["age_group"] = "16-24"
    population = aggregate["activity_level"] + aggregate["inactivity_level"]
    aggregate["employment_rate"] = aggregate["employment_level"] / population * 100
    aggregate["unemployment_rate"] = aggregate["unemployment_level"] / aggregate["activity_level"] * 100
    aggregate["inactivity_rate"] = aggregate["inactivity_level"] / population * 100
    aggregate["activity_rate"] = aggregate["activity_level"] / population * 100
    return aggregate


def add_2019_changes(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    rate_cols = ["employment_rate", "unemployment_rate", "inactivity_rate"]
    baseline = (
        result[result["date"].dt.year.eq(2019)]
        .groupby("age_group")[rate_cols]
        .mean()
        .rename(columns={col: f"{col}_2019_baseline" for col in rate_cols})
    )
    result = result.merge(baseline, on="age_group", how="left")
    for col in rate_cols:
        result[f"{col}_change_since_2019"] = result[col] - result[f"{col}_2019_baseline"]
    return result


def build_a05(raw_root: str | Path = RAW_ROOT) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = single_matching_file(raw_root, ["**/*.xls"])
    long = _extract_long_levels(source)
    wide = _wide_from_long(long)
    youth = _derive_16_24(wide)
    combined = pd.concat([wide, youth], ignore_index=True, sort=False)
    combined["source_file"] = source.name
    combined["source_release"] = source.parent.name
    combined = add_2019_changes(combined)
    combined = combined.sort_values(["date", "age_group"]).reset_index(drop=True)

    gap_base = combined[combined["age_group"].isin(["16-24", "25-34"])].pivot(
        index="date", columns="age_group", values=["unemployment_rate", "inactivity_rate"]
    )
    gaps = pd.DataFrame({"date": gap_base.index})
    gaps["youth_unemployment_gap"] = (
        gap_base[("unemployment_rate", "16-24")] - gap_base[("unemployment_rate", "25-34")]
    ).to_numpy()
    gaps["youth_inactivity_gap"] = (
        gap_base[("inactivity_rate", "16-24")] - gap_base[("inactivity_rate", "25-34")]
    ).to_numpy()
    baseline = gaps[gaps["date"].dt.year.eq(2019)][
        ["youth_unemployment_gap", "youth_inactivity_gap"]
    ].mean()
    gaps["youth_unemployment_gap_change_since_2019"] = (
        gaps["youth_unemployment_gap"] - baseline["youth_unemployment_gap"]
    )
    gaps["youth_inactivity_gap_change_since_2019"] = (
        gaps["youth_inactivity_gap"] - baseline["youth_inactivity_gap"]
    )
    return combined, gaps.reset_index(drop=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Clean ONS A05 SA labour-market data.")
    parser.parse_args(argv)
    a05, gaps = build_a05()
    output = PROCESSED_ROOT / "a05_age_labour_market.parquet"
    gap_output = project_path("outputs", "tables", "youth_labour_market_gaps.csv")
    write_dataframe(a05, output)
    write_dataframe(gaps, gap_output)
    print(output)
    print(gap_output)


if __name__ == "__main__":
    main()
