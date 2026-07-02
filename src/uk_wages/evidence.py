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
    if diagnostics_path.exists():
        lines.extend(
            [
                "## Fragility Diagnostics",
                "",
                "See `outputs/evidence/fragility_diagnostics.md` for one-way sensitivity and minimal flip details.",
                "",
            ]
        )
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
