from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import ensure_dir, project_path


OUTPUT_ROOT = project_path("outputs")
PROCESSED_ROOT = project_path("data", "processed")


def _require_csv(path: Path, description: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required {description}: {path}")
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError(f"Required {description} is empty: {path}")
    return frame


def _require_text(path: Path, description: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required {description}: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Required {description} is empty: {path}")
    return text


def _require_text_contains(path: Path, description: str, required_text: list[str]) -> str:
    text = _require_text(path, description)
    missing = [value for value in required_text if value not in text]
    if missing:
        raise ValueError(f"Required {description} is missing expected evidence text: {missing}")
    return text


def _claim_verdict(claims: pd.DataFrame, claim_id: str, default: str = "inconclusive") -> str:
    if claims.empty or "claim_id" not in claims.columns:
        return default
    match = claims[claims["claim_id"].eq(claim_id)]
    if match.empty:
        return default
    return str(match.iloc[0].get("verdict", default))


def _summary_value(summary: pd.DataFrame, age_group: str, column: str) -> str:
    if summary.empty or column not in summary.columns:
        raise ValueError(f"Missing summary column {column!r} for {age_group}.")
    row = summary[summary["age_group"].eq(age_group)]
    if row.empty:
        raise ValueError(f"Missing summary row for {age_group}.")
    value = row.iloc[0][column]
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _fragility_line(scores: pd.DataFrame, age_group: str) -> str:
    if scores.empty:
        raise ValueError("Fragility scores were not available.")
    rows = scores[scores["age_group"].eq(age_group)]
    if rows.empty:
        raise ValueError(f"No fragility row was available for {age_group}.")
    core = rows[rows["spec_tier"].eq("core")] if "spec_tier" in rows.columns else pd.DataFrame()
    selected = core.iloc[0] if not core.empty else rows.iloc[0]
    return (
        f"Core specs: {int(selected['material_disagreements'])}/"
        f"{int(selected['specifications_tested'])} material disagreements; "
        f"directional fragility {float(selected['fragility_score']):.1%}."
    )


def _latest_youth_gap_line(output_root: Path) -> str:
    gaps = _require_csv(
        output_root / "tables" / "youth_labour_market_gaps.csv",
        "youth labour-market stress table",
    )
    latest = gaps.sort_values("date").iloc[-1]
    return (
        f"Latest A05 16-24 vs 25-34 gap changes since 2019: unemployment "
        f"{float(latest['youth_unemployment_gap_change_since_2019']):.2f}pp; "
        f"inactivity {float(latest['youth_inactivity_gap_change_since_2019']):.2f}pp."
    )


def _latest_earn01_line(processed_root: Path) -> str:
    path = processed_root / "awe_real_monthly.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing required EARN01 monthly processed table: {path}")
    awe = pd.read_parquet(path)
    focus = awe[awe["sector"].eq("Whole Economy")].sort_values("date")
    if focus.empty:
        raise ValueError("EARN01 whole-economy monthly row was not available.")
    latest = focus.iloc[-1]
    return (
        f"Latest whole-economy EARN01 month: {pd.Timestamp(latest['date']):%Y-%m}; "
        f"real regular pay index {float(latest['real_regular_pay_index_jan2019_100']):.2f}; "
        f"real total pay index {float(latest['real_total_pay_index_jan2019_100']):.2f}."
    )


def _earn01_triangulation_line(output_root: Path, age_group: str = "18-21") -> str:
    path = output_root / "evidence" / "triangulation_summary.csv"
    if not path.exists():
        return "ASHE-EARN01 directional concordance metrics have not been generated."
    summary = pd.read_csv(path)
    focus = summary[summary["age_group"].astype(str).eq(age_group)]
    if focus.empty:
        return f"ASHE-EARN01 directional concordance metrics are missing for {age_group}."
    row = focus.iloc[0]
    return (
        f"Directional concordance with EARN01 regular pay for ASHE {age_group}: "
        f"{float(row['regular_direction_concordance']):.0%} across "
        f"{int(row['yoy_comparison_years'])} adjacent year-over-year comparisons; "
        "latest cross-source index difference "
        f"{float(row['latest_regular_cross_source_index_difference']):.2f} index points."
    )


def _latest_rti_line(output_root: Path) -> str:
    rti = _require_csv(
        output_root / "tables" / "rti_age_real_pay_change.csv",
        "RTI age real-pay summary",
    )
    focus = rti[rti["age_group"].eq("18-24")]
    if focus.empty:
        raise ValueError("RTI 18-24 summary row was not available.")
    row = focus.iloc[0]
    return (
        f"RTI 18-24 real median monthly PAYE pay changed "
        f"{float(row['real_pay_pct_change_since_jan2019']):.2f}% from January 2019 "
        f"to {row['latest_available_month']}; latest-month flash/provisional flag: "
        f"{bool(row['latest_available_is_flash_or_provisional'])}."
    )


def _rti_concordance_line(output_root: Path, ashe_age_group: str = "18-21") -> str:
    path = output_root / "evidence" / "rti_ashe_annual_summary.csv"
    if not path.exists():
        return "April-to-April RTI-ASHE concordance metrics have not been generated."
    summary = pd.read_csv(path)
    focus = summary[summary["ashe_age_group"].astype(str).eq(ashe_age_group)]
    if focus.empty:
        return f"April-to-April RTI-ASHE concordance metrics are missing for ASHE {ashe_age_group}."
    row = focus.iloc[0]
    return (
        f"April-to-April RTI-ASHE concordance for RTI {row['rti_age_group']} versus "
        f"ASHE {ashe_age_group}: {float(row['directional_concordance']):.0%} across "
        f"{int(row['comparison_years'])} adjacent year-over-year comparisons; "
        "latest cross-source index difference "
        f"{float(row['latest_cross_source_index_difference']):.2f} index points."
    )


def _decomposition_line(output_root: Path) -> str:
    table = _require_csv(
        output_root / "tables" / "ashe_hours_decomposition.csv",
        "ASHE hourly-pay and hours decomposition",
    )
    focus = table[table["age_group"].eq("18-21")]
    if focus.empty:
        raise ValueError("ASHE decomposition 18-21 row was not available.")
    row = focus.iloc[0]
    return (
        f"For 18-21, real weekly earnings changed {float(row['weekly_pct_change']):.2f}% "
        f"from {int(row['baseline_year'])} to {int(row['latest_year'])}; hourly pay contributed "
        f"{float(row['hourly_log_contribution']):.3f} log points, hours contributed "
        f"{float(row['hours_log_contribution']):.3f}, and the residual was "
        f"{float(row['residual_log_contribution']):.3f}."
    )


def _ashe_cv_band_line(output_root: Path, age_group: str = "18-21") -> str:
    path = output_root / "evidence" / "ashe_uncertainty_bands.md"
    if not path.exists():
        return "ASHE approximate two-CV bands have not been generated."
    for line in path.read_text(encoding="utf-8").splitlines():
        if age_group in line and "approximate two-CV" in line:
            return line.lstrip("- ")
    return f"ASHE approximate two-CV band text is missing for {age_group}."


def _minimum_wage_line(output_root: Path) -> str:
    rates = _require_csv(
        output_root / "tables" / "minimum_wage_real_rates.csv",
        "minimum wage real-rate table",
    )
    focus = rates[rates["policy_series"].eq("18 to 20")].sort_values("effective_year")
    if focus.empty:
        raise ValueError("Minimum wage 18 to 20 rows were not available.")
    latest = focus.iloc[-1]
    return (
        f"The 18 to 20 statutory hourly rate is {float(latest['nominal_hourly_rate']):.2f} "
        f"in April {int(latest['effective_year'])}; its real statutory wage index is "
        f"{float(latest['real_statutory_wage_index_2019_100']):.2f} with April 2019 = 100."
    )


def _option_b_lines(output_root: Path) -> list[str]:
    path = output_root / "evidence" / "option_b_ds_report.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    evidence_lines = [
        "Option B adds structural break, event framing, and forecast baseline diagnostics."
    ]
    structural_path = output_root / "tables" / "structural_break_weights.csv"
    event_path = output_root / "tables" / "minimum_wage_event_study.csv"
    forecast_path = output_root / "tables" / "ashe_forecast_baseline.csv"
    if structural_path.exists():
        structural = pd.read_csv(structural_path)
        required = {"age_group", "break_year", "relative_weight", "level_shift_index_points"}
        if not structural.empty and required.issubset(structural.columns):
            top = structural.sort_values("relative_weight", ascending=False).iloc[0]
            evidence_lines.append(
                f"Highest relative break-year weight: {top['age_group']} in "
                f"{int(top['break_year'])} ({float(top['relative_weight']):.1%}); "
                f"level shift {float(top['level_shift_index_points']):.2f} index points."
            )
    if event_path.exists():
        event = pd.read_csv(event_path)
        if not event.empty and "descriptive_did_index_points" in event.columns:
            row = event.iloc[0]
            evidence_lines.append(
                f"Minimum-wage event framing: {row['treated_age_group']} versus "
                f"{row['comparison_age_group']} descriptive DID "
                f"{float(row['descriptive_did_index_points']):.2f} index points "
                f"({float(row['descriptive_did_percent_points']):.2f} percentage points "
                "on percent-change scale); threshold context is mixed."
            )
    if forecast_path.exists():
        forecast = pd.read_csv(forecast_path)
        required = {"age_group", "forecast_year", "forecast_index", "interval_note"}
        focus = forecast[forecast["age_group"].eq("18-21")] if "age_group" in forecast.columns else pd.DataFrame()
        if not focus.empty and required.issubset(forecast.columns):
            row = focus.sort_values("forecast_year").iloc[0]
            evidence_lines.append(
                f"Forecast baseline: {row['age_group']} {int(row['forecast_year'])} "
                f"index {float(row['forecast_index']):.2f}; band type is {row['interval_note']}."
            )
    return evidence_lines


def _ashe_quality_line(output_root: Path, age_group: str) -> str:
    path = output_root / "tables" / "ashe_quality_summary.csv"
    if not path.exists():
        return (
            f"ASHE uncertainty and quality evidence for {age_group} has not been run; "
            "do not infer confidence intervals."
        )
    quality = pd.read_csv(path)
    focus = quality[
        quality["age_group"].astype(str).eq(age_group)
        & quality["measure"].astype(str).eq("weekly_gross")
        & quality["estimate"].astype(str).eq("median")
    ]
    if focus.empty:
        return (
            f"ASHE uncertainty and quality evidence for {age_group} is missing from the parsed CV summary; "
            "do not infer confidence intervals."
        )
    row = focus.iloc[0]
    if bool(row.get("missing_quality_evidence", False)):
        return (
            f"ASHE uncertainty and quality evidence for {age_group} is recorded as missing; "
            "do not infer confidence intervals."
        )
    return (
        f"ASHE uncertainty and quality evidence: {age_group} median weekly CV is "
        f"{float(row['latest_cv_percent']):.2f}% "
        f"({str(row['latest_quality_status']).replace('_', ' ')}), from the ASHE CV workbook. "
        "This is a source quality marker, not a constructed confidence interval."
    )


def _what_would_change_lines() -> list[str]:
    return [
        "## Further questions",
        "",
        "- Would the 18-21 result strengthen if the next ASHE release keeps the negative weekly-earnings signal under the core specifications?",
        "- Does the 18-24 RTI PAYE series keep pointing differently once flash months are revised and more non-flash months are available?",
        "- Are the 18-21 movements mostly a paid-hours story, a worker-composition story, or both?",
        "- Do source quality, work-status splits, or source-triangulation checks move away from the baseline ASHE result for 22-29?",
        "",
    ]


def build_final_claims(
    *,
    output_root: str | Path = OUTPUT_ROOT,
    processed_root: str | Path = PROCESSED_ROOT,
) -> Path:
    output_root = Path(output_root)
    processed_root = Path(processed_root)
    evidence_root = ensure_dir(output_root / "evidence")
    claims = _require_csv(evidence_root / "claim_assessment.csv", "claim assessment")
    scores = _require_csv(evidence_root / "fragility_scores.csv", "fragility scores")
    summary = _require_csv(
        output_root / "tables" / "age_group_real_earnings_change.csv",
        "age-group summary",
    )
    diagnostics = _require_text(evidence_root / "fragility_diagnostics.md", "fragility diagnostics")
    _require_text_contains(
        evidence_root / "triangulation_report.md",
        "triangulation report",
        ["EARN01", "not age-specific"],
    )
    _require_text_contains(
        evidence_root / "rti_ashe_triangulation.md",
        "RTI-ASHE triangulation report",
        ["RTI is a monthly PAYE check", "does not replace ASHE"],
    )
    _require_text_contains(
        evidence_root / "ashe_decomposition_report.md",
        "ASHE decomposition report",
        ["hourly pay", "hours", "residual"],
    )
    _require_text_contains(
        evidence_root / "minimum_wage_context.md",
        "minimum wage context report",
        ["context", "do not prove"],
    )

    latest_year = _summary_value(summary, "18-21", "latest_year")
    result_18 = _summary_value(summary, "18-21", "real_pct_change")
    result_22 = _summary_value(summary, "22-29", "real_pct_change")
    latest_22 = _summary_value(summary, "22-29", "latest_year")
    verdict_18 = _claim_verdict(claims, "c1_youngest_real_wages")
    verdict_22 = _claim_verdict(claims, "c2_22_29_real_wages")
    fragile_18 = verdict_18 in {"fragile", "not robust"}
    label_18 = f"{verdict_18} / ambiguous" if fragile_18 else verdict_18
    wording_18 = (
        "The 18-21 real-earnings result is ambiguous and specification-dependent; state the baseline, deflator, worker definition, and earnings measure when discussing it."
        if fragile_18 else
        f"The baseline 18-21 result is {verdict_18} across the tested specifications; state its signed change, baseline, deflator, worker definition, and earnings measure."
    )
    headline_18 = (
        "The evidence does not support a simple claim that 18-21 workers clearly became better or worse off in real earnings terms after 2019."
        if fragile_18 else f"The baseline 18-21 ASHE result is assessed as {verdict_18} across the tested specifications."
    )
    diagnostics_summary = (
        diagnostics.split("## Fragility diagnostics for 18-21", 1)[-1].strip().split("\n\n", 1)[0]
        if "## Fragility diagnostics for 18-21" in diagnostics
        else diagnostics.strip().split("\n\n", 1)[0]
    )
    option_b = _option_b_lines(output_root)
    option_b_primary = option_b[0] if option_b else "Option B modelling diagnostics have not been generated."
    option_b_detail = option_b[1:] if len(option_b) > 1 else []

    lines = [
        "# UK Youth Real-Wage Claims Report",
        "",
        "## Executive Summary",
        "",
        (
            f"- **Bottom line.** {headline_18} "
            f"The baseline ASHE CPIH comparison shows 18-21 real earnings change of {result_18}% from 2019 to {latest_year}. {wording_18}"
        ),
        (
            f"- **ASHE 22-29.** Baseline ASHE shows 22-29 real earnings change of {result_22}% from 2019 to {latest_22}; "
            f"its assessment is {verdict_22}. This remains an annual ASHE age-group finding."
        ),
        "- **Current and contextual sources should stay in their lanes.** EARN01 is a whole-economy wage trend, RTI is monthly PAYE age-pay triangulation, A05 is labour-market stress context, and minimum-wage rates are wage-floor context rather than causal proof.",
        "- **The practical reporting line is qualified.** Use ASHE as the anchor, use RTI and EARN01 as triangulation, keep hours visible, and avoid turning descriptive diagnostics into causal claims.",
        "",
        "## What the evidence supports",
        "",
        f"- **18-21 ASHE real earnings:** Verdict: {label_18}. Baseline real earnings changed {result_18}% from 2019 to {latest_year}; {_fragility_line(scores, '18-21')}",
        f"- **22-29 ASHE real earnings:** Verdict: {verdict_22}. Baseline real earnings changed {result_22}% from 2019 to {latest_22}; {_fragility_line(scores, '22-29')}",
        f"- **Youth labour-market stress:** Verdict: descriptive / corroborating stress signal. {_latest_youth_gap_line(output_root)}",
        f"- **Hourly pay versus hours:** Verdict: descriptive decomposition. {_decomposition_line(output_root)}",
        f"- **Minimum wage context:** Verdict: policy context only. {_minimum_wage_line(output_root)}",
        f"- **Option B modelling diagnostics:** Verdict: modelling diagnostics / not causal. {option_b_primary}",
        "",
        "## Evidence by source",
        "",
        "### ASHE 18-21 and robustness",
        "",
        (
            "The 18-21 result is the main point that needs careful wording. Claim assessment verdict: "
            f"{_claim_verdict(claims, 'c1_youngest_real_wages', 'fragile')}. "
            f"{diagnostics_summary} {_ashe_quality_line(output_root, '18-21')} {_ashe_cv_band_line(output_root, '18-21')}"
        ),
        "",
        f"**Interpretation:** {wording_18}",
        "",
        "### ASHE 22-29",
        "",
        f"The 22-29 ASHE assessment is {verdict_22}: {_ashe_quality_line(output_root, '22-29')} This is still annual ASHE evidence, not a monthly wage signal.",
        "",
        "### Current monthly wage trend (EARN01)",
        "",
        _latest_earn01_line(processed_root),
        "The triangulation report compares ASHE with EARN01 and records that EARN01 is not age-specific.",
        _earn01_triangulation_line(output_root, "18-21"),
        "**Interpretation:** EARN01 provides a current whole-economy wage trend and should not be interpreted as age-specific evidence for 18-21 or 22-29 workers.",
        "",
        "### RTI monthly age-pay triangulation",
        "",
        _latest_rti_line(output_root),
        "The RTI triangulation report compares RTI 18-24 with ASHE 18-21 and 22-29, and records the age-band mismatch.",
        _rti_concordance_line(output_root, "18-21"),
        "**Interpretation:** RTI provides monthly PAYE age-pay triangulation, not a replacement for ASHE.",
        "",
        "### Wage-floor, hours, and modelling context",
        "",
        "Hourly pay versus hours remains a descriptive accounting split, not a causal explanation. The minimum wage context report uses GOV.UK rates from April 2019 onward and flags the statutory age-threshold mismatch. Minimum wage changes provide context, not causal proof of ASHE changes.",
        *[f"- {line}" for line in option_b_detail],
        "",
        "## Recommended wording",
        "",
        f"- **18-21:** {wording_18}",
        f"- **22-29:** The 22-29 baseline result is assessed as {verdict_22}; report the signed change with the tested assumptions.",
        "- **EARN01:** EARN01 provides a current whole-economy wage trend, not age-specific evidence for 18-21 or 22-29 workers.",
        "- **RTI:** RTI provides monthly PAYE age-pay triangulation, not a replacement for ASHE.",
        "- **Hours and wage floors:** Weekly earnings changes can be decomposed into hourly pay, hours, and residual movement; use minimum wage rates as wage-floor context for young workers, not as a causal claim.",
        "- **Option B:** Use Option B outputs as relative structural-break weights, mixed-threshold event framing, and rough forecast-baseline diagnostics rather than as official forecasts or causal estimates.",
        "",
    ]
    lines.extend(_what_would_change_lines())
    lines.extend(
        [
            "## Caveats and assumptions",
            "",
            "ASHE, RTI, A05, EARN01, and minimum-wage data measure different populations, frequencies, and concepts. This is the source limitation that prevents stronger wording.",
            "",
            "RTI is PAYE administrative data. It covers payrolled employees, not self-employment or all income. It measures monthly pay, not ASHE weekly or hourly earnings. RTI 18-24 does not exactly match ASHE 18-21 or 22-29.",
            "",
            "ASHE age bands do not line up exactly with statutory minimum-wage thresholds. Minimum wage changes provide context, not causal proof of ASHE changes.",
            "",
            "The decomposition uses ASHE medians from separate tables. It can separate hourly pay, hours, and residual movements descriptively, but it is not a causal explanation.",
            "",
            "These outputs add modelling context, but they do not replace ASHE, do not identify causal effects, and do not provide official forecasts.",
            "",
        ]
    )
    path = evidence_root / "final_claims.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build final claims from evidence outputs.")
    parser.parse_args(argv)
    print(build_final_claims())


if __name__ == "__main__":
    main()
