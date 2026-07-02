from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from .clean_ashe import _header_positions, split_sheet_demographics, year_from_path
from .utils import clean_numeric_value, normalise_age_label, project_path, write_dataframe


RAW_ROOT = project_path("data", "raw", "ashe_region_age")
PROCESSED_ROOT = project_path("data", "processed")
REGION_KEY_COLUMNS = ["year", "region", "age_group", "sex", "work_status", "earnings_measure"]


def find_region_weekly_gross_workbook(zip_path: str | Path) -> str:
    with ZipFile(zip_path) as archive:
        matches = [
            name
            for name in archive.namelist()
            if "Weekly pay - Gross" in name
            and "CV" not in name
            and name.lower().endswith((".xls", ".xlsx"))
        ]
    if not matches:
        raise FileNotFoundError(f"No region-age weekly gross workbook found in {zip_path}")
    return matches[0]


def _parse_region_age(description: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"(.+),\s+Age\s+(.+)", description.strip())
    if not match:
        return None
    region = match.group(1).strip()
    age_group = normalise_age_label(match.group(2))
    return region, age_group


def extract_region_ashe_rows(
    workbook_path: str | Path,
    *,
    year: int,
    source_file: str,
    source_release: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    excel = pd.ExcelFile(workbook_path)
    try:
        for sheet_name in excel.sheet_names:
            if sheet_name.lower().startswith("notes"):
                continue
            sex, work_status = split_sheet_demographics(sheet_name)
            df = pd.read_excel(workbook_path, sheet_name=sheet_name, header=None)
            header_row, desc_idx, median_idx, mean_idx = _header_positions(df)
            for _, row in df.iloc[header_row + 1 :].iterrows():
                description = str(row.iloc[desc_idx]).strip()
                parsed = _parse_region_age(description)
                if parsed is None:
                    continue
                region, age_group = parsed
                for measure, value_idx in {
                    "median_weekly_gross": median_idx,
                    "mean_weekly_gross": mean_idx,
                }.items():
                    value = clean_numeric_value(row.iloc[value_idx])
                    rows.append(
                        {
                            "year": year,
                            "region": region,
                            "age_group": age_group,
                            "sex": sex,
                            "work_status": work_status,
                            "earnings_measure": measure,
                            "nominal_earnings": value,
                            "unit": "GBP per week",
                            "source_file": source_file,
                            "source_release": source_release,
                        }
                    )
    finally:
        excel.close()
    result = pd.DataFrame(rows)
    result["nominal_earnings"] = pd.to_numeric(result["nominal_earnings"], errors="coerce")
    return result.dropna(subset=["nominal_earnings"]).reset_index(drop=True)


def clean_zip(zip_path: str | Path) -> pd.DataFrame:
    zip_path = Path(zip_path)
    workbook_name = find_region_weekly_gross_workbook(zip_path)
    year = year_from_path(zip_path)
    release = zip_path.parent.name
    temp_dir = Path(tempfile.mkdtemp())
    try:
        with ZipFile(zip_path) as archive:
            archive.extract(workbook_name, temp_dir)
        workbook_path = temp_dir / workbook_name
        return extract_region_ashe_rows(
            workbook_path,
            year=year,
            source_file=zip_path.name,
            source_release=release,
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def assert_unique_region_keys(df: pd.DataFrame) -> None:
    duplicates = df[df.duplicated(REGION_KEY_COLUMNS, keep=False)]
    if not duplicates.empty:
        sample = duplicates[REGION_KEY_COLUMNS].head().to_dict("records")
        raise ValueError(f"Duplicate region ASHE rows found: {sample}")


def build_region_ashe(raw_root: str | Path = RAW_ROOT) -> pd.DataFrame:
    zip_files = sorted(Path(raw_root).glob("**/*.zip"))
    if not zip_files:
        raise FileNotFoundError(f"No region ASHE zip files found under {raw_root}")
    frames = [clean_zip(path) for path in zip_files]
    result = pd.concat(frames, ignore_index=True).sort_values(REGION_KEY_COLUMNS)
    assert_unique_region_keys(result)
    return result.reset_index(drop=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Clean regional ASHE age-group earnings.")
    parser.parse_args(argv)
    df = build_region_ashe()
    output = PROCESSED_ROOT / "ashe_region_age_annual.parquet"
    write_dataframe(df, output)
    print(output)


if __name__ == "__main__":
    main()
