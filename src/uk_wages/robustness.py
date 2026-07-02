from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .evidence import build_evidence_report
from .experiment_runner import EXPERIMENT_ROOT, OUTPUT_ROOT, run_experiment
from .experiment_schema import load_experiment
from .utils import ensure_dir, write_dataframe


EVIDENCE_ROOT = OUTPUT_ROOT / "evidence"


def sign_flipped(baseline: float, candidate: float) -> bool:
    if baseline == 0 or candidate == 0:
        return False
    return (baseline < 0 < candidate) or (baseline > 0 > candidate)


def fragility_label(score: float) -> str:
    if score <= 0.10:
        return "robust"
    if score <= 0.30:
        return "moderately robust"
    if score < 0.50:
        return "fragile"
    return "not robust"


def compute_fragility_scores(matrix: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for age_group, group in matrix.groupby("age_group"):
        total = len(group)
        disagree = int((~group["supports_main_claim"].astype(bool)).sum())
        score = disagree / total if total else 0.0
        rows.append(
            {
                "claim": f"{age_group} direction matches baseline",
                "age_group": age_group,
                "specifications_tested": total,
                "specifications_that_disagree": disagree,
                "fragility_score": round(score, 4),
                "assessment": fragility_label(score),
            }
        )
    return pd.DataFrame(rows).sort_values("age_group").reset_index(drop=True)


def experiment_specs(root: str | Path = EXPERIMENT_ROOT) -> list[Path]:
    paths = sorted(Path(root).glob("*.yaml"))
    baseline = [path for path in paths if path.stem == "baseline"]
    rest = [path for path in paths if path.stem != "baseline"]
    return baseline + rest


def run_all_experiments(
    *,
    experiment_root: str | Path = EXPERIMENT_ROOT,
    output_root: str | Path = OUTPUT_ROOT,
) -> pd.DataFrame:
    output_root = Path(output_root)
    comparisons: list[pd.DataFrame] = []
    for path in experiment_specs(experiment_root):
        result = run_experiment(load_experiment(path), output_root=output_root)
        comparisons.append(result.comparison_table)
    matrix = pd.concat(comparisons, ignore_index=True) if comparisons else pd.DataFrame()
    evidence_root = ensure_dir(output_root / "evidence")
    write_dataframe(matrix, evidence_root / "robustness_matrix.csv")
    scores = compute_fragility_scores(matrix)
    write_dataframe(scores, evidence_root / "fragility_scores.csv")
    build_evidence_report(output_root=output_root)
    build_contrarian_report(matrix, evidence_root)
    return matrix


def build_contrarian_report(matrix: pd.DataFrame, output_root: str | Path = EVIDENCE_ROOT) -> Path:
    output_root = ensure_dir(output_root)
    contrarian = matrix[
        matrix["sign_flip_vs_baseline"].astype(bool)
        | (matrix["difference_from_baseline"].abs() >= 2.0)
        | (~matrix["supports_main_claim"].astype(bool))
    ].copy()
    contrarian = contrarian.sort_values(
        ["sign_flip_vs_baseline", "difference_from_baseline"], ascending=[False, True]
    )
    lines = ["# Contrarian findings", ""]
    if contrarian.empty:
        lines.append("No specifications materially weakened or reversed the baseline direction.")
    else:
        for idx, row in enumerate(contrarian.itertuples(index=False), start=1):
            note = "" if pd.isna(row.notes) else str(row.notes)
            lines.extend(
                [
                    f"## Finding {idx}: {row.experiment_name} complicates {row.age_group}",
                    "",
                    f"Baseline result: {row.baseline_real_pct_change:.2f}%.",
                    f"Contrarian specification result: {row.real_pct_change:.2f}%.",
                    f"Difference from baseline: {row.difference_from_baseline:.2f} percentage points.",
                    f"Sign flip: {bool(row.sign_flip_vs_baseline)}.",
                    "",
                    "Interpretation:",
                    note or "Magnitude changes materially versus the baseline.",
                    "",
                ]
            )
    path = output_root / "contrarian_findings.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run robustness experiments and contrarian checks.")
    parser.add_argument("--run-all", action="store_true", help="Run all YAML experiments.")
    parser.add_argument("--contrarian", action="store_true", help="Build contrarian findings.")
    args = parser.parse_args(argv)
    if args.run_all:
        matrix = run_all_experiments()
        print(OUTPUT_ROOT / "evidence" / "robustness_matrix.csv")
        return
    if args.contrarian:
        matrix_path = OUTPUT_ROOT / "evidence" / "robustness_matrix.csv"
        if not matrix_path.exists():
            matrix = run_all_experiments()
        else:
            matrix = pd.read_csv(matrix_path)
        print(build_contrarian_report(matrix, OUTPUT_ROOT / "evidence"))
        return
    parser.error("Use --run-all or --contrarian.")


if __name__ == "__main__":
    main()
