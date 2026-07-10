from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from bs4 import BeautifulSoup

from .clean_ashe import find_weekly_gross_workbook
from .clean_cpi import read_ons_timeseries_csv
from .clean_earn01 import _parse_index_sheet
from .clean_rti import parse_rti_month
from .utils import (
    clean_numeric_value,
    ensure_dir,
    normalise_age_label,
    parse_rolling_period_end,
    project_path,
    single_matching_file,
    write_dataframe,
)


RAW_ROOT = project_path("data", "raw")
PROCESSED_ROOT = project_path("data", "processed")
EVIDENCE_ROOT = project_path("outputs", "evidence")

REQUIRED_SOURCE_CHECKS = [
    "cpih_2019_april_baseline_value",
    "cpih_latest_ashe_year_april_value",
    "cpi_latest_ashe_year_april_value",
    "ashe_18_21_nominal_2019",
    "ashe_18_21_nominal_latest_ashe_year",
    "ashe_22_29_nominal_2019",
    "ashe_22_29_nominal_latest_ashe_year",
    "a05_16_24_unemployment_2019_baseline",
    "a05_16_24_unemployment_latest",
    "earn01_whole_economy_jan_2019_regular_pay_index",
    "earn01_whole_economy_latest_regular_pay_index",
    "rti_18_24_jan_2019_median_pay",
    "rti_18_24_latest_median_pay",
    "minimum_wage_18_20_2019_rate",
    "minimum_wage_18_20_2026_rate",
    "minimum_wage_adult_threshold_2019_rate",
    "minimum_wage_adult_threshold_latest_ashe_year_rate",
]

SOURCE_CHECK_COLUMNS = [
    "check_name",
    "source_dataset",
    "raw_file_path",
    "sheet_or_table",
    "row_or_series_identifier",
    "raw_value",
    "processed_value",
    "absolute_difference",
    "pass_tolerance",
    "warning_tolerance",
    "status",
    "note",
]

DEFAULT_TOLERANCE_NOTE = (
    "Numeric comparisons use raw source values against processed outputs. "
    "Each row records its pass and warning tolerances in the same unit as the checked value."
)


def _display_path(path: str | Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.resolve().relative_to(project_path().resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _status(diff: float, *, pass_tolerance: float = 0.01, warning_tolerance: float = 0.10) -> str:
    if pd.isna(diff):
        return "fail"
    if diff <= pass_tolerance:
        return "pass"
    if diff <= warning_tolerance:
        return "warning"
    return "fail"


def _record(
    *,
    check_name: str,
    source_dataset: str,
    raw_file_path: str | Path,
    sheet_or_table: str,
    row_or_series_identifier: str,
    raw_value: float,
    processed_value: float,
    note: str,
    pass_tolerance: float = 0.01,
    warning_tolerance: float = 0.10,
) -> dict[str, object]:
    diff = abs(float(raw_value) - float(processed_value))
    return {
        "check_name": check_name,
        "source_dataset": source_dataset,
        "raw_file_path": _display_path(raw_file_path),
        "sheet_or_table": sheet_or_table,
        "row_or_series_identifier": row_or_series_identifier,
        "raw_value": round(float(raw_value), 6),
        "processed_value": round(float(processed_value), 6),
        "absolute_difference": round(diff, 6),
        "pass_tolerance": pass_tolerance,
        "warning_tolerance": warning_tolerance,
        "status": _status(
            diff,
            pass_tolerance=pass_tolerance,
            warning_tolerance=warning_tolerance,
        ),
        "note": note,
    }


def _latest_ashe_year(processed_root: Path) -> int:
    ashe = pd.read_parquet(processed_root / "ashe_age_annual.parquet")
    return int(ashe["year"].max())


def _raw_inflation_value(path: Path, value_name: str, date: pd.Timestamp) -> float:
    raw = read_ons_timeseries_csv(path, value_name)
    match = raw[raw["date"].eq(date)]
    if match.empty:
        raise ValueError(f"Missing inflation raw value for {date:%Y-%m} in {path}")
    return float(match.iloc[0][value_name])


def _inflation_records(raw_root: Path, processed_root: Path, latest_ashe_year: int) -> list[dict[str, object]]:
    raw_inflation = raw_root / "inflation"
    cpih_file = single_matching_file(raw_inflation, ["**/*l522.csv"])
    cpi_file = single_matching_file(raw_inflation, ["**/*d7bt.csv"])
    annual = pd.read_parquet(processed_root / "inflation_annual.parquet").set_index("year")
    latest_date = pd.Timestamp(year=latest_ashe_year, month=4, day=1)
    return [
        _record(
            check_name="cpih_2019_april_baseline_value",
            source_dataset="ONS MM23 CPIH",
            raw_file_path=cpih_file,
            sheet_or_table="L522 time series CSV",
            row_or_series_identifier="2019 APR / CPIH L522",
            raw_value=_raw_inflation_value(cpih_file, "cpih_index", pd.Timestamp("2019-04-01")),
            processed_value=float(annual.loc[2019, "cpih_april_index"]),
            note="Checks the CPIH April baseline selected for ASHE deflation.",
        ),
        _record(
            check_name="cpih_latest_ashe_year_april_value",
            source_dataset="ONS MM23 CPIH",
            raw_file_path=cpih_file,
            sheet_or_table="L522 time series CSV",
            row_or_series_identifier=f"{latest_ashe_year} APR / CPIH L522",
            raw_value=_raw_inflation_value(cpih_file, "cpih_index", latest_date),
            processed_value=float(annual.loc[latest_ashe_year, "cpih_april_index"]),
            note="Checks the CPIH value used for the latest ASHE-year real wage comparison.",
        ),
        _record(
            check_name="cpi_latest_ashe_year_april_value",
            source_dataset="ONS MM23 CPI",
            raw_file_path=cpi_file,
            sheet_or_table="D7BT time series CSV",
            row_or_series_identifier=f"{latest_ashe_year} APR / CPI D7BT",
            raw_value=_raw_inflation_value(cpi_file, "cpi_index", latest_date),
            processed_value=float(annual.loc[latest_ashe_year, "cpi_april_index"]),
            note="Checks the CPI sensitivity deflator for the latest ASHE year.",
        ),
    ]


def _ashe_zip_for_year(raw_root: Path, year: int) -> Path:
    matches = sorted((raw_root / "ashe_age").glob(f"**/*{year}*.zip"))
    if not matches:
        raise FileNotFoundError(f"No ASHE age zip found for {year}")
    return matches[-1]


def _excel_column_name(index: int) -> str:
    result = ""
    number = index + 1
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _compact_text(value: object) -> str:
    return " ".join(str(value).strip().split())


def _raw_ashe_median_weekly(zip_path: Path, age_group: str) -> tuple[float, str, str]:
    workbook_name = find_weekly_gross_workbook(zip_path)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        with ZipFile(zip_path) as archive:
            archive.extract(workbook_name, temp_root)
        workbook_path = temp_root / workbook_name
        df = pd.read_excel(workbook_path, sheet_name="All", header=None)
    for idx, row in df.iterrows():
        values = [str(value).strip() for value in row.tolist()]
        if "Description" in values and "Median" in values:
            desc_idx = values.index("Description")
            median_idx = values.index("Median")
            data = df.iloc[idx + 1 :]
            break
    else:
        raise ValueError(f"No Description/Median header found in {zip_path}")
    for _, row in data.iterrows():
        description = str(row.iloc[desc_idx]).strip()
        if normalise_age_label(description) == age_group:
            value = clean_numeric_value(row.iloc[median_idx])
            if pd.isna(value):
                raise ValueError(f"Missing ASHE value for {age_group} in {zip_path}")
            cell = f"{_excel_column_name(median_idx)}{int(row.name) + 1}"
            return float(value), workbook_name, cell
    raise ValueError(f"No ASHE row for {age_group} in {zip_path}")


def _raw_rti_median_pay_cell(
    source: str | Path,
    *,
    age_column: str = "18 to 24",
    date: pd.Timestamp | None = None,
    latest: bool = False,
) -> dict[str, object]:
    if latest == (date is not None):
        raise ValueError("Pass exactly one of date=... or latest=True.")
    sheet_name = "29. Median pay (Age)"
    raw = pd.read_excel(source, sheet_name=sheet_name, header=None)
    header_idx = None
    date_col = None
    for idx, row in raw.iterrows():
        values = [_compact_text(value) for value in row.tolist()]
        if "Date" in values:
            header_idx = int(idx)
            date_col = values.index("Date")
            break
    if header_idx is None or date_col is None:
        raise ValueError(f"No Date header row found in {sheet_name}.")

    headers = [_compact_text(value) for value in raw.iloc[header_idx].tolist()]
    try:
        age_col = headers.index(age_column)
    except ValueError as exc:
        raise ValueError(f"No {age_column!r} column found in {sheet_name}.") from exc

    candidates: list[dict[str, object]] = []
    for row_idx, row in raw.iloc[header_idx + 1 :].iterrows():
        try:
            row_date = parse_rti_month(row.iloc[date_col])
        except ValueError:
            continue
        value = clean_numeric_value(row.iloc[age_col])
        if pd.isna(value):
            continue
        candidates.append(
            {
                "date": row_date,
                "raw_value": float(value),
                "cell": f"{_excel_column_name(age_col)}{int(row_idx) + 1}",
                "sheet_or_table": sheet_name,
                "age_column": age_column,
            }
        )
    if not candidates:
        raise ValueError(f"No RTI median pay rows found in {sheet_name}.")
    if latest:
        return max(candidates, key=lambda item: item["date"])
    assert date is not None
    target = pd.Timestamp(date)
    for candidate in candidates:
        if candidate["date"] == target:
            return candidate
    raise ValueError(f"No RTI median pay row found for {target:%Y-%m}.")


def _processed_ashe_value(processed_root: Path, *, year: int, age_group: str) -> float:
    ashe = pd.read_parquet(processed_root / "ashe_age_annual.parquet")
    row = ashe[
        ashe["year"].eq(year)
        & ashe["age_group"].eq(age_group)
        & ashe["sex"].eq("All")
        & ashe["work_status"].eq("All")
        & ashe["earnings_measure"].eq("median_weekly_gross")
    ]
    if row.empty:
        raise ValueError(f"Missing processed ASHE value for {age_group} in {year}")
    return float(row.iloc[0]["nominal_earnings"])


def _ashe_records(raw_root: Path, processed_root: Path, latest_ashe_year: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for age_group in ["18-21", "22-29"]:
        for year, suffix in [(2019, "2019"), (latest_ashe_year, "latest_ashe_year")]:
            zip_path = _ashe_zip_for_year(raw_root, year)
            raw_value, workbook_name, cell = _raw_ashe_median_weekly(zip_path, age_group)
            rows.append(
                _record(
                    check_name=f"ashe_{age_group.replace('-', '_')}_nominal_{suffix}",
                    source_dataset="ONS ASHE Table 6",
                    raw_file_path=zip_path,
                    sheet_or_table=f"{workbook_name} / sheet All",
                    row_or_series_identifier=(
                        f"{age_group}; all employees; median weekly gross pay; {year}; cell {cell}"
                    ),
                    raw_value=raw_value,
                    processed_value=_processed_ashe_value(
                        processed_root,
                        year=year,
                        age_group=age_group,
                    ),
                    note="Checks the ASHE age row, all-employee sheet, and median weekly gross column.",
                )
            )
    return rows


def _find_a05_code_row(df: pd.DataFrame) -> int:
    for idx, row in df.iterrows():
        if row.astype(str).str.contains("Dataset identifier code", case=False, regex=False).any():
            return int(idx)
    raise ValueError("Could not find A05 dataset identifier row.")


def _derive_raw_a05_16_24_unemployment(source: Path) -> pd.DataFrame:
    df = pd.read_excel(source, sheet_name="People", header=None)
    code_row = _find_a05_code_row(df)
    age_row = df.iloc[code_row - 3].ffill()
    metric_row = df.iloc[code_row - 2].ffill()
    kind_row = df.iloc[code_row - 1]
    records: list[dict[str, object]] = []
    for row_idx, source_row in df.iloc[code_row + 1 :].iterrows():
        period = str(source_row.iloc[0]).strip()
        if not re.fullmatch(r"[A-Za-z]{3}-[A-Za-z]{3}\s+\d{4}", period):
            continue
        values: dict[tuple[str, str], float] = {}
        cells: list[str] = []
        for col_idx in range(1, len(source_row)):
            age = str(age_row.iloc[col_idx]).strip()
            metric = str(metric_row.iloc[col_idx]).strip()
            kind = str(kind_row.iloc[col_idx]).strip()
            if age not in {"Aged 16-17", "Aged 18-24"}:
                continue
            if metric not in {"Unemployment", "Activity"} or kind != "level":
                continue
            value = clean_numeric_value(source_row.iloc[col_idx])
            if pd.isna(value):
                continue
            values[(age, metric)] = float(value)
            cells.append(f"{_excel_column_name(col_idx)}{int(row_idx) + 1}")
        required = {
            ("Aged 16-17", "Unemployment"),
            ("Aged 18-24", "Unemployment"),
            ("Aged 16-17", "Activity"),
            ("Aged 18-24", "Activity"),
        }
        if not required.issubset(values):
            continue
        unemployment = values[("Aged 16-17", "Unemployment")] + values[
            ("Aged 18-24", "Unemployment")
        ]
        activity = values[("Aged 16-17", "Activity")] + values[("Aged 18-24", "Activity")]
        records.append(
            {
                "period": period,
                "date": parse_rolling_period_end(period),
                "unemployment_rate": unemployment / activity * 100,
                "component_cells": ", ".join(cells),
            }
        )
    if not records:
        raise ValueError(f"No A05 component rows found in {source}")
    return pd.DataFrame(records).sort_values("date").reset_index(drop=True)


def _a05_records(raw_root: Path, processed_root: Path) -> list[dict[str, object]]:
    source = single_matching_file(raw_root / "a05", ["**/*.xls"])
    raw_a05 = _derive_raw_a05_16_24_unemployment(source)
    processed = pd.read_parquet(processed_root / "a05_age_labour_market.parquet")
    processed_focus = processed[processed["age_group"].eq("16-24")].sort_values("date")
    raw_2019 = raw_a05[raw_a05["date"].dt.year.eq(2019)]
    baseline_raw = float(raw_2019["unemployment_rate"].mean())
    baseline_processed = float(
        processed_focus[processed_focus["date"].dt.year.eq(2019)]["unemployment_rate"].mean()
    )
    latest_raw = raw_a05.iloc[-1]
    latest_processed = processed_focus.iloc[-1]
    return [
        _record(
            check_name="a05_16_24_unemployment_2019_baseline",
            source_dataset="ONS A05 SA",
            raw_file_path=source,
            sheet_or_table="People",
            row_or_series_identifier="Derived 16-24 unemployment rate, 2019 average",
            raw_value=baseline_raw,
            processed_value=baseline_processed,
            note=(
                "Independent raw derivation: mean of 2019 rolling-period rates computed as "
                "(16-17 unemployment level + 18-24 unemployment level) / "
                "(16-17 activity level + 18-24 activity level) * 100."
            ),
        ),
        _record(
            check_name="a05_16_24_unemployment_latest",
            source_dataset="ONS A05 SA",
            raw_file_path=source,
            sheet_or_table="People",
            row_or_series_identifier=f"Derived 16-24 unemployment rate, {latest_raw['period']}",
            raw_value=float(latest_raw["unemployment_rate"]),
            processed_value=float(latest_processed["unemployment_rate"]),
            note=(
                "Independent raw derivation from component cells "
                f"{latest_raw['component_cells']}: "
                "(16-17 unemployment level + 18-24 unemployment level) / "
                "(16-17 activity level + 18-24 activity level) * 100."
            ),
        ),
    ]


def _earn01_records(raw_root: Path, processed_root: Path) -> list[dict[str, object]]:
    source = single_matching_file(raw_root / "earn01", ["**/*.xls"])
    raw = _parse_index_sheet(source, "5. AWE Regular Pay Index", "nominal_regular_pay_index")
    raw_focus = raw[raw["sector"].eq("Whole Economy")].sort_values("date")
    processed = pd.read_parquet(processed_root / "awe_real_monthly.parquet")
    processed_focus = processed[processed["sector"].eq("Whole Economy")].sort_values("date")
    jan_2019 = pd.Timestamp("2019-01-01")
    raw_jan = raw_focus[raw_focus["date"].eq(jan_2019)].iloc[0]
    processed_jan = processed_focus[processed_focus["date"].eq(jan_2019)].iloc[0]
    raw_latest = raw_focus.iloc[-1]
    processed_latest = processed_focus[processed_focus["date"].eq(raw_latest["date"])].iloc[0]
    return [
        _record(
            check_name="earn01_whole_economy_jan_2019_regular_pay_index",
            source_dataset="ONS EARN01",
            raw_file_path=source,
            sheet_or_table="5. AWE Regular Pay Index",
            row_or_series_identifier="Whole Economy regular pay index, 2019-01",
            raw_value=float(raw_jan["nominal_regular_pay_index"]),
            processed_value=float(processed_jan["nominal_regular_pay_index"]),
            note="Checks the EARN01 January 2019 whole-economy regular pay index before real rebasing.",
        ),
        _record(
            check_name="earn01_whole_economy_latest_regular_pay_index",
            source_dataset="ONS EARN01",
            raw_file_path=source,
            sheet_or_table="5. AWE Regular Pay Index",
            row_or_series_identifier=(
                f"Whole Economy regular pay index, {pd.Timestamp(raw_latest['date']):%Y-%m}"
            ),
            raw_value=float(raw_latest["nominal_regular_pay_index"]),
            processed_value=float(processed_latest["nominal_regular_pay_index"]),
            note="Checks the latest EARN01 whole-economy monthly regular pay index; it is not age-specific.",
        ),
    ]


def _rti_records(raw_root: Path, processed_root: Path) -> list[dict[str, object]]:
    source = single_matching_file(raw_root / "rti", ["**/*.xlsx"])
    processed = pd.read_parquet(processed_root / "rti_age_monthly.parquet")
    focus_processed = processed[processed["age_group"].eq("18-24")].sort_values("date")
    jan_2019 = pd.Timestamp("2019-01-01")
    raw_jan = _raw_rti_median_pay_cell(source, age_column="18 to 24", date=jan_2019)
    processed_jan = focus_processed[focus_processed["date"].eq(jan_2019)].iloc[0]
    raw_latest = _raw_rti_median_pay_cell(source, age_column="18 to 24", latest=True)
    processed_latest = focus_processed[focus_processed["date"].eq(raw_latest["date"])].iloc[0]
    return [
        _record(
            check_name="rti_18_24_jan_2019_median_pay",
            source_dataset="ONS/HMRC PAYE RTI",
            raw_file_path=source,
            sheet_or_table="29. Median pay (Age)",
            row_or_series_identifier=(
                f"18 to 24 median monthly pay, 2019-01, cell {raw_jan['cell']}"
            ),
            raw_value=float(raw_jan["raw_value"]),
            processed_value=float(processed_jan["median_monthly_pay"]),
            note=(
                "Independent raw workbook spot check: reads sheet 29 directly, locates "
                "the Date row and 18 to 24 column, then checks the Jan 2019 cell."
            ),
        ),
        _record(
            check_name="rti_18_24_latest_median_pay",
            source_dataset="ONS/HMRC PAYE RTI",
            raw_file_path=source,
            sheet_or_table="29. Median pay (Age)",
            row_or_series_identifier=(
                f"18 to 24 median monthly pay, {pd.Timestamp(raw_latest['date']):%Y-%m}, "
                f"cell {raw_latest['cell']}"
            ),
            raw_value=float(raw_latest["raw_value"]),
            processed_value=float(processed_latest["median_monthly_pay"]),
            note=(
                "Independent raw workbook spot check: reads sheet 29 directly, locates "
                "the Date row and 18 to 24 column, then checks the latest available cell. "
                "The latest month is an early estimate."
            ),
        ),
    ]


def _raw_minimum_wage_rate_cell(
    html: str,
    *,
    period_label: str,
    age_band: str,
) -> dict[str, object]:
    soup = BeautifulSoup(html, "html.parser")
    for table_index, table in enumerate(soup.find_all("table"), start=1):
        headers = [cell.get_text(" ", strip=True) for cell in table.find_all("th", scope="col")]
        if age_band not in headers:
            continue
        value_index = headers.index(age_band)
        for body_row in table.find_all("tr"):
            label_cell = body_row.find("th", scope="row")
            if label_cell is None:
                continue
            label = label_cell.get_text(" ", strip=True)
            if label != period_label:
                continue
            cells = [cell.get_text(" ", strip=True) for cell in body_row.find_all("td")]
            if value_index >= len(cells):
                raise ValueError(f"No value cell for {age_band!r} in {period_label!r}.")
            numeric_text = re.sub(r"[^0-9.\-]", "", cells[value_index])
            value = clean_numeric_value(numeric_text)
            if pd.isna(value):
                raise ValueError(f"Cannot parse minimum wage value: {cells[value_index]!r}")
            return {
                "raw_value": float(value),
                "table_index": table_index,
                "period_label": period_label,
                "age_band": age_band,
            }
    raise ValueError(f"No GOV.UK minimum wage cell for {period_label!r} / {age_band!r}.")


def _read_minimum_wage_html(source: Path) -> str:
    if source.suffix.lower() == ".html":
        return source.read_text(encoding="utf-8")
    if source.suffix.lower() != ".json":
        raise ValueError(f"Unsupported GOV.UK minimum wage source format: {source.name}")
    payload = json.loads(source.read_text(encoding="utf-8"))
    details = payload.get("details")
    body = details.get("body") if isinstance(details, dict) else None
    if not isinstance(body, str) or not body.strip():
        raise ValueError(f"GOV.UK minimum wage JSON has no nonempty details.body: {source}")
    return body


def _minimum_wage_record(
    *,
    source: Path,
    processed: pd.DataFrame,
    check_name: str,
    year: int,
    policy_series: str,
    note: str,
) -> dict[str, object]:
    processed_row = processed[
        processed["effective_year"].eq(year) & processed["policy_series"].eq(policy_series)
    ].iloc[0]
    raw_cell = _raw_minimum_wage_rate_cell(
        _read_minimum_wage_html(source),
        period_label=str(processed_row["period_label"]),
        age_band=str(processed_row["age_band"]),
    )
    return _record(
        check_name=check_name,
        source_dataset="GOV.UK National Minimum Wage",
        raw_file_path=source,
        sheet_or_table="Content API details.body HTML rate tables",
        row_or_series_identifier=(
            f"{processed_row['age_band']} statutory hourly rate, "
            f"{processed_row['period_label']}, table {raw_cell['table_index']}"
        ),
        raw_value=float(raw_cell["raw_value"]),
        processed_value=float(processed_row["nominal_hourly_rate"]),
        note=f"Independent GOV.UK Content API HTML body spot check. {note}",
    )


def _minimum_wage_records(
    raw_root: Path, processed_root: Path, latest_ashe_year: int
) -> list[dict[str, object]]:
    source = single_matching_file(
        raw_root / "minimum_wage", ["**/minimum_wage.json", "**/minimum_wage.html"]
    )
    processed = pd.read_parquet(processed_root / "minimum_wage_rates.parquet")
    return [
        _minimum_wage_record(
            source=source,
            processed=processed,
            check_name="minimum_wage_18_20_2019_rate",
            year=2019,
            policy_series="18 to 20",
            note="Checks the GOV.UK 18 to 20 statutory rate used for young-worker context.",
        ),
        _minimum_wage_record(
            source=source,
            processed=processed,
            check_name="minimum_wage_18_20_2026_rate",
            year=2026,
            policy_series="18 to 20",
            note="Checks the latest GOV.UK 18 to 20 statutory rate used for young-worker context.",
        ),
        _minimum_wage_record(
            source=source,
            processed=processed,
            check_name="minimum_wage_adult_threshold_2019_rate",
            year=2019,
            policy_series="adult threshold",
            note="Checks the adult-threshold statutory rate used for the ASHE 22-29 bite context.",
        ),
        _minimum_wage_record(
            source=source,
            processed=processed,
            check_name="minimum_wage_adult_threshold_latest_ashe_year_rate",
            year=latest_ashe_year,
            policy_series="adult threshold",
            note=(
                "Checks the latest ASHE-overlap adult-threshold statutory rate used "
                "for the ASHE 22-29 bite context."
            ),
        )
    ]


def collect_source_value_checks(
    *,
    raw_root: str | Path = RAW_ROOT,
    processed_root: str | Path = PROCESSED_ROOT,
) -> list[dict[str, object]]:
    raw_root = Path(raw_root)
    processed_root = Path(processed_root)
    latest_ashe_year = _latest_ashe_year(processed_root)
    rows: list[dict[str, object]] = []
    rows.extend(_inflation_records(raw_root, processed_root, latest_ashe_year))
    rows.extend(_ashe_records(raw_root, processed_root, latest_ashe_year))
    rows.extend(_a05_records(raw_root, processed_root))
    rows.extend(_earn01_records(raw_root, processed_root))
    rows.extend(_rti_records(raw_root, processed_root))
    rows.extend(_minimum_wage_records(raw_root, processed_root, latest_ashe_year))
    missing = sorted(set(REQUIRED_SOURCE_CHECKS) - {str(row["check_name"]) for row in rows})
    if missing:
        raise ValueError(f"Missing required source checks: {missing}")
    return rows


def write_source_validation_outputs(
    records: list[dict[str, object]],
    output_root: str | Path = EVIDENCE_ROOT,
    *,
    tolerance_note: str = DEFAULT_TOLERANCE_NOTE,
) -> tuple[Path, Path]:
    output_root = ensure_dir(output_root)
    frame = pd.DataFrame(records, columns=SOURCE_CHECK_COLUMNS)
    csv_path = output_root / "source_value_checks.csv"
    write_dataframe(frame, csv_path)

    lines = [
        "# Manual Validation Audit",
        "",
        "This audit spot-checks selected final-analysis values against the downloaded raw official source files, including ONS/HMRC and GOV.UK inputs.",
        "",
        "## Tolerance",
        "",
        tolerance_note,
        "",
        "## Results",
        "",
    ]
    status_counts = frame["status"].value_counts().to_dict() if not frame.empty else {}
    lines.append(
        "Status summary: "
        + ", ".join(f"{status}={count}" for status, count in sorted(status_counts.items()))
        if status_counts
        else "Status summary: no checks were written."
    )
    lines.append("")
    for row in frame.itertuples(index=False):
        lines.extend(
            [
                f"### {row.check_name}",
                "",
                f"- Dataset: {row.source_dataset}",
                f"- Raw file: `{row.raw_file_path}`",
                f"- Sheet/table: {row.sheet_or_table}",
                f"- Row/series: {row.row_or_series_identifier}",
                f"- Raw value: {row.raw_value}",
                f"- Processed value: {row.processed_value}",
                f"- Absolute difference: {row.absolute_difference}",
                f"- Pass tolerance: {row.pass_tolerance}",
                f"- Warning tolerance: {row.warning_tolerance}",
                f"- Status: {row.status}",
                f"- Note: {row.note}",
                "",
            ]
        )
    audit_path = output_root / "manual_validation_audit.md"
    audit_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return csv_path, audit_path


def build_source_value_audit(
    *,
    raw_root: str | Path = RAW_ROOT,
    processed_root: str | Path = PROCESSED_ROOT,
    output_root: str | Path = EVIDENCE_ROOT,
) -> tuple[Path, Path]:
    records = collect_source_value_checks(raw_root=raw_root, processed_root=processed_root)
    return write_source_validation_outputs(records, output_root)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build source-value validation audit outputs.")
    parser.parse_args(argv)
    csv_path, audit_path = build_source_value_audit()
    print(csv_path)
    print(audit_path)


if __name__ == "__main__":
    main()
