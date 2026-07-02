from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import ensure_dir, project_path


OUTPUT_ROOT = project_path("outputs")


def build_evidence_report(*, output_root: str | Path = OUTPUT_ROOT) -> Path:
    output_root = Path(output_root)
    evidence_root = ensure_dir(output_root / "evidence")
    matrix_path = evidence_root / "robustness_matrix.csv"
    scores_path = evidence_root / "fragility_scores.csv"
    claims_path = evidence_root / "claim_assessment.csv"
    diagnostics_path = evidence_root / "fragility_diagnostics.md"
    source_checks_path = evidence_root / "source_value_checks.csv"
    manual_audit_path = evidence_root / "manual_validation_audit.md"
    final_claims_path = evidence_root / "final_claims.md"
    triangulation_path = evidence_root / "triangulation_report.md"
    triangulation_summary_path = evidence_root / "triangulation_summary.csv"
    rti_path = evidence_root / "rti_ashe_triangulation.md"
    rti_annual_path = evidence_root / "rti_ashe_annual_summary.csv"
    decomposition_path = evidence_root / "ashe_decomposition_report.md"
    minimum_wage_path = evidence_root / "minimum_wage_context.md"
    quality_path = evidence_root / "ashe_quality_availability.md"
    uncertainty_path = evidence_root / "ashe_uncertainty_bands.md"
    composition_path = evidence_root / "ashe_composition_audit.md"
    confidence_path = evidence_root / "claim_confidence.md"
    lineage_path = evidence_root / "headline_number_lineage.md"
    lines = ["# Evidence Report", ""]
    if matrix_path.exists():
        matrix = pd.read_csv(matrix_path)
        specs = matrix["experiment_name"].nunique()
        flips = int(matrix["sign_flip_vs_baseline"].astype(bool).sum())
        material_disagreements = (
            int(matrix["material_disagreement"].astype(bool).sum())
            if "material_disagreement" in matrix.columns
            else 0
        )
        lines.extend(
            [
                "## Summary",
                "",
                f"Specifications tested: {specs}.",
                f"Age-group sign flips versus baseline: {flips}.",
                f"Material disagreements versus baseline: {material_disagreements}.",
                "",
            ]
        )
    if scores_path.exists():
        scores = pd.read_csv(scores_path)
        lines.extend(["## Fragility Scores", ""])
        for row in scores.itertuples(index=False):
            lines.append(
                f"- {row.age_group} [{row.spec_tier}]: {row.fragility_score:.1%} "
                f"({row.assessment}); {row.specifications_that_disagree}/"
                f"{row.specifications_tested} disagree; material disagreement rate "
                f"{row.material_fragility_score:.1%}."
            )
        lines.append("")
    if claims_path.exists():
        claims = pd.read_csv(claims_path)
        lines.extend(["## Claim Assessment", ""])
        for row in claims.itertuples(index=False):
            lines.append(f"- {row.claim_id}: {row.verdict}. {row.recommended_wording}")
        lines.append("")
    if source_checks_path.exists():
        source_checks = pd.read_csv(source_checks_path)
        status_counts = source_checks["status"].value_counts().to_dict()
        lines.extend(
            [
                "## Source Value Validation",
                "",
                "Manual source-value audit: `outputs/evidence/manual_validation_audit.md`.",
                "Status summary: "
                + ", ".join(
                    f"{status}={count}" for status, count in sorted(status_counts.items())
                ),
                "",
            ]
        )
    if diagnostics_path.exists():
        lines.extend(
            [
                "## Fragility Diagnostics",
                "",
                "See `outputs/evidence/fragility_diagnostics.md` for the one-way sensitivity checks and minimal flip details.",
                "",
            ]
        )
    if manual_audit_path.exists() and final_claims_path.exists():
        lines.extend(
            [
                "## Final Claim Files",
                "",
                "- `outputs/evidence/manual_validation_audit.md`",
                "- `outputs/evidence/final_claims.md`",
                "",
            ]
        )
    extra_reports = [
        ("ASHE-EARN01 triangulation report", triangulation_path),
        ("ASHE-EARN01 triangulation metrics", triangulation_summary_path),
        ("RTI triangulation", rti_path),
        ("RTI-ASHE annual concordance", rti_annual_path),
        ("ASHE hourly pay and hours decomposition", decomposition_path),
        ("Minimum wage context", minimum_wage_path),
        ("ASHE uncertainty and quality audit", quality_path),
        ("ASHE approximate CV bands", uncertainty_path),
        ("ASHE composition audit", composition_path),
        ("Claim confidence ladder", confidence_path),
        ("Headline number lineage", lineage_path),
    ]
    available_reports = [(label, path) for label, path in extra_reports if path.exists()]
    if available_reports:
        lines.extend(["## Evidence Pillars", ""])
        for label, path in available_reports:
            lines.append(f"- {label}: `{path.relative_to(output_root)}`")
        lines.append("")
    lines.extend(["## Evidence Cards", ""])
    card_paths = sorted((output_root / "experiments").glob("*/evidence_card.md"))
    if not card_paths:
        lines.append("No evidence cards found. Run `python -m uk_wages.robustness --run-all`.")
    for card_path in card_paths:
        lines.append(card_path.read_text(encoding="utf-8").strip())
        lines.append("")
    path = evidence_root / "evidence_report.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the evidence report from experiment outputs.")
    parser.add_argument("--build-report", action="store_true", help="Build outputs/evidence/evidence_report.md.")
    args = parser.parse_args(argv)
    if not args.build_report:
        parser.error("Use --build-report.")
    print(build_evidence_report())


if __name__ == "__main__":
    main()
