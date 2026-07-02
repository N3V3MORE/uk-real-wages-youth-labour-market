from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from .utils import project_path, single_matching_file, write_dataframe


RAW_ROOT = project_path("data", "raw", "rti")
PROCESSED_ROOT = project_path("data", "processed")
AGE_GROUPS = ["Under 18", "18-24", "25-34", "35-49", "50-64", "65+"]


def normalise_rti_age_group(value: object) -> str:
    text = " ".join(str(value).strip().split())
    replacements = {
        "0 to 17": "Under 18",
        "18 to 24": "18-24",
        "25 to 34": "25-34",
        "35 to 49": "35-49",
        "50 to 64": "50-64",
        "65 and over": "65+",
    }
    return replacements.get(text, text)


def parse_rti_month(value: object) -> pd.Timestamp:
    parsed = pd.to_datetime(str(value).strip(), format="%B %Y", errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Cannot parse RTI month: {value!r}")
    return pd.Timestamp(parsed).replace(day=1)


def extract_release_date(path: str | Path) -> str:
    df = pd.read_excel(path, sheet_name="Index", header=None, nrows=3)
    for value in df.iloc[:, 0].dropna():
        text = str(value)
        match = re.search(r"Date of publication:\s*(.+)$", text)
        if match:
            return pd.Timestamp(match.group(1)).date().isoformat()
    return ""


def _header_row(df: pd.DataFrame) -> int:
    for idx, row in df.iterrows():
        if row.astype(str).str.strip().eq("Date").any():
            return int(idx)
    raise ValueError("Could not find RTI Date header row.")


def _read_age_sheet(path: str | Path, sheet_name: str, value_name: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    header_idx = _header_row(raw)
    headers = raw.iloc[header_idx].tolist()
    data = raw.iloc[header_idx + 1 :].copy()
    data.columns = headers
    data = data[pd.to_datetime(data["Date"], format="%B %Y", errors="coerce").notna()]
    rows: list[dict[str, object]] = []
    for _, source_row in data.iterrows():
        date = parse_rti_month(source_row["Date"])
        for column in data.columns:
            if column == "Date":
                continue
            age_group = normalise_rti_age_group(column)
            if age_group not in AGE_GROUPS:
                continue
            value = pd.to_numeric(source_row[column], errors="coerce")
            if pd.isna(value):
                continue
            rows.append({"date": date, "age_group": age_group, value_name: float(value)})
    return pd.DataFrame(rows)


def parse_rti_age_workbook(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    employees = _read_age_sheet(path, "28. Employees (Age)", "payrolled_employees")
    pay = _read_age_sheet(path, "29. Median pay (Age)", "median_monthly_pay")
    result = employees.merge(pay, on=["date", "age_group"], how="inner")
    if result.empty:
        raise ValueError(f"No RTI age rows parsed from {path}")
    latest_date = result["date"].max()
    result["seasonal_adjustment_status"] = "seasonally adjusted"
    result["flash_or_provisional_flag"] = result["date"].eq(latest_date)
    result["source_file"] = path.name
    result["source_release_date"] = extract_release_date(path)
    return result.sort_values(["age_group", "date"]).reset_index(drop=True)


def build_rti_age_monthly(raw_root: str | Path = RAW_ROOT) -> pd.DataFrame:
    source = single_matching_file(raw_root, ["**/*.xlsx"])
    return parse_rti_age_workbook(source)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Clean PAYE RTI age-specific monthly pay data.")
    parser.parse_args(argv)
    df = build_rti_age_monthly()
    output = PROCESSED_ROOT / "rti_age_monthly.parquet"
    write_dataframe(df, output)
    print(output)


if __name__ == "__main__":
    main()
