from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

from .fragility_diagnostics import material_disagreement
from .utils import ensure_dir, project_path, write_dataframe


CLAIM_COLUMNS = [
    "claim_id",
    "claim_text",
    "population",
    "outcome",
    "spec_tier",
    "specifications_tested",
    "directional_disagreements",
    "material_disagreements",
    "near_zero_sign_flips",
    "fragility_score",
    "material_fragility_score",
    "verdict",
    "recommended_wording",
]


def verdict_from_scores(fragility_score: float | None, material_fragility_score: float | None) -> str:
    if fragility_score is None or material_fragility_score is None:
        return "inconclusive"
    score = max(float(fragility_score), float(material_fragility_score))
    if score >= 0.50:
        return "not robust"
    if score >= 0.30:
        return "fragile"
    if score > 0.10:
        return "moderately robust"
    return "robust"


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).map(
        lambda value: str(value).strip().lower() in {"true", "1", "yes"}
    )


def _claim_age_groups(claim: dict[str, object], matrix: pd.DataFrame) -> list[str]:
    explicit = claim.get("age_groups")
    if isinstance(explicit, list):
        return [str(value) for value in explicit]

    population = str(claim.get("population", ""))
    known_age_groups = sorted(matrix["age_group"].dropna().astype(str).unique(), key=len, reverse=True)
    matches = [age_group for age_group in known_age_groups if re.search(re.escape(age_group), population)]
    return matches or known_age_groups


def _material_disagreement_series(rows: pd.DataFrame, *, threshold_pp: float) -> pd.Series:
    if "material_disagreement" in rows.columns:
        return _bool_series(rows["material_disagreement"])
    return rows.apply(
        lambda row: material_disagreement(
            float(row["baseline_real_pct_change"]),
            float(row["real_pct_change"]),
            threshold_pp=threshold_pp,
        ),
        axis=1,
    )


def _recommended_wording(claim: dict[str, object], verdict: str) -> str:
    text = str(claim.get("text", "This claim"))
    if verdict in {"fragile", "not robust"}:
        return (
            "Treat this claim as sensitive to defensible specification choices. "
            "Do not state it as a simple gain or loss; report the relevant baseline, "
            "deflator, worker definition, and sample caveats instead."
        )
    if verdict == "moderately robust":
        return (
            f"This claim is moderately robust but still sensitive to some specification choices: "
            f"{text}"
        )
    if verdict == "robust":
        return f"This claim is robust across the tested core specifications: {text}"
    return f"The evidence is inconclusive for this claim: {text}"


def assess_claims(
    claims: Iterable[dict[str, object]],
    matrix: pd.DataFrame,
    output_root: str | Path,
    *,
    threshold_pp: float = 1.0,
) -> Path:
    output_root = ensure_dir(output_root)
    rows: list[dict[str, object]] = []
    has_tiers = "spec_tier" in matrix.columns

    for claim in claims:
        age_groups = _claim_age_groups(claim, matrix)
        tier = str(claim.get("spec_tier", "core" if has_tiers else "all"))
        claim_rows = matrix[matrix["age_group"].astype(str).isin(age_groups)].copy()
        if has_tiers and tier != "all":
            claim_rows = claim_rows[claim_rows["spec_tier"].eq(tier)]

        if claim_rows.empty:
            rows.append(
                {
                    "claim_id": claim.get("claim_id", ""),
                    "claim_text": claim.get("text", ""),
                    "population": claim.get("population", ""),
                    "outcome": claim.get("outcome", ""),
                    "spec_tier": tier,
                    "specifications_tested": 0,
                    "directional_disagreements": 0,
                    "material_disagreements": 0,
                    "near_zero_sign_flips": 0,
                    "fragility_score": pd.NA,
                    "material_fragility_score": pd.NA,
                    "verdict": "inconclusive",
                    "recommended_wording": _recommended_wording(claim, "inconclusive"),
                }
            )
            continue

        material = _material_disagreement_series(claim_rows, threshold_pp=threshold_pp)
        if "sign_flip_vs_baseline" in claim_rows.columns:
            sign_flips = _bool_series(claim_rows["sign_flip_vs_baseline"])
        else:
            sign_flips = pd.Series(False, index=claim_rows.index)
        directional = material | (
            sign_flips & claim_rows["difference_from_baseline"].abs().ge(threshold_pp)
        )
        near_zero_flips = sign_flips & ~material
        total = len(claim_rows)
        fragility_score = float(directional.sum()) / total if total else None
        material_fragility_score = float(material.sum()) / total if total else None
        verdict = verdict_from_scores(fragility_score, material_fragility_score)
        rows.append(
            {
                "claim_id": claim.get("claim_id", ""),
                "claim_text": claim.get("text", ""),
                "population": claim.get("population", ""),
                "outcome": claim.get("outcome", ""),
                "spec_tier": tier,
                "specifications_tested": total,
                "directional_disagreements": int(directional.sum()),
                "material_disagreements": int(material.sum()),
                "near_zero_sign_flips": int(near_zero_flips.sum()),
                "fragility_score": round(fragility_score, 4) if fragility_score is not None else pd.NA,
                "material_fragility_score": (
                    round(material_fragility_score, 4)
                    if material_fragility_score is not None
                    else pd.NA
                ),
                "verdict": verdict,
                "recommended_wording": _recommended_wording(claim, verdict),
            }
        )

    output = output_root / "claim_assessment.csv"
    frame = pd.DataFrame(rows, columns=CLAIM_COLUMNS)
    write_dataframe(frame, output)
    return output


def update_policy_brief_with_claims(
    claim_assessment_path: str | Path,
    *,
    policy_path: str | Path = project_path("reports", "policy_brief.md"),
) -> Path | None:
    policy_path = Path(policy_path)
    if not policy_path.exists():
        return None
    claims = pd.read_csv(claim_assessment_path)
    if claims.empty:
        return None
    focus = claims[
        claims["population"].astype(str).str.contains("18-21", regex=False)
        | claims["claim_id"].astype(str).str.contains("young", case=False, regex=False)
    ]
    selected = focus.iloc[0] if not focus.empty else claims.iloc[0]
    marker = "## Robustness wording"
    current = policy_path.read_text(encoding="utf-8").rstrip()
    if marker in current:
        current = current.split(marker, 1)[0].rstrip()
    addition = "\n\n".join(
        [
            marker,
            str(selected["recommended_wording"]),
        ]
    )
    policy_path.write_text(f"{current}\n\n{addition}\n", encoding="utf-8")
    return policy_path
