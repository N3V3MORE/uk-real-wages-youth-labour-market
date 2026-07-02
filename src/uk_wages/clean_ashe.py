from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from .utils import clean_numeric_value, normalise_age_label, project_path, write_dataframe


RAW_ROOT = project_path("data", "raw", "ashe_age")
PROCESSED_ROOT = project_path("data", "processed")
ASHE_KEY_COLUMNS = ["year", "age_group", "sex", "work_status", "earnings_measure"]


def split_sheet_demographics(sheet_name: str) -> tuple[str, str]:
    if sheet_name == "All":
        return "All", "All"
    parts = sheet_name.split()
    sex = "All"
    status = "All"
    if "Male" in parts:
        sex = "Male"
    if "Female" in parts:
        sex = "Female"
    if "Full-Time" in parts:
        status = "Full-Time"
    if "Part-Time" in parts:
        status = "Part-Time"
    return sex, status


def year_from_path(path: str | Path) -> int:
    path = Path(path)
    for part in (path.name, path.parent.name):
        match = re.search(r"(20\d{2})", part)
        if match:
            return int(match.group(1))
    raise ValueError(f"Could not infer ASHE year from source filename or release folder: {path}")


def find_weekly_gross_workbook(zip_path: str | Path) -> str:
    with ZipFile(zip_path) as archive:
        matches = [
            name
            for name in archive.namelist()
            if "Weekly pay - Gross" in name
            and "CV" not in name
            and name.lower().endswith((".xls", ".xlsx"))
        ]
    if not matches:
        raise FileNotFoundError(f"No weekly gross ASHE workbook found in {zip_path}")
    return matches[0]


def _header_positions(df: pd.DataFrame) -> tuple[int, int, int, int]:
    for idx, row in df.iterrows():
        values = [str(value).strip() for value in row.tolist()]
        if "Description" in values and "Median" in values and "Mean" in values:
            return idx, values.index("Description"), values.index("Median"), values.index("Mean")
    raise ValueError("Could not find ASHE Description/Median/Mean header row.")


def _is_age_description(description: str) -> bool:
    label = normalise_age_label(description)
    return description == "All employees" or bool(re.fullmatch(r"\d{2}-\d{2}|60\+", label))


def extract_ashe_rows(
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
                if description.lower() in {"nan", ""}:
                    continue
                if not _is_age_description(description):
                    continue
                age_group = "All employees" if description == "All employees" else normalise_age_label(description)
                for measure, value_idx in {
                    "median_weekly_gross": median_idx,
                    "mean_weekly_gross": mean_idx,
                }.items():
                    value = clean_numeric_value(row.iloc[value_idx])
                    rows.append(
                        {
                            "year": year,
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
    workbook_name = find_weekly_gross_workbook(zip_path)
    year = year_from_path(zip_path)
    release = zip_path.parent.name
    temp_dir = Path(tempfile.mkdtemp())
    try:
        with ZipFile(zip_path) as archive:
            archive.extract(workbook_name, temp_dir)
        workbook_path = temp_dir / workbook_name
        return extract_ashe_rows(
            workbook_path,
            year=year,
            source_file=zip_path.name,
            source_release=release,
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def assert_unique_ashe_keys(df: pd.DataFrame) -> None:
    duplicates = df[df.duplicated(ASHE_KEY_COLUMNS, keep=False)]
    if not duplicates.empty:
        sample = duplicates[ASHE_KEY_COLUMNS].head().to_dict("records")
        raise ValueError(f"Duplicate ASHE rows found for {ASHE_KEY_COLUMNS}: {sample}")


def build_ashe_age(raw_root: str | Path = RAW_ROOT) -> pd.DataFrame:
    zip_files = sorted(Path(raw_root).glob("**/*.zip"))
    if not zip_files:
        raise FileNotFoundError(f"No ASHE age zip files found under {raw_root}")
    frames = [clean_zip(path) for path in zip_files]
    result = pd.concat(frames, ignore_index=True).sort_values(ASHE_KEY_COLUMNS)
    assert_unique_ashe_keys(result)
    return result.reset_index(drop=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Clean ASHE Table 6 age-group earnings.")
    parser.parse_args(argv)
    df = build_ashe_age()
    output = PROCESSED_ROOT / "ashe_age_annual.parquet"
    write_dataframe(df, output)
    print(output)


if __name__ == "__main__":
    main()
