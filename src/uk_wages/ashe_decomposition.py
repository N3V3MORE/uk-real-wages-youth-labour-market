from __future__ import annotations

import argparse
import math
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from .clean_ashe import (
    _header_positions,
    _is_age_description,
    split_sheet_demographics,
    year_from_path,
)
from .utils import clean_numeric_value, normalise_age_label, project_path, write_dataframe


RAW_ROOT = project_path("data", "raw", "ashe_age")
PROCESSED_ROOT = project_path("data", "processed")
OUTPUT_TABLES = project_path("outputs", "tables")
OUTPUT_CHARTS = project_path("outputs", "charts")
EVIDENCE_ROOT = project_path("outputs", "evidence")
FOCUS_AGE_GROUPS = ["18-21", "22-29", "25-34", "30-39"]

MEASURE_PATTERNS = {
    "weekly_gross": "Weekly pay - Gross",
    "hourly_gross": "Hourly pay - Gross",
    "hourly_excluding_overtime": "Hourly pay - Excluding overtime",
    "total_paid_hours": "Paid hours worked - Total",
    "basic_paid_hours": "Paid hours worked - Basic",
}


def _find_workbook(zip_path: str | Path, pattern: str) -> str | None:
    with ZipFile(zip_path) as archive:
        matches = [
            name
            for name in archive.namelist()
            if pattern in name and "CV" not in name and name.lower().endswith((".xls", ".xlsx"))
        ]
    return matches[0] if matches else None


def inspect_ashe_decomposition_availability(raw_root: str | Path = RAW_ROOT) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for zip_path in sorted(Path(raw_root).glob("**/*.zip")):
        year = year_from_path(zip_path)
        for measure, pattern in MEASURE_PATTERNS.items():
            workbook = _find_workbook(zip_path, pattern)
            rows.append(
                {
                    "year": year,
                    "source_file": zip_path.name,
                    "source_release": zip_path.parent.name,
                    "measure": measure,
                    "pattern_checked": pattern,
                    "available": workbook is not None,
                    "workbook": workbook or "",
                }
            )
    return pd.DataFrame(rows).sort_values(["year", "measure"]).reset_index(drop=True)


def _extract_measure_rows(
    workbook_path: str | Path,
    *,
    year: int,
    source_file: str,
    source_release: str,
    measure: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    excel = pd.ExcelFile(workbook_path)
    try:
        for sheet_name in excel.sheet_names:
            if sheet_name.lower().startswith("notes"):
                continue
            sex, work_status = split_sheet_demographics(sheet_name)
            if sex != "All" or work_status != "All":
                continue
            df = pd.read_excel(workbook_path, sheet_name=sheet_name, header=None)
            header_row, desc_idx, median_idx, _ = _header_positions(df)
            for _, row in df.iloc[header_row + 1 :].iterrows():
                description = str(row.iloc[desc_idx]).strip()
                if description.lower() in {"nan", ""} or not _is_age_description(description):
                    continue
                age_group = (
                    "All employees"
                    if description == "All employees"
                    else normalise_age_label(description)
                )
                if age_group not in FOCUS_AGE_GROUPS:
                    continue
                value = clean_numeric_value(row.iloc[median_idx])
                rows.append(
                    {
                        "year": year,
                        "age_group": age_group,
                        "measure": measure,
                        "median_value": value,
                        "source_file": source_file,
                        "source_release": source_release,
                    }
                )
    finally:
        excel.close()
    result = pd.DataFrame(rows)
    if not result.empty:
        result["median_value"] = pd.to_numeric(result["median_value"], errors="coerce")
        result = result.dropna(subset=["median_value"])
    return result


def parse_decomposition_zip(zip_path: str | Path) -> pd.DataFrame:
    zip_path = Path(zip_path)
    year = year_from_path(zip_path)
    release = zip_path.parent.name
    rows: list[pd.DataFrame] = []
    temp_dir = Path(tempfile.mkdtemp())
    try:
        with ZipFile(zip_path) as archive:
            for measure, pattern in MEASURE_PATTERNS.items():
                workbook = _find_workbook(zip_path, pattern)
                if workbook is None:
                    continue
                archive.extract(workbook, temp_dir)
                rows.append(
                    _extract_measure_rows(
                        temp_dir / workbook,
                        year=year,
                        source_file=zip_path.name,
                        source_release=release,
                        measure=measure,
                    )
                )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _availability_problem(availability: pd.DataFrame) -> str | None:
    if availability.empty:
        return f"No ASHE age zip files were found under {RAW_ROOT}."
    required = {"weekly_gross", "hourly_gross", "total_paid_hours"}
    missing = availability[
        availability["measure"].isin(required) & ~availability["available"].astype(bool)
    ]
    if not missing.empty:
        sample = missing[["year", "measure", "source_file"]].to_dict("records")
        return f"Missing required ASHE workbooks: {sample}"
    return None


def compute_decomposition(
    raw: pd.DataFrame,
    inflation_annual: pd.DataFrame,
    *,
    baseline_year: int = 2019,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    wide = (
        raw.pivot_table(
            index=["year", "age_group", "source_file", "source_release"],
            columns="measure",
            values="median_value",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    required = ["weekly_gross", "hourly_gross", "total_paid_hours"]
    missing_cols = [column for column in required if column not in wide.columns]
    if missing_cols:
        raise ValueError(f"Missing decomposition columns: {missing_cols}")
    price = inflation_annual[["year", "cpih_index_2019_100"]]
    joined = wide.merge(price, on="year", how="inner")
    base = (
        joined[joined["year"].eq(baseline_year)]
        .set_index("age_group")[["weekly_gross", "hourly_gross", "total_paid_hours"]]
        .to_dict("index")
    )
    joined = joined[joined["age_group"].isin(base)].copy()
    joined["real_weekly_earnings_index_2019_100"] = joined.apply(
        lambda row: row["weekly_gross"]
        / base[row["age_group"]]["weekly_gross"]
        * 100
        / row["cpih_index_2019_100"]
        * 100,
        axis=1,
    )
    joined["real_hourly_earnings_index_2019_100"] = joined.apply(
        lambda row: row["hourly_gross"]
        / base[row["age_group"]]["hourly_gross"]
        * 100
        / row["cpih_index_2019_100"]
        * 100,
        axis=1,
    )
    joined["hours_index_2019_100"] = joined.apply(
        lambda row: row["total_paid_hours"] / base[row["age_group"]]["total_paid_hours"] * 100,
        axis=1,
    )
    joined["weekly_log_change"] = joined["real_weekly_earnings_index_2019_100"].apply(
        lambda value: math.log(float(value) / 100)
    )
    joined["hourly_log_contribution"] = joined["real_hourly_earnings_index_2019_100"].apply(
        lambda value: math.log(float(value) / 100)
    )
    joined["hours_log_contribution"] = joined["hours_index_2019_100"].apply(
        lambda value: math.log(float(value) / 100)
    )
    joined["residual_log_contribution"] = (
        joined["weekly_log_change"]
        - joined["hourly_log_contribution"]
        - joined["hours_log_contribution"]
    )
    joined["residual_abs_log_contribution"] = joined["residual_log_contribution"].abs()

    latest_rows: list[dict[str, object]] = []
    for age_group, group in joined.groupby("age_group"):
        ordered = group.sort_values("year")
        latest = ordered.iloc[-1]
        weekly_log = float(latest["weekly_log_change"])
        hourly_log = float(latest["hourly_log_contribution"])
        hours_log = float(latest["hours_log_contribution"])
        residual = float(latest["residual_log_contribution"])
        latest_rows.append(
            {
                "age_group": age_group,
                "baseline_year": baseline_year,
                "latest_year": int(latest["year"]),
                "real_weekly_earnings_index_2019_100": round(
                    float(latest["real_weekly_earnings_index_2019_100"]), 4
                ),
                "real_hourly_earnings_index_2019_100": round(
                    float(latest["real_hourly_earnings_index_2019_100"]), 4
                ),
                "hours_index_2019_100": round(float(latest["hours_index_2019_100"]), 4),
                "weekly_log_change": round(weekly_log, 6),
                "hourly_log_contribution": round(hourly_log, 6),
                "hours_log_contribution": round(hours_log, 6),
                "residual_log_contribution": round(residual, 6),
                "weekly_pct_change": round(
                    float(latest["real_weekly_earnings_index_2019_100"]) - 100, 2
                ),
                "hourly_pct_change": round(
                    float(latest["real_hourly_earnings_index_2019_100"]) - 100, 2
                ),
                "hours_pct_change": round(float(latest["hours_index_2019_100"]) - 100, 2),
            }
        )
    latest_table = pd.DataFrame(latest_rows).sort_values("age_group").reset_index(drop=True)
    return joined.sort_values(["age_group", "year"]).reset_index(drop=True), latest_table


def _plt():
    import matplotlib.pyplot as plt

    return plt


def chart_decomposition(summary: pd.DataFrame) -> None:
    plt = _plt()
    plot = summary.set_index("age_group")[
        ["hourly_log_contribution", "hours_log_contribution", "residual_log_contribution"]
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    plot.plot(kind="bar", stacked=True, ax=ax, color=["#3d7f5b", "#4b6fb4", "#777777"])
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("ASHE Weekly Pay Decomposition by Age")
    ax.set_ylabel("Log-point contribution since 2019")
    ax.set_xlabel("Age group")
    ax.legend(["Hourly pay", "Hours", "Residual"], fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.text(
        0.01,
        0.01,
        "Source: ONS ASHE Table 6 and MM23. Decomposition uses medians and is descriptive, not causal.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    OUTPUT_CHARTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_CHARTS / "weekly_pay_decomposition_by_age.png", dpi=180, bbox_inches="tight")
    fig.savefig(OUTPUT_CHARTS / "weekly_pay_decomposition_by_age.svg", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_decomposition_report(
    availability: pd.DataFrame,
    summary: pd.DataFrame | None,
    *,
    annual: pd.DataFrame | None = None,
    problem: str | None = None,
    evidence_root: str | Path = EVIDENCE_ROOT,
) -> Path:
    evidence_root = Path(evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ASHE Hourly Pay and Hours Decomposition",
        "",
        "This module checks whether weekly earnings changes line up more with hourly pay or paid hours. It is a decomposition of published medians, not a causal estimate.",
        "",
        "## Availability Check",
        "",
    ]
    if availability.empty:
        lines.append("No ASHE source zips were available to inspect.")
    else:
        checked = availability.groupby("measure")["available"].all().to_dict()
        for measure, available in checked.items():
            lines.append(f"- {measure}: {'available' if available else 'missing in at least one year'}")
    computed_groups = (
        sorted(summary["age_group"].astype(str).unique()) if summary is not None and not summary.empty else []
    )
    missing_focus_groups = [group for group in FOCUS_AGE_GROUPS if group not in computed_groups]
    lines.extend(
        [
            "",
            "## Requested Focus Groups",
            "",
            f"Requested ASHE decomposition groups: {', '.join(FOCUS_AGE_GROUPS)}.",
            f"Computed decomposition groups: {', '.join(computed_groups) if computed_groups else 'none'}.",
        ]
    )
    if missing_focus_groups:
        lines.append(f"Unavailable requested groups: {', '.join(missing_focus_groups)}.")
        for group in missing_focus_groups:
            lines.append(
                f"- {group}: unavailable in the parsed ASHE Table 6 age rows for the required weekly, hourly, and hours measures, so no decomposition row is calculated or fabricated."
            )
    if problem:
        lines.extend(["", "## Result", "", problem, ""])
    elif summary is not None and not summary.empty:
        lines.extend(["", "## Result", ""])
        for row in summary.itertuples(index=False):
            total = row.weekly_log_change
            parts = (
                row.hourly_log_contribution
                + row.hours_log_contribution
                + row.residual_log_contribution
            )
            lines.append(
                f"- {row.age_group}: real weekly earnings changed by {row.weekly_pct_change:.2f}%. "
                f"Hourly pay contributes {row.hourly_log_contribution:.3f} log points; "
                f"hours contribute {row.hours_log_contribution:.3f}; residual {row.residual_log_contribution:.3f}. "
                f"Contribution check: {parts:.3f} versus total {total:.3f}."
            )
        lines.extend(
            [
                "",
                "## Residual Diagnostics",
                "",
            ]
        )
        if annual is None or annual.empty or "residual_abs_log_contribution" not in annual.columns:
            lines.append("No year-by-year residual diagnostics table was available.")
        else:
            for age_group, age_rows in annual.sort_values("year").groupby("age_group"):
                largest = age_rows.sort_values(
                    "residual_abs_log_contribution", ascending=False
                ).iloc[0]
                baseline = age_rows.sort_values("year").iloc[0]
                lines.append(
                    f"- {age_group}: maximum absolute residual is "
                    f"{float(largest['residual_abs_log_contribution']):.3f} log points "
                    f"in {int(largest['year'])}; baseline-year residual is "
                    f"{float(baseline['residual_log_contribution']):.3f}."
                )
        lines.extend(
            [
                "",
                "A residual is expected because the calculation compares medians from separate ASHE tables. It should not be read as an unexplained causal factor.",
                "",
            ]
        )
    path = evidence_root / "ashe_decomposition_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_ashe_decomposition(raw_root: str | Path = RAW_ROOT) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    availability = inspect_ashe_decomposition_availability(raw_root)
    problem = _availability_problem(availability)
    if problem:
        write_decomposition_report(availability, None, problem=problem)
        return availability, None
    frames = [parse_decomposition_zip(path) for path in sorted(Path(raw_root).glob("**/*.zip"))]
    raw = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if raw.empty:
        problem = "ASHE workbooks were found, but no focus age-group rows could be parsed."
        write_decomposition_report(availability, None, problem=problem)
        return availability, None
    inflation = pd.read_parquet(PROCESSED_ROOT / "inflation_annual.parquet")
    annual, summary = compute_decomposition(raw, inflation)
    write_dataframe(annual, PROCESSED_ROOT / "ashe_age_hours_decomposition.parquet")
    write_dataframe(annual, OUTPUT_TABLES / "ashe_hours_decomposition_timeseries.csv")
    write_dataframe(summary, OUTPUT_TABLES / "ashe_hours_decomposition.csv")
    chart_decomposition(summary)
    write_decomposition_report(availability, summary, annual=annual)
    return availability, summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build ASHE hourly-pay and hours decomposition.")
    parser.parse_args(argv)
    _, summary = build_ashe_decomposition()
    if summary is None:
        print(EVIDENCE_ROOT / "ashe_decomposition_report.md")
    else:
        print(OUTPUT_TABLES / "ashe_hours_decomposition.csv")


if __name__ == "__main__":
    main()
