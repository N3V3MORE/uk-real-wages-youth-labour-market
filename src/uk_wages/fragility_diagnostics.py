from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .utils import ensure_dir, load_yaml, project_path, write_dataframe


DEFAULT_MATERIALITY_THRESHOLD_PP = 1.0
DEFAULT_FOCUS_AGE_GROUPS = ["18-21", "22-29", "25-34", "30-39"]
ASSUMPTION_COLUMNS = [
    "baseline_year",
    "deflator",
    "inflation_period",
    "wage_measure",
    "work_status",
]
ONE_WAY_COLUMNS = [
    "age_group",
    "experiment_name",
    "spec_tier",
    "changed_assumption",
    "baseline_value",
    "alternative_value",
    "baseline_real_pct_change",
    "alternative_real_pct_change",
    "difference_pp",
    "sign_flip",
    "material_disagreement",
    "interpretation",
]
MINIMAL_FLIP_COLUMNS = [
    "age_group",
    "baseline_result",
    "flipped_result",
    "number_of_assumptions_changed",
    "changed_assumptions",
    "material_flip",
    "interpretation",
]


def load_materiality_threshold(
    config_path: str | Path = project_path("config", "analysis.yaml"),
) -> float:
    config = load_yaml(config_path)
    return float(config.get("materiality_threshold_pp", DEFAULT_MATERIALITY_THRESHOLD_PP))


def classify_materiality(value: float, *, threshold_pp: float) -> str:
    if pd.isna(value):
        return "near_zero_or_inconclusive"
    if float(value) >= threshold_pp:
        return "positive_material"
    if float(value) <= -threshold_pp:
        return "negative_material"
    return "near_zero_or_inconclusive"


def material_disagreement(
    baseline_value: float,
    alternative_value: float,
    *,
    threshold_pp: float,
) -> bool:
    baseline_class = classify_materiality(baseline_value, threshold_pp=threshold_pp)
    alternative_class = classify_materiality(alternative_value, threshold_pp=threshold_pp)
    if baseline_class == alternative_class:
        return False
    if baseline_class == alternative_class == "near_zero_or_inconclusive":
        return False
    return abs(float(alternative_value) - float(baseline_value)) >= threshold_pp


def sign_flip(baseline_value: float, alternative_value: float) -> bool:
    if pd.isna(baseline_value) or pd.isna(alternative_value):
        return False
    baseline = float(baseline_value)
    alternative = float(alternative_value)
    if baseline == 0 or alternative == 0:
        return False
    return (baseline < 0 < alternative) or (baseline > 0 > alternative)


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).map(
        lambda value: str(value).strip().lower() in {"true", "1", "yes"}
    )


def _baseline_row(group: pd.DataFrame) -> pd.Series:
    baseline = group[group["experiment_name"].eq("baseline")]
    if baseline.empty and "difference_from_baseline" in group:
        baseline = group[group["difference_from_baseline"].fillna(0).abs().le(1e-9)]
    if baseline.empty:
        baseline = group.head(1)
    return baseline.iloc[0]


def _available_assumption_columns(matrix: pd.DataFrame) -> list[str]:
    return [column for column in ASSUMPTION_COLUMNS if column in matrix.columns]


def _changed_assumptions(baseline: pd.Series, candidate: pd.Series, columns: Iterable[str]) -> list[str]:
    changed: list[str] = []
    for column in columns:
        baseline_value = baseline.get(column)
        candidate_value = candidate.get(column)
        if pd.isna(baseline_value) and pd.isna(candidate_value):
            continue
        if baseline_value != candidate_value:
            changed.append(column)
    return changed


def _interpretation(
    baseline_value: float,
    alternative_value: float,
    *,
    threshold_pp: float,
) -> str:
    if material_disagreement(
        baseline_value,
        alternative_value,
        threshold_pp=threshold_pp,
    ):
        return (
            "Material disagreement: the alternative changes the substantive conclusion "
            "relative to the baseline."
        )
    if sign_flip(baseline_value, alternative_value):
        return "Near-zero sign flip: direction changes, but the magnitude is below materiality."
    return "No material disagreement with the baseline."


def build_one_way_sensitivity(
    matrix: pd.DataFrame,
    output_root: str | Path,
    *,
    age_groups: Iterable[str] = DEFAULT_FOCUS_AGE_GROUPS,
    threshold_pp: float,
) -> Path:
    output_root = ensure_dir(output_root)
    rows: list[dict[str, object]] = []
    assumption_columns = _available_assumption_columns(matrix)

    for age_group in age_groups:
        group = matrix[matrix["age_group"].eq(age_group)].copy()
        if group.empty:
            continue
        baseline = _baseline_row(group)
        for candidate in group.itertuples(index=False):
            candidate_series = pd.Series(candidate._asdict())
            if candidate_series["experiment_name"] == baseline["experiment_name"]:
                continue
            changed = _changed_assumptions(baseline, candidate_series, assumption_columns)
            if len(changed) != 1:
                continue
            baseline_value = float(baseline["baseline_real_pct_change"])
            alternative_value = float(candidate_series["real_pct_change"])
            changed_column = changed[0]
            rows.append(
                {
                    "age_group": age_group,
                    "experiment_name": candidate_series["experiment_name"],
                    "spec_tier": candidate_series.get("spec_tier", "all"),
                    "changed_assumption": changed_column,
                    "baseline_value": baseline[changed_column],
                    "alternative_value": candidate_series[changed_column],
                    "baseline_real_pct_change": round(baseline_value, 4),
                    "alternative_real_pct_change": round(alternative_value, 4),
                    "difference_pp": round(alternative_value - baseline_value, 4),
                    "sign_flip": sign_flip(baseline_value, alternative_value),
                    "material_disagreement": material_disagreement(
                        baseline_value,
                        alternative_value,
                        threshold_pp=threshold_pp,
                    ),
                    "interpretation": _interpretation(
                        baseline_value,
                        alternative_value,
                        threshold_pp=threshold_pp,
                    ),
                }
            )

    output = output_root / "one_way_sensitivity.csv"
    frame = pd.DataFrame(rows, columns=ONE_WAY_COLUMNS)
    write_dataframe(frame, output)
    return output


def build_minimal_flip_specs(
    matrix: pd.DataFrame,
    output_root: str | Path,
    *,
    threshold_pp: float,
) -> Path:
    output_root = ensure_dir(output_root)
    rows: list[dict[str, object]] = []
    assumption_columns = _available_assumption_columns(matrix)

    for age_group, group in matrix.groupby("age_group"):
        baseline = _baseline_row(group)
        candidates: list[dict[str, object]] = []
        for candidate in group.itertuples(index=False):
            candidate_series = pd.Series(candidate._asdict())
            if candidate_series["experiment_name"] == baseline["experiment_name"]:
                continue
            baseline_value = float(baseline["baseline_real_pct_change"])
            alternative_value = float(candidate_series["real_pct_change"])
            changed = _changed_assumptions(baseline, candidate_series, assumption_columns)
            has_sign_flip = sign_flip(baseline_value, alternative_value)
            has_material_flip = material_disagreement(
                baseline_value,
                alternative_value,
                threshold_pp=threshold_pp,
            )
            if not has_sign_flip and not has_material_flip:
                continue
            candidates.append(
                {
                    "age_group": age_group,
                    "baseline_result": classify_materiality(
                        baseline_value,
                        threshold_pp=threshold_pp,
                    ),
                    "flipped_result": classify_materiality(
                        alternative_value,
                        threshold_pp=threshold_pp,
                    ),
                    "number_of_assumptions_changed": len(changed),
                    "changed_assumptions": ", ".join(changed) if changed else "none visible",
                    "material_flip": has_material_flip,
                    "interpretation": _interpretation(
                        baseline_value,
                        alternative_value,
                        threshold_pp=threshold_pp,
                    ),
                    "_sort_material": 1 if has_material_flip else 0,
                    "_sort_abs_diff": abs(alternative_value - baseline_value),
                }
            )
        if not candidates:
            continue
        selected = sorted(
            candidates,
            key=lambda row: (
                -int(row["_sort_material"]),
                int(row["number_of_assumptions_changed"]),
                -float(row["_sort_abs_diff"]),
            ),
        )[0]
        selected.pop("_sort_material")
        selected.pop("_sort_abs_diff")
        rows.append(selected)

    output = output_root / "minimal_flip_specs.csv"
    frame = pd.DataFrame(rows, columns=MINIMAL_FLIP_COLUMNS)
    write_dataframe(frame, output)
    return output


def build_fragility_diagnostics(
    matrix: pd.DataFrame,
    output_root: str | Path,
    *,
    threshold_pp: float,
) -> Path:
    output_root = ensure_dir(output_root)
    one_way_path = output_root / "one_way_sensitivity.csv"
    minimal_path = output_root / "minimal_flip_specs.csv"
    one_way = pd.read_csv(one_way_path) if one_way_path.exists() else pd.DataFrame()
    minimal = pd.read_csv(minimal_path) if minimal_path.exists() else pd.DataFrame()

    lines = [
        "# Fragility Diagnostics",
        "",
        "## Materiality",
        "",
        (
            f"Results are treated as materially positive or negative only when the real "
            f"earnings change is at least {threshold_pp:.1f} percentage point away from zero. "
            "Smaller sign changes are labelled near-zero or inconclusive."
        ),
        "",
        "## Fragility diagnostics for 18-21",
        "",
    ]
    focus = one_way[one_way["age_group"].eq("18-21")] if not one_way.empty else pd.DataFrame()
    if focus.empty:
        lines.append("No one-way 18-21 sensitivity rows were available.")
    else:
        material = focus[_bool_series(focus["material_disagreement"])]
        near_zero_flips = focus[_bool_series(focus["sign_flip"]) & ~_bool_series(focus["material_disagreement"])]
        if material.empty:
            lines.append("No one-way assumption change produced a material 18-21 disagreement.")
        else:
            drivers = ", ".join(sorted(material["changed_assumption"].astype(str).unique()))
            lines.append(f"Material 18-21 disagreements are driven by: {drivers}.")
        if near_zero_flips.empty:
            lines.append("No one-way near-zero sign flips were found for 18-21.")
        else:
            drivers = ", ".join(sorted(near_zero_flips["changed_assumption"].astype(str).unique()))
            lines.append(f"Near-zero sign flips are separated from material disagreements: {drivers}.")
    lines.append("")

    lines.extend(["## Minimal flip diagnostics", ""])
    if minimal.empty:
        lines.append("No minimal flip specifications were found.")
    else:
        for row in minimal.itertuples(index=False):
            lines.append(
                f"- {row.age_group}: {row.number_of_assumptions_changed} changed assumption(s) "
                f"({row.changed_assumptions}); material flip: {bool(row.material_flip)}."
            )
    lines.append("")

    lines.extend(
        [
            "## Recommended policy wording",
            "",
            (
                "Use cautious wording for the youngest workers: say the 18-21 real earnings "
                "finding is sensitive to baseline and sample choices when material disagreements "
                "appear, and do not describe near-zero sign flips as decisive reversals."
            ),
        ]
    )
    path = output_root / "fragility_diagnostics.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
