from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from .utils import project_path, single_matching_file, write_dataframe


RAW_ROOT = project_path("data", "raw", "earn01")
PROCESSED_ROOT = project_path("data", "processed")


def normalise_sector_label(value: object) -> str:
    text = " ".join(str(value).replace("\n", " ").split())
    text = re.sub(r"\s+\d+(?:\s+\d+)*$", "", text)
    return text.strip()


def _find_cdid_row(df: pd.DataFrame) -> int:
    for idx, row in df.iterrows():
        if row.astype(str).str.fullmatch("CDID", case=False).any():
            return idx
    raise ValueError("Could not find EARN01 CDID row.")


def _parse_index_sheet(path: str | Path, sheet_name: str, value_name: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name, header=None)
    cdid_row = _find_cdid_row(df)
    sector_row_idx = cdid_row - 2
    sectors = df.iloc[sector_row_idx].ffill()
    data = df.iloc[cdid_row + 1 :].copy()
    date_mask = pd.to_datetime(data.iloc[:, 0], errors="coerce").notna()
    data = data.loc[date_mask]
    rows: list[dict[str, object]] = []
    for _, source_row in data.iterrows():
        date = pd.Timestamp(source_row.iloc[0]).replace(day=1)
        for col_idx in range(1, len(source_row)):
            sector = str(sectors.iloc[col_idx]).strip()
            sector = normalise_sector_label(sector)
            if sector.lower() in {"nan", ""}:
                continue
            value = pd.to_numeric(source_row.iloc[col_idx], errors="coerce")
            if pd.isna(value):
                continue
            rows.append({"date": date, "sector": sector, value_name: float(value)})
    return pd.DataFrame(rows)


def _rebase_by_sector(df: pd.DataFrame, column: str, baseline: pd.Timestamp) -> pd.Series:
    bases = (
        df.loc[df["date"].eq(baseline), ["sector", column]]
        .dropna()
        .set_index("sector")[column]
        .to_dict()
    )
    return df.apply(lambda row: row[column] / bases[row["sector"]] * 100, axis=1)


def build_earn01(raw_root: str | Path = RAW_ROOT) -> pd.DataFrame:
    source = single_matching_file(raw_root, ["**/*.xls"])
    total = _parse_index_sheet(source, "4. AWE Total Pay Index", "nominal_total_pay_index")
    regular = _parse_index_sheet(source, "5. AWE Regular Pay Index", "nominal_regular_pay_index")
    result = total.merge(regular, on=["date", "sector"], how="inner")

    inflation = pd.read_parquet(PROCESSED_ROOT / "inflation_monthly.parquet")[
        ["date", "cpih_index_jan2019_100"]
    ]
    result = result.merge(inflation, on="date", how="inner")
    baseline = pd.Timestamp("2019-01-01")
    result["nominal_total_pay_index_jan2019_100"] = _rebase_by_sector(
        result, "nominal_total_pay_index", baseline
    )
    result["nominal_regular_pay_index_jan2019_100"] = _rebase_by_sector(
        result, "nominal_regular_pay_index", baseline
    )
    result["real_total_pay_index_jan2019_100"] = (
        result["nominal_total_pay_index_jan2019_100"] / result["cpih_index_jan2019_100"] * 100
    )
    result["real_regular_pay_index_jan2019_100"] = (
        result["nominal_regular_pay_index_jan2019_100"] / result["cpih_index_jan2019_100"] * 100
    )
    result["source_file"] = source.name
    result["source_release"] = source.parent.name
    return result.sort_values(["sector", "date"]).reset_index(drop=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Clean ONS EARN01 monthly AWE data.")
    parser.parse_args(argv)
    df = build_earn01()
    output = PROCESSED_ROOT / "awe_real_monthly.parquet"
    write_dataframe(df, output)
    print(output)


if __name__ == "__main__":
    main()
