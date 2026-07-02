from __future__ import annotations

import argparse
import io
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from .clean_ashe import (
    _header_positions,
    _is_age_description,
    split_sheet_demographics,
    year_from_path,
)
from .utils import clean_numeric_value, ensure_dir, normalise_age_label, project_path, write_dataframe


AGE_RAW_ROOT = project_path("data", "raw", "ashe_age")
REGION_AGE_RAW_ROOT = project_path("data", "raw", "ashe_region_age")
PROCESSED_ROOT = project_path("data", "processed")
OUTPUT_ROOT = project_path("outputs")
FOCUS_AGE_GROUPS = ["18-21", "22-29", "30-39"]

MEASURE_PATTERNS = {
    "weekly_gross": "Weekly pay - Gross",
    "weekly_excluding_overtime": "Weekly pay - Excluding overtime",
    "basic_pay_including_other": "Basic Pay - Including other pay",
    "overtime_pay": "Overtime pay",
    "hourly_gross": "Hourly pay - Gross",
    "hourly_excluding_overtime": "Hourly pay - Excluding overtime",
    "annual_gross": "Annual pay - Gross",
    "annual_incentive": "Annual pay - Incentive",
    "total_paid_hours": "Paid hours worked - Total",
    "basic_paid_hours": "Paid hours worked - Basic",
    "overtime_paid_hours": "Paid hours worked - Overtime",
}

FLAG_COLUMNS = [
    "year",
    "source_family",
    "source_file",
    "source_release",
    "workbook",
    "sheet_name",
    "measure",
    "region",
    "age_group",
    "sex",
    "work_status",
    "estimate",
    "raw_marker",
    "cv_percent",
    "quality_status",
    "usable_quality_evidence",
    "note",
]


def _measure_from_member(member_name: str) -> str:
    lower = member_name.lower()
    for measure, pattern in MEASURE_PATTERNS.items():
        if pattern.lower() in lower:
            return measure
    return "unknown"


def _evidence_type(member_name: str) -> str:
    lower = member_name.lower()
    if "cv" in lower or "coefficients of variation" in lower:
        return "coefficient_of_variation"
    if "confidence" in lower:
        return "confidence_interval"
    if "standard error" in lower or "standard_error" in lower:
        return "standard_error"
    if "quality" in lower or "reliab" in lower:
        return "quality_marker"
    if "suppress" in lower:
        return "suppression_marker"
    if "note" in lower:
        return "quality_note"
    return "none"


def _is_quality_member(member_name: str) -> bool:
    return _evidence_type(member_name) != "none" and member_name.lower().endswith(
        (".xls", ".xlsx")
    )


def _excel_from_zip(zip_path: Path, member_name: str) -> pd.ExcelFile:
    with ZipFile(zip_path) as archive:
        payload = io.BytesIO(archive.read(member_name))
    return pd.ExcelFile(payload)


def _sheet_names(zip_path: Path, member_name: str) -> list[str]:
    excel = _excel_from_zip(zip_path, member_name)
    try:
        return list(excel.sheet_names)
    finally:
        excel.close()


def inspect_ashe_quality_archives(
    *,
    age_raw_root: str | Path = AGE_RAW_ROOT,
    region_age_raw_root: str | Path = REGION_AGE_RAW_ROOT,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    roots = [
        ("ashe_age", Path(age_raw_root)),
        ("ashe_region_age", Path(region_age_raw_root)),
    ]
    for source_family, root in roots:
        for zip_path in sorted(root.glob("**/*.zip")):
            year = year_from_path(zip_path)
            release = zip_path.parent.name
            with ZipFile(zip_path) as archive:
                members = [
                    name
                    for name in archive.namelist()
                    if name.lower().endswith((".xls", ".xlsx"))
                ]
            for member in members:
                evidence_type = _evidence_type(member)
                usable = _is_quality_member(member)
                sheets = _sheet_names(zip_path, member) if usable else [""]
                for sheet_name in sheets:
                    rows.append(
                        {
                            "year": year,
                            "source_family": source_family,
                            "archive_path": str(zip_path),
                            "source_file": zip_path.name,
                            "source_release": release,
                            "member_name": member,
                            "sheet_name": sheet_name,
                            "measure": _measure_from_member(member),
                            "evidence_type": evidence_type,
                            "usable_quality_evidence": usable,
                            "marker": "CV workbook" if evidence_type == "coefficient_of_variation" else "",
                            "note": (
                                "Candidate ASHE quality workbook."
                                if usable
                                else "Workbook checked; no uncertainty or quality marker in member name."
                            ),
                        }
                    )
    if not rows:
        return pd.DataFrame(
            columns=[
                "year",
                "source_family",
                "archive_path",
                "source_file",
                "source_release",
                "member_name",
                "sheet_name",
                "measure",
                "evidence_type",
                "usable_quality_evidence",
                "marker",
                "note",
            ]
        )
    return pd.DataFrame(rows).sort_values(
        ["source_family", "year", "member_name", "sheet_name"]
    ).reset_index(drop=True)


def _as_float(value: object) -> float | None:
    cleaned = clean_numeric_value(value)
    if pd.isna(cleaned):
        return None
    return float(cleaned)


def _quality_status(raw_value: object, cv_percent: float | None) -> str:
    raw = str(raw_value).strip().lower()
    if raw == "x":
        return "unreliable"
    if raw == "..":
        return "disclosive_suppressed"
    if raw == ":":
        return "not_applicable"
    if raw == ".":
        return "unavailable"
    if cv_percent is None:
        return "missing"
    if cv_percent <= 5:
        return "precise"
    if cv_percent <= 10:
        return "reasonably_precise"
    if cv_percent <= 20:
        return "acceptable"
    return "unreliable"


def _parse_description(description: str, source_family: str) -> tuple[str, str] | None:
    text = str(description).strip()
    if text.lower() in {"", "nan"}:
        return None
    if source_family == "ashe_region_age":
        if ", Age " not in text:
            return None
        region, age = text.split(", Age ", 1)
        age_group = normalise_age_label(age)
        if age_group in FOCUS_AGE_GROUPS or age_group == "60+":
            return region.strip(), age_group
        return None
    if not _is_age_description(text):
        return None
    age_group = "All employees" if text == "All employees" else normalise_age_label(text)
    return "United Kingdom", age_group


def _estimate_columns(df: pd.DataFrame, header_row: int, median_idx: int, mean_idx: int) -> dict[str, int]:
    values = [str(value).strip() for value in df.iloc[header_row].tolist()]
    job_idx = values.index("(thousand)") if "(thousand)" in values else max(0, median_idx - 1)
    return {
        "number_of_jobs": job_idx,
        "median": median_idx,
        "mean": mean_idx,
    }


def parse_quality_member(zip_path: str | Path, member_name: str, *, source_family: str) -> pd.DataFrame:
    zip_path = Path(zip_path)
    year = year_from_path(zip_path)
    measure = _measure_from_member(member_name)
    rows: list[dict[str, object]] = []
    excel = _excel_from_zip(zip_path, member_name)
    try:
        for sheet_name in excel.sheet_names:
            if sheet_name.lower().startswith(("cv notes", "notes")):
                continue
            sex, work_status = split_sheet_demographics(sheet_name)
            df = pd.read_excel(excel, sheet_name=sheet_name, header=None)
            try:
                header_row, desc_idx, median_idx, mean_idx = _header_positions(df)
            except ValueError:
                continue
            for _, row in df.iloc[header_row + 1 :].iterrows():
                parsed = _parse_description(str(row.iloc[desc_idx]), source_family)
                if parsed is None:
                    continue
                region, age_group = parsed
                for estimate, value_idx in _estimate_columns(
                    df, header_row, median_idx, mean_idx
                ).items():
                    raw_marker = row.iloc[value_idx]
                    cv_percent = _as_float(raw_marker)
                    quality_status = _quality_status(raw_marker, cv_percent)
                    rows.append(
                        {
                            "year": year,
                            "source_family": source_family,
                            "source_file": zip_path.name,
                            "source_release": zip_path.parent.name,
                            "workbook": member_name,
                            "sheet_name": sheet_name,
                            "measure": measure,
                            "region": region,
                            "age_group": age_group,
                            "sex": sex,
                            "work_status": work_status,
                            "estimate": estimate,
                            "raw_marker": str(raw_marker).strip(),
                            "cv_percent": cv_percent,
                            "quality_status": quality_status,
                            "usable_quality_evidence": cv_percent is not None
                            or quality_status
                            in {
                                "unreliable",
                                "disclosive_suppressed",
                                "not_applicable",
                                "unavailable",
                            },
                            "note": (
                                "Coefficient of variation from ASHE CV workbook; "
                                "not a constructed confidence interval."
                            ),
                        }
                    )
    finally:
        excel.close()
    if not rows:
        return pd.DataFrame(columns=FLAG_COLUMNS)
    return pd.DataFrame(rows)[FLAG_COLUMNS]


def parse_quality_archives(availability: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if availability.empty:
        return pd.DataFrame(columns=FLAG_COLUMNS)
    quality_members = availability[
        availability["usable_quality_evidence"].astype(bool)
        & availability["evidence_type"].eq("coefficient_of_variation")
    ][["archive_path", "member_name", "source_family"]].drop_duplicates()
    for row in quality_members.itertuples(index=False):
        frames.append(
            parse_quality_member(
                row.archive_path,
                row.member_name,
                source_family=row.source_family,
            )
        )
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=FLAG_COLUMNS)
    return pd.concat(frames, ignore_index=True).sort_values(
        ["source_family", "year", "measure", "region", "age_group", "sex", "work_status", "estimate"]
    ).reset_index(drop=True)


def summarise_quality_flags(flags: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "age_group",
        "measure",
        "estimate",
        "latest_year",
        "latest_cv_percent",
        "latest_quality_status",
        "worst_quality_status",
        "years_with_quality_evidence",
        "missing_quality_evidence",
    ]
    if flags.empty:
        return pd.DataFrame(columns=columns)
    focus = flags[
        flags["source_family"].eq("ashe_age")
        & flags["region"].eq("United Kingdom")
        & flags["sex"].eq("All")
        & flags["work_status"].eq("All")
        & flags["age_group"].isin(FOCUS_AGE_GROUPS)
        & flags["estimate"].isin(["median", "mean", "number_of_jobs"])
    ].copy()
    if focus.empty:
        return pd.DataFrame(columns=columns)
    severity = {
        "precise": 0,
        "reasonably_precise": 1,
        "acceptable": 2,
        "unavailable": 3,
        "not_applicable": 3,
        "disclosive_suppressed": 4,
        "unreliable": 5,
        "missing": 6,
    }
    rows: list[dict[str, object]] = []
    for (age_group, measure, estimate), group in focus.groupby(["age_group", "measure", "estimate"]):
        ordered = group.sort_values("year")
        latest = ordered.iloc[-1]
        worst = max(
            ordered["quality_status"].astype(str),
            key=lambda status: severity.get(status, 99),
        )
        rows.append(
            {
                "age_group": age_group,
                "measure": measure,
                "estimate": estimate,
                "latest_year": int(latest["year"]),
                "latest_cv_percent": latest["cv_percent"],
                "latest_quality_status": latest["quality_status"],
                "worst_quality_status": worst,
                "years_with_quality_evidence": int(ordered["year"].nunique()),
                "missing_quality_evidence": False,
            }
        )
    return pd.DataFrame(rows).sort_values(["age_group", "measure", "estimate"]).reset_index(
        drop=True
    )


def _chart_quality(summary: pd.DataFrame, output_root: Path) -> None:
    if summary.empty:
        return
    plot = summary[
        summary["measure"].eq("weekly_gross") & summary["estimate"].eq("median")
    ].copy()
    if plot.empty:
        return
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plot = plot.sort_values("age_group")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(plot["age_group"], plot["latest_cv_percent"], color="#4b6fb4")
    ax.axhline(5, color="#3d7f5b", linewidth=1, linestyle="--")
    ax.axhline(10, color="#c98b2c", linewidth=1, linestyle="--")
    ax.axhline(20, color="#b44b4b", linewidth=1, linestyle="--")
    ax.set_title("ASHE Weekly Earnings CV by Age")
    ax.set_xlabel("ASHE age group")
    ax.set_ylabel("Median weekly earnings CV (%)")
    ax.grid(axis="y", alpha=0.25)
    for idx, row in enumerate(plot.itertuples(index=False)):
        ax.text(
            idx,
            float(row.latest_cv_percent) + 0.15,
            str(row.latest_quality_status).replace("_", " "),
            ha="center",
            va="bottom",
            fontsize=8,
        )
    fig.text(
        0.01,
        0.01,
        "Source: ONS ASHE Table 6 CV workbooks. CVs are source quality measures, not constructed confidence intervals.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    charts = ensure_dir(output_root / "charts")
    fig.savefig(charts / "ashe_real_earnings_with_quality_flags.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_quality_availability_report(
    availability: pd.DataFrame,
    flags: pd.DataFrame,
    summary: pd.DataFrame,
    *,
    output_root: str | Path = OUTPUT_ROOT,
) -> Path:
    evidence = ensure_dir(Path(output_root) / "evidence")
    lines = [
        "# ASHE Uncertainty and Quality Availability",
        "",
        "This audit checks ASHE age and region-by-age downloads for published quality evidence: CV workbooks, confidence interval fields, standard errors, suppression markers, reliability markers, and quality notes.",
        "",
        "It does not fabricate confidence intervals or infer sampling error without a source field.",
        "",
        "## What Was Checked",
        "",
    ]
    if availability.empty:
        lines.append("No ASHE age or region-by-age zip files were found to inspect.")
    else:
        archives = availability[["source_family", "source_file"]].drop_duplicates()
        lines.append(f"- ASHE archives checked: {len(archives)}.")
        lines.append(
            f"- Excel workbooks checked: {availability[['source_file', 'member_name']].drop_duplicates().shape[0]}."
        )
        quality = availability[availability["usable_quality_evidence"].astype(bool)]
        lines.append(f"- Candidate quality workbooks found: {quality['member_name'].nunique()}.")
        for row in archives.sort_values(["source_family", "source_file"]).itertuples(index=False):
            lines.append(f"- {row.source_family}: {row.source_file}")
    lines.extend(["", "## Result", ""])
    if flags.empty:
        lines.append(
            "No usable ASHE uncertainty fields were found. The report records the checked archives and leaves confidence intervals absent rather than inventing them."
        )
    else:
        lines.append(
            f"Usable ASHE CV fields were parsed from {flags['workbook'].nunique()} CV workbooks."
        )
        lines.append(
            "The parsed fields are coefficients of variation for published ASHE estimates. They are quality indicators, not direct confidence intervals created by this project."
        )
        weekly = summary[
            summary["measure"].eq("weekly_gross") & summary["estimate"].eq("median")
        ]
        for row in weekly.sort_values("age_group").itertuples(index=False):
            lines.append(
                f"- {row.age_group}: latest median weekly CV is {float(row.latest_cv_percent):.2f}% "
                f"({str(row.latest_quality_status).replace('_', ' ')})."
            )
    path = evidence / "ashe_quality_availability.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def build_ashe_quality_outputs(
    *,
    age_raw_root: str | Path = AGE_RAW_ROOT,
    region_age_raw_root: str | Path = REGION_AGE_RAW_ROOT,
    processed_root: str | Path = PROCESSED_ROOT,
    output_root: str | Path = OUTPUT_ROOT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    output_root = Path(output_root)
    processed_root = ensure_dir(processed_root)
    tables = ensure_dir(output_root / "tables")
    availability = inspect_ashe_quality_archives(
        age_raw_root=age_raw_root,
        region_age_raw_root=region_age_raw_root,
    )
    flags = parse_quality_archives(availability)
    summary = summarise_quality_flags(flags)
    write_dataframe(flags, processed_root / "ashe_quality_flags.parquet")
    write_dataframe(summary, tables / "ashe_quality_summary.csv")
    uncertainty = summary[
        summary["estimate"].eq("median") & summary["measure"].isin(["weekly_gross", "hourly_gross", "total_paid_hours"])
    ].copy()
    write_dataframe(uncertainty, tables / "ashe_uncertainty_by_age.csv")
    _chart_quality(summary, output_root)
    write_quality_availability_report(availability, flags, summary, output_root=output_root)
    return flags, summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Inspect ASHE quality and uncertainty fields.")
    parser.parse_args(argv)
    _, summary = build_ashe_quality_outputs()
    print(OUTPUT_ROOT / "tables" / "ashe_quality_summary.csv" if not summary.empty else OUTPUT_ROOT / "evidence" / "ashe_quality_availability.md")


if __name__ == "__main__":
    main()
