from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .claims import assess_claims, update_policy_brief_with_claims
from .evidence import build_evidence_report
from .experiment_runner import EXPERIMENT_ROOT, OUTPUT_ROOT, run_experiment
from .experiment_schema import load_experiment
from .fragility_diagnostics import (
    build_fragility_diagnostics,
    build_minimal_flip_specs,
    build_one_way_sensitivity,
    load_materiality_threshold,
    material_disagreement,
)
from .utils import ensure_dir, load_yaml, project_path, write_dataframe


EVIDENCE_ROOT = OUTPUT_ROOT / "evidence"
CLAIMS_CONFIG = project_path("config", "claims.yaml")
FRAGILITY_SCORE_COLUMNS = [
    "claim",
    "age_group",
    "spec_tier",
    "specifications_tested",
    "specifications_that_disagree",
    "material_disagreements",
    "fragility_score",
    "material_fragility_score",
    "assessment",
    "material_assessment",
]


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


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).map(
        lambda value: str(value).strip().lower() in {"true", "1", "yes"}
    )


def _disagreement_series(group: pd.DataFrame) -> pd.Series:
    if "supports_main_claim" in group.columns:
        return ~_bool_series(group["supports_main_claim"])
    if "sign_flip_vs_baseline" in group.columns:
        return _bool_series(group["sign_flip_vs_baseline"])
    return pd.Series(False, index=group.index)


def _material_disagreement_series(group: pd.DataFrame, *, threshold_pp: float) -> pd.Series:
    if "material_disagreement" in group.columns:
        return _bool_series(group["material_disagreement"])
    required = {"baseline_real_pct_change", "real_pct_change"}
    if required.issubset(group.columns):
        return group.apply(
            lambda row: material_disagreement(
                float(row["baseline_real_pct_change"]),
                float(row["real_pct_change"]),
                threshold_pp=threshold_pp,
            ),
            axis=1,
        )
    return _disagreement_series(group)


def _tier_groups(age_group_matrix: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    if "spec_tier" not in age_group_matrix.columns:
        return [("all", age_group_matrix)]
    tiers = ["all"]
    tiers.extend(
        tier
        for tier in ["core", "stress"]
        if tier in set(age_group_matrix["spec_tier"].dropna().astype(str))
    )
    groups: list[tuple[str, pd.DataFrame]] = []
    for tier in tiers:
        group = (
            age_group_matrix
            if tier == "all"
            else age_group_matrix[age_group_matrix["spec_tier"].eq(tier)]
        )
        groups.append((tier, group))
    return groups


def compute_fragility_scores(matrix: pd.DataFrame, *, threshold_pp: float = 1.0) -> pd.DataFrame:
    if matrix.empty:
        return pd.DataFrame(columns=FRAGILITY_SCORE_COLUMNS)
    rows: list[dict[str, object]] = []
    for age_group, age_group_matrix in matrix.groupby("age_group"):
        for tier, group in _tier_groups(age_group_matrix):
            total = len(group)
            disagree = int(_disagreement_series(group).sum())
            material = int(_material_disagreement_series(group, threshold_pp=threshold_pp).sum())
            score = disagree / total if total else 0.0
            material_score = material / total if total else 0.0
            rows.append(
                {
                    "claim": f"{age_group} direction matches baseline",
                    "age_group": age_group,
                    "spec_tier": tier,
                    "specifications_tested": total,
                    "specifications_that_disagree": disagree,
                    "material_disagreements": material,
                    "fragility_score": round(score, 4),
                    "material_fragility_score": round(material_score, 4),
                    "assessment": fragility_label(score),
                    "material_assessment": fragility_label(material_score),
                }
            )
    result = pd.DataFrame(rows, columns=FRAGILITY_SCORE_COLUMNS)
    tier_order = {"all": 0, "core": 1, "stress": 2}
    result["_tier_order"] = result["spec_tier"].map(tier_order).fillna(99)
    return result.sort_values(["age_group", "_tier_order"]).drop(columns="_tier_order").reset_index(drop=True)


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
    threshold_pp = load_materiality_threshold()
    for path in experiment_specs(experiment_root):
        result = run_experiment(load_experiment(path), output_root=output_root)
        comparisons.append(result.comparison_table)
    matrix = pd.concat(comparisons, ignore_index=True) if comparisons else pd.DataFrame()
    evidence_root = ensure_dir(output_root / "evidence")
    write_dataframe(matrix, evidence_root / "robustness_matrix.csv")
    scores = compute_fragility_scores(matrix, threshold_pp=threshold_pp)
    write_dataframe(scores, evidence_root / "fragility_scores.csv")
    build_one_way_sensitivity(
        matrix,
        evidence_root,
        threshold_pp=threshold_pp,
    )
    build_minimal_flip_specs(matrix, evidence_root, threshold_pp=threshold_pp)
    build_fragility_diagnostics(matrix, evidence_root, threshold_pp=threshold_pp)
    if CLAIMS_CONFIG.exists():
        claims_payload = load_yaml(CLAIMS_CONFIG).get("claims", [])
        claim_assessment = assess_claims(
            claims_payload,
            matrix,
            evidence_root,
            threshold_pp=threshold_pp,
        )
        update_policy_brief_with_claims(claim_assessment)
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
                    f"Material disagreement: {bool(getattr(row, 'material_disagreement', False))}.",
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
