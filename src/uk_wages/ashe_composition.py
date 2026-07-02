from __future__ import annotations

import argparse
import io
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from .clean_ashe import (
    _header_positions,
    _is_age_description,
    find_weekly_gross_workbook,
    split_sheet_demographics,
    year_from_path,
)
from .utils import clean_numeric_value, ensure_dir, normalise_age_label, project_path, write_dataframe


RAW_ROOT = project_path("data", "raw", "ashe_age")
PROCESSED_ROOT = project_path("data", "processed")
OUTPUT_ROOT = project_path("outputs")
FOCUS_AGE_GROUPS = ["18-21", "22-29", "30-39"]


def _as_float(value: object) -> float | None:
    cleaned = clean_numeric_value(value)
    if pd.isna(cleaned):
        return None
    return float(cleaned)


def _pct_change(base: float | None, latest: float | None) -> float | None:
    if base in {None, 0} or latest is None:
        return None
    return round((float(latest) / float(base) - 1) * 100, 2)


def _extract_job_count_rows(workbook_payload: bytes, *, year: int, source_file: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    excel = pd.ExcelFile(io.BytesIO(workbook_payload))
    try:
        for sheet_name in excel.sheet_names:
            if sheet_name.lower().startswith("notes"):
                continue
            sex, work_status = split_sheet_demographics(sheet_name)
            df = pd.read_excel(excel, sheet_name=sheet_name, header=None)
            try:
                header_row, desc_idx, median_idx, _ = _header_positions(df)
            except ValueError:
                continue
            header_values = [str(value).strip() for value in df.iloc[header_row].tolist()]
            job_idx = (
                header_values.index("(thousand)")
                if "(thousand)" in header_values
                else max(0, median_idx - 1)
            )
            for _, row in df.iloc[header_row + 1 :].iterrows():
                description = str(row.iloc[desc_idx]).strip()
                if not _is_age_description(description):
                    continue
                age_group = (
                    "All employees"
                    if description == "All employees"
                    else normalise_age_label(description)
                )
                if age_group not in FOCUS_AGE_GROUPS:
                    continue
                jobs = _as_float(row.iloc[job_idx])
                if jobs is None:
                    continue
                rows.append(
                    {
                        "year": year,
                        "age_group": age_group,
                        "sex": sex,
                        "work_status": work_status,
                        "employee_jobs_thousand": jobs,
                        "source_file": source_file,
                    }
                )
    finally:
        excel.close()
    return pd.DataFrame(rows)


def extract_job_counts(raw_root: str | Path = RAW_ROOT) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for zip_path in sorted(Path(raw_root).glob("**/*.zip")):
        try:
            workbook = find_weekly_gross_workbook(zip_path)
        except FileNotFoundError:
            continue
        with ZipFile(zip_path) as archive:
            frames.append(
                _extract_job_count_rows(
                    archive.read(workbook),
                    year=year_from_path(zip_path),
                    source_file=zip_path.name,
                )
            )
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(
            columns=[
                "year",
                "age_group",
                "sex",
                "work_status",
                "employee_jobs_thousand",
                "source_file",
            ]
        )
    return pd.concat(frames, ignore_index=True).drop_duplicates(
        ["year", "age_group", "sex", "work_status"]
    )


def build_composition_frame(
    ashe_age: pd.DataFrame,
    *,
    job_counts: pd.DataFrame | None = None,
) -> pd.DataFrame:
    weekly = ashe_age[
        ashe_age["age_group"].isin(FOCUS_AGE_GROUPS)
        & ashe_age["earnings_measure"].eq("median_weekly_gross")
        & (
            (ashe_age["sex"].eq("All") & ashe_age["work_status"].isin(["All", "Full-Time", "Part-Time"]))
            | (ashe_age["sex"].isin(["Male", "Female"]) & ashe_age["work_status"].eq("All"))
        )
    ].copy()
    weekly = weekly.rename(columns={"nominal_earnings": "median_weekly_gross"})
    keep = [
        "year",
        "age_group",
        "sex",
        "work_status",
        "median_weekly_gross",
        "unit",
        "source_file",
        "source_release",
    ]
    weekly = weekly[keep]
    if job_counts is not None and not job_counts.empty:
        weekly = weekly.merge(
            job_counts[["year", "age_group", "sex", "work_status", "employee_jobs_thousand"]],
            on=["year", "age_group", "sex", "work_status"],
            how="left",
        )
    else:
        weekly["employee_jobs_thousand"] = pd.NA
    return weekly.sort_values(["age_group", "year", "sex", "work_status"]).reset_index(drop=True)


def _value_for(
    group: pd.DataFrame,
    *,
    year: int,
    sex: str,
    work_status: str,
    column: str,
) -> float | None:
    match = group[
        group["year"].eq(year) & group["sex"].eq(sex) & group["work_status"].eq(work_status)
    ]
    if match.empty or pd.isna(match.iloc[0][column]):
        return None
    return float(match.iloc[0][column])


def _share(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return round(float(numerator) / float(denominator), 4)


def summarise_composition(
    composition: pd.DataFrame,
    *,
    hours: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for age_group, group in composition.groupby("age_group"):
        years = sorted(group["year"].unique())
        if len(years) < 2:
            continue
        baseline_year = int(years[0])
        latest_year = int(years[-1])
        all_base = _value_for(
            group, year=baseline_year, sex="All", work_status="All", column="median_weekly_gross"
        )
        all_latest = _value_for(
            group, year=latest_year, sex="All", work_status="All", column="median_weekly_gross"
        )
        full_base = _value_for(
            group, year=baseline_year, sex="All", work_status="Full-Time", column="median_weekly_gross"
        )
        full_latest = _value_for(
            group, year=latest_year, sex="All", work_status="Full-Time", column="median_weekly_gross"
        )
        part_base = _value_for(
            group, year=baseline_year, sex="All", work_status="Part-Time", column="median_weekly_gross"
        )
        part_latest = _value_for(
            group, year=latest_year, sex="All", work_status="Part-Time", column="median_weekly_gross"
        )
        male_base = _value_for(
            group, year=baseline_year, sex="Male", work_status="All", column="median_weekly_gross"
        )
        male_latest = _value_for(
            group, year=latest_year, sex="Male", work_status="All", column="median_weekly_gross"
        )
        female_base = _value_for(
            group, year=baseline_year, sex="Female", work_status="All", column="median_weekly_gross"
        )
        female_latest = _value_for(
            group, year=latest_year, sex="Female", work_status="All", column="median_weekly_gross"
        )
        all_jobs_base = _value_for(
            group, year=baseline_year, sex="All", work_status="All", column="employee_jobs_thousand"
        )
        all_jobs_latest = _value_for(
            group, year=latest_year, sex="All", work_status="All", column="employee_jobs_thousand"
        )
        full_jobs_base = _value_for(
            group,
            year=baseline_year,
            sex="All",
            work_status="Full-Time",
            column="employee_jobs_thousand",
        )
        full_jobs_latest = _value_for(
            group,
            year=latest_year,
            sex="All",
            work_status="Full-Time",
            column="employee_jobs_thousand",
        )
        female_jobs_base = _value_for(
            group,
            year=baseline_year,
            sex="Female",
            work_status="All",
            column="employee_jobs_thousand",
        )
        female_jobs_latest = _value_for(
            group,
            year=latest_year,
            sex="Female",
            work_status="All",
            column="employee_jobs_thousand",
        )
        hours_pct_change = None
        if hours is not None and not hours.empty:
            hour_row = hours[hours["age_group"].eq(age_group)].sort_values("year")
            if not hour_row.empty:
                latest_hours = hour_row.iloc[-1]
                if "hours_index_2019_100" in latest_hours:
                    hours_pct_change = round(float(latest_hours["hours_index_2019_100"]) - 100, 2)
                elif "total_paid_hours" in latest_hours:
                    base_hours = hour_row.iloc[0]["total_paid_hours"]
                    hours_pct_change = _pct_change(float(base_hours), float(latest_hours["total_paid_hours"]))
        full_time_share_base = _share(full_jobs_base, all_jobs_base)
        full_time_share_latest = _share(full_jobs_latest, all_jobs_latest)
        female_share_base = _share(female_jobs_base, all_jobs_base)
        female_share_latest = _share(female_jobs_latest, all_jobs_latest)
        job_count_available = all_jobs_base is not None and all_jobs_latest is not None
        rows.append(
            {
                "age_group": age_group,
                "baseline_year": baseline_year,
                "latest_year": latest_year,
                "all_employee_weekly_pct_change": _pct_change(all_base, all_latest),
                "full_time_weekly_pct_change": _pct_change(full_base, full_latest),
                "part_time_weekly_pct_change": _pct_change(part_base, part_latest),
                "male_weekly_pct_change": _pct_change(male_base, male_latest),
                "female_weekly_pct_change": _pct_change(female_base, female_latest),
                "hours_pct_change": hours_pct_change,
                "job_count_proxy_available": job_count_available,
                "full_time_job_share_baseline": full_time_share_base,
                "full_time_job_share_latest": full_time_share_latest,
                "full_time_job_share_change": (
                    round(full_time_share_latest - full_time_share_base, 4)
                    if full_time_share_base is not None and full_time_share_latest is not None
                    else None
                ),
                "female_job_share_baseline": female_share_base,
                "female_job_share_latest": female_share_latest,
                "female_job_share_change": (
                    round(female_share_latest - female_share_base, 4)
                    if female_share_base is not None and female_share_latest is not None
                    else None
                ),
                "composition_note": (
                    "Published ASHE number-of-jobs column parsed as a composition proxy."
                    if job_count_available
                    else "ASHE employee job counts or sample-size proxies were not available in the parsed composition inputs."
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("age_group").reset_index(drop=True)


def _chart_composition(summary: pd.DataFrame, output_root: Path) -> None:
    if summary.empty:
        return
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.5))
    if summary["full_time_job_share_latest"].notna().any():
        plot = summary.set_index("age_group")[
            ["full_time_job_share_baseline", "full_time_job_share_latest"]
        ]
        plot.plot(kind="bar", ax=ax, color=["#777777", "#4b6fb4"])
        ax.set_ylabel("Full-time share of ASHE jobs")
        ax.legend(["Baseline", "Latest"], fontsize=8)
    else:
        plot = summary.set_index("age_group")[
            ["full_time_weekly_pct_change", "part_time_weekly_pct_change"]
        ]
        plot.plot(kind="bar", ax=ax, color=["#4b6fb4", "#c98b2c"])
        ax.set_ylabel("Median weekly pay change (%)")
        ax.legend(["Full-time", "Part-time"], fontsize=8)
    ax.set_title("ASHE Full-Time and Part-Time Composition by Age")
    ax.set_xlabel("Age group")
    ax.grid(axis="y", alpha=0.25)
    fig.text(
        0.01,
        0.01,
        "Source: ONS ASHE Table 6. Composition evidence is descriptive and not causal.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    charts = ensure_dir(output_root / "charts")
    fig.savefig(charts / "ashe_full_time_part_time_mix_by_age.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_composition_report(
    summary: pd.DataFrame,
    *,
    output_root: str | Path = OUTPUT_ROOT,
) -> Path:
    evidence = ensure_dir(Path(output_root) / "evidence")
    lines = [
        "# ASHE Composition Audit",
        "",
        "This audit checks whether the 18-21 weekly-earnings result may be affected by worker or job composition. It compares all employees, full-time, part-time, male, female, and paid-hours rows where ASHE publishes them.",
        "",
        "This is descriptive composition evidence, not causal evidence.",
        "",
        "## Fields Checked",
        "",
        "- Full-time and part-time median weekly rows by age group.",
        "- Male and female median weekly rows by age group.",
        "- Paid-hours movement from the ASHE hourly-pay and hours decomposition.",
        "- Published ASHE number-of-jobs columns where raw Table 6 workbooks were available.",
        "",
        "## Result",
        "",
    ]
    if summary.empty:
        lines.append("No ASHE composition rows were available to summarise.")
    else:
        if not summary["job_count_proxy_available"].astype(bool).any():
            lines.append(
                "ASHE employee job counts or sample-size proxies were not available in the parsed composition inputs, so mix shares are not fabricated."
            )
            lines.append("")
        for row in summary.itertuples(index=False):
            lines.append(
                f"- {row.age_group}: all-employee weekly pay changed by {row.all_employee_weekly_pct_change}%; "
                f"full-time {row.full_time_weekly_pct_change}%; part-time {row.part_time_weekly_pct_change}%; "
                f"paid hours {row.hours_pct_change if pd.notna(row.hours_pct_change) else 'unavailable'}%."
            )
            if row.job_count_proxy_available:
                lines.append(
                    f"  Full-time job share moved from {row.full_time_job_share_baseline:.3f} "
                    f"to {row.full_time_job_share_latest:.3f}; female job share moved from "
                    f"{row.female_job_share_baseline:.3f} to {row.female_job_share_latest:.3f}."
                )
            else:
                lines.append("  Employee job-count mix was unavailable for this row.")
    path = evidence / "ashe_composition_audit.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def build_ashe_composition_outputs(
    *,
    processed_root: str | Path = PROCESSED_ROOT,
    output_root: str | Path = OUTPUT_ROOT,
    raw_root: str | Path | None = RAW_ROOT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    processed_root = Path(processed_root)
    output_root = Path(output_root)
    ashe = pd.read_parquet(processed_root / "ashe_age_annual.parquet")
    job_counts = extract_job_counts(raw_root) if raw_root is not None else pd.DataFrame()
    composition = build_composition_frame(ashe, job_counts=job_counts)
    hours_path = processed_root / "ashe_age_hours_decomposition.parquet"
    hours = pd.read_parquet(hours_path) if hours_path.exists() else pd.DataFrame()
    summary = summarise_composition(composition, hours=hours)
    write_dataframe(composition, processed_root / "ashe_age_composition.parquet")
    write_dataframe(summary, ensure_dir(output_root / "tables") / "ashe_composition_change_by_age.csv")
    _chart_composition(summary, output_root)
    write_composition_report(summary, output_root=output_root)
    return composition, summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build ASHE age composition audit outputs.")
    parser.parse_args(argv)
    _, summary = build_ashe_composition_outputs()
    print(OUTPUT_ROOT / "tables" / "ashe_composition_change_by_age.csv" if not summary.empty else OUTPUT_ROOT / "evidence" / "ashe_composition_audit.md")


if __name__ == "__main__":
    main()
