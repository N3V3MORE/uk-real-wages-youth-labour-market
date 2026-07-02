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
    triangulation = _require_text(evidence_root / "triangulation_report.md", "triangulation report")

    latest_year = _summary_value(summary, "18-21", "latest_year")
    lines = [
        "# Final Claims",
        "",
        "These are the frozen reviewer-facing interpretations for the current evidence package.",
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
            "better or worse off in real earnings terms after 2019. The result is sensitive "
            "to reasonable specification choices."
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
        "This is still an ASHE annual age-group finding and should not be treated as monthly evidence.",
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
        "A05 is a separate labour-market dataset, so it corroborates stress conditions rather than validating age-specific ASHE wage changes.",
        "",
        "Caveats:",
        "A05 is rolling three-month labour-market evidence and is not an earnings dataset.",
        "",
        "Recommended wording for the policy brief and dashboard:",
        "Use A05 as descriptive labour-market stress context alongside, not as proof of, age-specific wage movements.",
        "",
        "## Claim 4: Current monthly wage trend",
        "",
        "Verdict: descriptive only",
        "",
        "Primary evidence:",
        _latest_earn01_line(processed_root),
        "",
        "Robustness evidence:",
        triangulation,
        "",
        "Caveats:",
        "EARN01 provides a current whole-economy wage trend but should not be interpreted as age-specific evidence.",
        "",
        "Recommended wording for the policy brief and dashboard:",
        "EARN01 provides a current whole-economy wage trend, not age-specific evidence for 18-21 or 22-29 workers.",
        "",
    ]
    path = evidence_root / "final_claims.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build frozen final claims from evidence outputs.")
    parser.parse_args(argv)
    print(build_final_claims())


if __name__ == "__main__":
    main()
