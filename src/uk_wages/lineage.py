from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import ensure_dir, project_path


OUTPUT_ROOT = project_path("outputs")


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _row(df: pd.DataFrame, column: str, value: object) -> pd.Series | None:
    if df.empty or column not in df.columns:
        return None
    match = df[df[column].astype(str).eq(str(value))]
    return None if match.empty else match.iloc[0]


def _latest(df: pd.DataFrame, sort_column: str) -> pd.Series | None:
    if df.empty or sort_column not in df.columns:
        return None
    return df.sort_values(sort_column).iloc[-1]


def _value(value: object, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "unavailable"
    if isinstance(value, str):
        return value
    return f"{float(value):.{digits}f}"


def build_headline_number_lineage(*, output_root: str | Path = OUTPUT_ROOT) -> tuple[Path, Path]:
    output_root = Path(output_root)
    tables = output_root / "tables"
    evidence = ensure_dir(output_root / "evidence")
    ashe = _read_csv(tables / "age_group_real_earnings_change.csv")
    rti = _read_csv(tables / "rti_age_real_pay_change.csv")
    decomp = _read_csv(tables / "ashe_hours_decomposition.csv")
    wages = _read_csv(tables / "minimum_wage_real_rates.csv")
    gaps = _read_csv(tables / "youth_labour_market_gaps.csv")
    checks = _read_csv(evidence / "source_value_checks.csv")

    rows: list[dict[str, object]] = []

    def add(
        *,
        headline_number: str,
        value: object,
        unit: str,
        source_dataset: str,
        raw_file: str,
        processed_file: str,
        analysis_module: str,
        chart_or_report: str,
        validation_check: str,
        caveat: str,
    ) -> None:
        rows.append(
            {
                "headline_number": headline_number,
                "value": _value(value),
                "unit": unit,
                "source_dataset": source_dataset,
                "raw_file": raw_file,
                "processed_file": processed_file,
                "analysis_module": analysis_module,
                "chart_or_report": chart_or_report,
                "validation_check": validation_check,
                "caveat": caveat,
            }
        )

    ashe_18 = _row(ashe, "age_group", "18-21")
    ashe_22 = _row(ashe, "age_group", "22-29")
    add(
        headline_number="18-21 ASHE real weekly earnings change",
        value=None if ashe_18 is None else ashe_18.get("real_pct_change"),
        unit="percent change since 2019",
        source_dataset="ASHE Table 6 + MM23 CPIH",
        raw_file="data/raw/ashe_age/**/ashetable6*.zip; data/raw/inflation/*",
        processed_file="data/processed/ashe_age_annual.parquet; data/processed/inflation_annual.parquet",
        analysis_module="uk_wages.analysis",
        chart_or_report="reports/research_note.md; outputs/charts/real_earnings_change_by_age.png",
        validation_check="ashe_18_21_nominal_2019; ashe_18_21_nominal_latest_ashe_year",
        caveat="not robust under the configured core checks and source-dependent.",
    )
    add(
        headline_number="22-29 ASHE real weekly earnings change",
        value=None if ashe_22 is None else ashe_22.get("real_pct_change"),
        unit="percent change since 2019",
        source_dataset="ASHE Table 6 + MM23 CPIH",
        raw_file="data/raw/ashe_age/**/ashetable6*.zip; data/raw/inflation/*",
        processed_file="data/processed/ashe_age_annual.parquet; data/processed/inflation_annual.parquet",
        analysis_module="uk_wages.analysis",
        chart_or_report="reports/research_note.md; outputs/charts/real_earnings_change_by_age.png",
        validation_check="ashe_22_29_nominal_2019; ashe_22_29_nominal_latest_ashe_year",
        caveat="More stable than 18-21, but still annual ASHE evidence.",
    )

    rti_18 = _row(rti, "age_group", "18-24")
    add(
        headline_number="RTI 18-24 real monthly PAYE pay change",
        value=None if rti_18 is None else rti_18.get("real_pay_pct_change_since_jan2019"),
        unit="percent change since January 2019",
        source_dataset="ONS/HMRC PAYE RTI + MM23 CPIH",
        raw_file="data/raw/rti/*; data/raw/inflation/*",
        processed_file="data/processed/rti_age_monthly.parquet",
        analysis_module="uk_wages.rti_analysis",
        chart_or_report="outputs/evidence/rti_ashe_triangulation.md",
        validation_check="rti_18_24_median_pay_jan2019; rti_18_24_median_pay_latest",
        caveat="Monthly PAYE source for 18-24, not a replacement for ASHE 18-21 or 22-29.",
    )

    decomp_18 = _row(decomp, "age_group", "18-21")
    add(
        headline_number="18-21 real hourly pay change",
        value=None if decomp_18 is None else decomp_18.get("hourly_pct_change"),
        unit="percent change since 2019",
        source_dataset="ASHE Table 6 hourly gross pay + MM23 CPIH",
        raw_file="data/raw/ashe_age/**/ashetable6*.zip; data/raw/inflation/*",
        processed_file="data/processed/ashe_age_hours_decomposition.parquet",
        analysis_module="uk_wages.ashe_decomposition",
        chart_or_report="outputs/evidence/ashe_decomposition_report.md",
        validation_check="ASHE weekly/hourly workbooks availability check",
        caveat="Descriptive decomposition of medians, not causal.",
    )
    add(
        headline_number="18-21 paid hours change",
        value=None if decomp_18 is None else decomp_18.get("hours_pct_change"),
        unit="percent change since 2019",
        source_dataset="ASHE Table 6 paid-hours workbooks",
        raw_file="data/raw/ashe_age/**/ashetable6*.zip",
        processed_file="data/processed/ashe_age_hours_decomposition.parquet",
        analysis_module="uk_wages.ashe_decomposition",
        chart_or_report="outputs/evidence/ashe_decomposition_report.md",
        validation_check="ASHE paid-hours workbook availability check",
        caveat="Hours are part of the weekly-pay arithmetic, not a causal mechanism by themselves.",
    )

    wage_18_20 = wages[
        wages.get("policy_series", pd.Series(dtype=str)).astype(str).eq("18 to 20")
    ] if not wages.empty else pd.DataFrame()
    wage_latest = _latest(wage_18_20, "effective_year")
    add(
        headline_number="18-20 real minimum wage index",
        value=None if wage_latest is None else wage_latest.get("real_statutory_wage_index_2019_100"),
        unit="index, 2019 = 100",
        source_dataset="GOV.UK minimum wage rates + MM23 CPIH",
        raw_file="data/raw/minimum_wage/*; data/raw/inflation/*",
        processed_file="data/processed/minimum_wage_rates.parquet",
        analysis_module="uk_wages.minimum_wage",
        chart_or_report="outputs/evidence/minimum_wage_context.md",
        validation_check="minimum_wage_18_20_2026_rate",
        caveat="Policy context only; ASHE 18-21 includes 21-year-olds.",
    )

    gap_latest = _latest(gaps, "date")
    add(
        headline_number="A05 youth unemployment gap change",
        value=None if gap_latest is None else gap_latest.get("youth_unemployment_gap_change_since_2019"),
        unit="percentage points since 2019",
        source_dataset="ONS A05 SA",
        raw_file="data/raw/a05/*",
        processed_file="data/processed/a05_age_labour_market.parquet",
        analysis_module="uk_wages.analysis",
        chart_or_report="outputs/charts/youth_labour_market_stress.png",
        validation_check="a05_16_24_unemployment_latest",
        caveat="Labour-market status context, not earnings evidence.",
    )

    pass_count = (
        int(checks["status"].astype(str).str.lower().eq("pass").sum())
        if not checks.empty and "status" in checks.columns
        else None
    )
    total_count = len(checks) if not checks.empty else None
    add(
        headline_number="source audit pass count",
        value=f"{pass_count}/{total_count}" if pass_count is not None else None,
        unit="checks passed",
        source_dataset="Manual source-value audit",
        raw_file="official source files listed in outputs/evidence/source_value_checks.csv",
        processed_file="outputs/evidence/source_value_checks.csv",
        analysis_module="uk_wages.source_validation",
        chart_or_report="outputs/evidence/manual_validation_audit.md",
        validation_check="all source-value checks",
        caveat="Audit checks selected headline source cells, not every cell in every workbook.",
    )

    lineage = pd.DataFrame(rows)
    csv_path = evidence / "headline_number_lineage.csv"
    lineage.to_csv(csv_path, index=False)
    md_lines = [
        "# Headline Number Lineage",
        "",
        "This file maps each headline number back to source datasets, raw files, processed files, analysis modules, validation checks, and caveats.",
        "",
    ]
    for row in lineage.itertuples(index=False):
        md_lines.extend(
            [
                f"## {row.headline_number}",
                "",
                f"- Value: {row.value} {row.unit}",
                f"- Source dataset: {row.source_dataset}",
                f"- Raw file: {row.raw_file}",
                f"- Processed file: {row.processed_file}",
                f"- Analysis module: {row.analysis_module}",
                f"- Chart or report: {row.chart_or_report}",
                f"- Validation check: {row.validation_check}",
                f"- Caveat: {row.caveat}",
                "",
            ]
        )
    md_path = evidence / "headline_number_lineage.md"
    md_path.write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")
    return csv_path, md_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build headline number lineage outputs.")
    parser.parse_args(argv)
    csv_path, _ = build_headline_number_lineage()
    print(csv_path)


if __name__ == "__main__":
    main()
