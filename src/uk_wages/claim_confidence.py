from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import ensure_dir, project_path


OUTPUT_ROOT = project_path("outputs")
CONFIDENCE_LABELS = {
    "high confidence",
    "medium confidence",
    "low confidence",
    "descriptive only",
    "not supported",
}


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _age_from_claim(row: pd.Series) -> str | None:
    claim_id = str(row.get("claim_id", ""))
    if any(token in claim_id for token in ["rti", "hourly", "hours", "minimum_wage"]):
        return None
    text = " ".join(str(row.get(column, "")) for column in ["claim_id", "claim_text", "population"])
    for age_group in ["18-21", "22-29", "30-39"]:
        if age_group in text:
            return age_group
    return None


def _baseline_result(age_group: str | None, summary: pd.DataFrame) -> str:
    if not age_group or summary.empty or "age_group" not in summary.columns:
        return "Baseline result not age-specific in this claim."
    row = summary[summary["age_group"].astype(str).eq(age_group)]
    if row.empty:
        return f"No baseline ASHE row for {age_group}."
    item = row.iloc[0]
    return (
        f"ASHE {age_group} real weekly earnings changed by "
        f"{float(item['real_pct_change']):.2f}% to {int(item['latest_year'])}."
    )


def _robustness_status(age_group: str | None, scores: pd.DataFrame, verdict: str) -> str:
    if not age_group or scores.empty or "age_group" not in scores.columns:
        return verdict or "descriptive source-bound claim"
    focus = scores[scores["age_group"].astype(str).eq(age_group)]
    if "spec_tier" in focus.columns:
        core = focus[focus["spec_tier"].astype(str).eq("core")]
        if not core.empty:
            focus = core
    if focus.empty:
        return verdict or "no robustness score available"
    row = focus.iloc[0]
    return (
        f"{verdict or 'assessed'}; {int(row['material_disagreements'])} of "
        f"{int(row['specifications_tested'])} tested specifications materially disagree."
    )


def _quality_status(age_group: str | None, quality: pd.DataFrame) -> str:
    if not age_group:
        return "ASHE quality evidence is not directly relevant to this non-ASHE claim."
    if quality.empty:
        return "ASHE quality audit not available."
    focus = quality[
        quality["age_group"].astype(str).eq(age_group)
        & quality["measure"].astype(str).eq("weekly_gross")
        & quality["estimate"].astype(str).eq("median")
    ]
    if focus.empty:
        return f"No ASHE median weekly quality row for {age_group}."
    row = focus.iloc[0]
    if bool(row.get("missing_quality_evidence", False)):
        return f"ASHE {age_group} median weekly quality evidence is missing."
    cv = row.get("latest_cv_percent")
    return (
        f"ASHE {age_group} median weekly CV is {float(cv):.2f}% "
        f"({str(row['latest_quality_status']).replace('_', ' ')})."
    )


def _triangulation_status(claim_id: str, rti_text: str, composition: pd.DataFrame) -> str:
    if "rti" in claim_id:
        return "RTI is descriptive monthly PAYE triangulation, not an ASHE replacement."
    if "hourly" in claim_id or "hours" in claim_id:
        return "ASHE decomposition is descriptive and not causal."
    if "minimum_wage" in claim_id:
        return "Minimum wage evidence is wage-floor context only."
    if "youngest" in claim_id or "22_29" in claim_id or "young_workers" in claim_id:
        composition_note = ""
        if not composition.empty:
            composition_note = " Composition audit is available for ASHE work-status and sex rows."
        if rti_text:
            return "RTI 18-24 is a separate PAYE check that complicates direct ASHE wording." + composition_note
        return "No RTI triangulation text available." + composition_note
    return "No separate triangulation layer required."


def _source_validation_status(checks: pd.DataFrame) -> str:
    if checks.empty or "status" not in checks.columns:
        return "Source validation output not available."
    passed = int(checks["status"].astype(str).str.lower().eq("pass").sum())
    total = int(len(checks))
    return f"{passed}/{total} source-value checks pass."


def _confidence_label(claim_id: str, verdict: str, robustness: str, quality: str) -> str:
    verdict_key = verdict.strip().lower()
    if "youngest" in claim_id and verdict_key in {"fragile", "not robust"}:
        return "not supported"
    if any(token in claim_id for token in ["rti", "hourly", "hours", "minimum_wage"]):
        return "descriptive only"
    if verdict_key in {"fragile", "not robust"}:
        return "low confidence"
    if "missing" in quality.lower() or "unavailable" in quality.lower():
        return "low confidence"
    if verdict_key in {"moderately robust", "robust"}:
        return "medium confidence"
    return "descriptive only"


def _what_would_change(claim_id: str) -> str:
    if "youngest" in claim_id:
        return (
            "The assessment would strengthen if ASHE quality remains reliable, core specifications stay negative, "
            "hourly pay, weekly pay, full-time rows, and RTI align; it would weaken if quality flags are poor, "
            "full-time-only or mean measures remove the loss, or the result is mostly hours."
        )
    if "22_29" in claim_id or "young_workers" in claim_id:
        return (
            "The assessment would strengthen if ASHE quality remains reliable and robustness checks agree; "
            "it would weaken if source quality, work-status splits, or RTI comparisons point away from the ASHE result."
        )
    if "rti" in claim_id:
        return (
            "The assessment would strengthen as a triangulation signal if non-flash RTI months keep the same direction; "
            "it would weaken if revisions reverse the monthly PAYE pattern."
        )
    if "hourly" in claim_id or "hours" in claim_id:
        return (
            "The assessment would strengthen if work-status and quality audits show the same hours story; "
            "it would weaken if separate median tables or composition shifts explain most of the split."
        )
    if "minimum_wage" in claim_id:
        return (
            "The assessment would strengthen as context if ASHE hourly rows near the statutory floor move consistently; "
            "it would weaken if age-threshold mismatch or composition dominates."
        )
    return (
        "The assessment would strengthen if source validation, robustness, and triangulation agree; "
        "it would weaken if any source boundary is violated."
    )


def build_claim_confidence(*, output_root: str | Path = OUTPUT_ROOT) -> tuple[Path, Path]:
    output_root = Path(output_root)
    evidence = ensure_dir(output_root / "evidence")
    tables = output_root / "tables"
    claims = _read_csv(evidence / "claim_assessment.csv")
    if claims.empty:
        raise FileNotFoundError(f"Missing claim assessment: {evidence / 'claim_assessment.csv'}")
    scores = _read_csv(evidence / "fragility_scores.csv")
    checks = _read_csv(evidence / "source_value_checks.csv")
    quality = _read_csv(tables / "ashe_quality_summary.csv")
    composition = _read_csv(tables / "ashe_composition_change_by_age.csv")
    baseline = _read_csv(tables / "age_group_real_earnings_change.csv")
    rti_text = _read_text(evidence / "rti_ashe_triangulation.md")
    source_status = _source_validation_status(checks)

    rows: list[dict[str, object]] = []
    for claim in claims.iterrows():
        row = claim[1]
        claim_id = str(row.get("claim_id", ""))
        claim_text = str(row.get("claim_text", row.get("text", "")))
        verdict = str(row.get("verdict", ""))
        age_group = _age_from_claim(row)
        robustness = _robustness_status(age_group, scores, verdict)
        quality_status = _quality_status(age_group, quality)
        triangulation = _triangulation_status(claim_id, rti_text, composition)
        confidence = _confidence_label(claim_id, verdict, robustness, quality_status)
        if confidence not in CONFIDENCE_LABELS:
            raise ValueError(f"Unexpected confidence label: {confidence}")
        rows.append(
            {
                "claim_id": claim_id,
                "claim_text": claim_text,
                "baseline_result": _baseline_result(age_group, baseline),
                "robustness_status": robustness,
                "quality_status": quality_status,
                "triangulation_status": triangulation,
                "source_validation_status": source_status,
                "confidence_label": confidence,
                "recommended_public_wording": str(row.get("recommended_wording", claim_text)),
                "what_would_change_this_assessment": _what_would_change(claim_id),
            }
        )

    ladder = pd.DataFrame(rows)
    csv_path = evidence / "claim_confidence_ladder.csv"
    ladder.to_csv(csv_path, index=False)
    md_lines = [
        "# Claim Confidence Ladder",
        "",
        "This reader-facing layer combines baseline results, robustness, source validation, RTI triangulation, ASHE quality evidence, composition checks, decomposition, and source boundaries. It does not replace `claim_assessment.csv`.",
        "",
    ]
    for row in ladder.itertuples(index=False):
        md_lines.extend(
            [
                f"## {row.claim_id}",
                "",
                f"- Confidence: {row.confidence_label}",
                f"- Baseline: {row.baseline_result}",
                f"- Robustness: {row.robustness_status}",
                f"- Quality: {row.quality_status}",
                f"- Triangulation: {row.triangulation_status}",
                f"- Public wording: {row.recommended_public_wording}",
                f"- What would change this assessment: {row.what_would_change_this_assessment}",
                "",
            ]
        )
    md_path = evidence / "claim_confidence.md"
    md_path.write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")
    return csv_path, md_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build reader-facing claim confidence ladder.")
    parser.parse_args(argv)
    csv_path, _ = build_claim_confidence()
    print(csv_path)


if __name__ == "__main__":
    main()
