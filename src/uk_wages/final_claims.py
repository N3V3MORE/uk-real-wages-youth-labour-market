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


def _claim_verdict(claims: pd.DataFrame, claim_id: str, default: str = "inconclusive") -> str:
    if claims.empty or "claim_id" not in claims.columns:
        return default
    match = claims[claims["claim_id"].eq(claim_id)]
    if match.empty:
        return default
    return str(match.iloc[0].get("verdict", default))


def _first_claim_verdict(
    claims: pd.DataFrame,
    claim_ids: list[str],
    default: str = "inconclusive",
) -> str:
    for claim_id in claim_ids:
        verdict = _claim_verdict(claims, claim_id, "")
        if verdict:
            return verdict
    return default


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
    _require_text(evidence_root / "triangulation_report.md", "triangulation report")
    _require_text(
        evidence_root / "rti_ashe_triangulation.md",
        "RTI-ASHE triangulation report",
    )
    _require_text(
        evidence_root / "ashe_decomposition_report.md",
        "ASHE decomposition report",
    )
    _require_text(
        evidence_root / "minimum_wage_context.md",
        "minimum wage context report",
    )

    latest_year = _summary_value(summary, "18-21", "latest_year")
    lines = [
        "# Final Claims",
        "",
        "Use these claim wordings when describing the current outputs.",
        "",
        "## Claim 1: 18-21 real earnings",
        "",
        "Verdict: fragile / ambiguous",
        "",
        "Primary evidence:",
        (
            f"The baseline ASHE CPIH comparison shows 18-21 real earnings change of "
            f"{_summary_value(summary, '18-21', 'real_pct_change')}% from 2019 to {latest_year}."
        ),
        "",
        "Robustness evidence:",
        f"Claim assessment verdict: {_claim_verdict(claims, 'c1_youngest_real_wages', 'fragile')}.",
        _fragility_line(scores, "18-21"),
        diagnostics.split("## Fragility diagnostics for 18-21", 1)[-1].strip().split("\n\n", 1)[0]
        if "## Fragility diagnostics for 18-21" in diagnostics
        else "Fragility diagnostics were not available.",
        "",
        "Caveats:",
        (
            "The evidence does not support a simple claim that 18-21 workers clearly became "
            "better or worse off in real earnings terms after 2019. The result moves under "
            "reasonable specification choices."
        ),
        "",
        "Recommended wording for the policy brief and dashboard:",
        (
            "The 18-21 real-earnings result is ambiguous and specification-dependent; "
            "state the baseline, deflator, worker definition, and earnings measure when discussing it."
        ),
        "",
        "## Claim 2: 22-29 real earnings",
        "",
        f"Verdict: {_first_claim_verdict(claims, ['c2_22_29_real_wages', 'c2_young_workers_vs_prime_age'], 'moderately robust')}",
        "",
        "Primary evidence:",
        (
            f"The baseline ASHE CPIH comparison shows 22-29 real earnings change of "
            f"{_summary_value(summary, '22-29', 'real_pct_change')}% from 2019 to "
            f"{_summary_value(summary, '22-29', 'latest_year')}."
        ),
        "",
        "Robustness evidence:",
        _fragility_line(scores, "22-29"),
        "",
        "Caveats:",
        "This is still an annual ASHE age-group finding, not monthly evidence.",
        "",
        "Recommended wording for the policy brief and dashboard:",
        "The 22-29 result is more stable than the 18-21 result, but should still be reported with the tested assumptions.",
        "",
        "## Claim 3: Youth labour-market stress",
        "",
        "Verdict: descriptive / corroborating stress signal",
        "",
        "Primary evidence:",
        _latest_youth_gap_line(output_root),
        "",
        "Robustness evidence:",
        "A05 is a separate labour-market dataset. It can show stress conditions, but it cannot validate age-specific ASHE wage changes.",
        "",
        "Caveats:",
        "A05 is rolling three-month labour-market evidence and is not an earnings dataset.",
        "",
        "Recommended wording for the policy brief and dashboard:",
        "Use A05 as labour-market stress context, not as proof of age-specific wage movements.",
        "",
        "## Claim 4: Current monthly wage trend",
        "",
        "Verdict: descriptive only",
        "",
        "Primary evidence:",
        _latest_earn01_line(processed_root),
        "",
        "Supporting evidence:",
        "The triangulation report compares ASHE with EARN01 and records that EARN01 is not age-specific.",
        "",
        "Caveats:",
        "EARN01 is not age-specific; it provides a current whole-economy wage trend and should not be interpreted as age-specific evidence.",
        "",
        "Recommended wording for the policy brief and dashboard:",
        "EARN01 provides a current whole-economy wage trend, not age-specific evidence for 18-21 or 22-29 workers.",
        "",
        "## Claim 5: RTI monthly age-pay triangulation",
        "",
        "Verdict: descriptive / source-bounded",
        "",
        "Primary evidence:",
        _latest_rti_line(output_root),
        "",
        "Supporting evidence:",
        "The RTI triangulation report compares RTI 18-24 with ASHE 18-21 and 22-29, and records the age-band mismatch.",
        "",
        "Caveats:",
        "RTI is PAYE administrative data. It covers payrolled employees, not self-employment or all income. It measures monthly pay, not ASHE weekly or hourly earnings. RTI 18-24 does not exactly match ASHE 18-21 or 22-29.",
        "",
        "Recommended wording for the policy brief and dashboard:",
        "RTI provides monthly PAYE age-pay triangulation, not a replacement for ASHE.",
        "",
        "## Claim 6: Hourly pay versus hours",
        "",
        "Verdict: descriptive decomposition",
        "",
        "Primary evidence:",
        _decomposition_line(output_root),
        "",
        "Supporting evidence:",
        "The ASHE decomposition report confirms the weekly, hourly, and paid-hours workbooks were available and keeps a residual term.",
        "",
        "Caveats:",
        "The decomposition uses ASHE medians from separate tables. It can separate hourly pay, hours, and residual movements descriptively, but it is not a causal explanation.",
        "",
        "Recommended wording for the policy brief and dashboard:",
        "Weekly earnings changes can be decomposed into hourly pay, hours, and residual movement; do not describe the decomposition as proof of cause.",
        "",
        "## Claim 7: Minimum wage context",
        "",
        "Verdict: policy context only",
        "",
        "Primary evidence:",
        _minimum_wage_line(output_root),
        "",
        "Supporting evidence:",
        "The minimum wage context report uses GOV.UK rates from April 2019 onward and flags the statutory age-threshold mismatch.",
        "",
        "Caveats:",
        "ASHE age bands do not line up exactly with statutory minimum-wage thresholds. Minimum wage changes provide context, not causal proof of ASHE changes.",
        "",
        "Recommended wording for the policy brief and dashboard:",
        "Use minimum wage rates as wage-floor context for young workers, not as a causal claim.",
        "",
    ]
    path = evidence_root / "final_claims.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build final claims from evidence outputs.")
    parser.parse_args(argv)
    print(build_final_claims())


if __name__ == "__main__":
    main()
