from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .experiment_schema import ExperimentSpec, load_experiment
from .fragility_diagnostics import (
    classify_materiality,
    load_materiality_threshold,
    material_disagreement,
)
from .utils import ensure_dir, project_path, write_dataframe, write_json


PROCESSED_ROOT = project_path("data", "processed")
OUTPUT_ROOT = project_path("outputs")
EXPERIMENT_ROOT = project_path("experiments")

WAGE_MEASURE_MAP = {
    "median_weekly": "median_weekly_gross",
    "mean_weekly": "mean_weekly_gross",
    "annual": "median_annual_gross",
}
WORK_STATUS_MAP = {"all": "All", "full_time": "Full-Time"}
SEX_MAP = {"all": "All", "male": "Male", "female": "Female"}
DEFLATOR_COLUMNS = {
    ("cpih", "april"): "cpih_april_index",
    ("cpi", "april"): "cpi_april_index",
    ("cpih", "calendar_year_average"): "cpih_calendar_year_avg",
    ("cpi", "calendar_year_average"): "cpi_calendar_year_avg",
}


@dataclass
class ExperimentResult:
    spec: ExperimentSpec
    experiment_dir: Path
    age_group_table: pd.DataFrame
    comparison_table: pd.DataFrame
    latest_table: pd.DataFrame
    summary: dict[str, object]


def sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _price_column(spec: ExperimentSpec) -> str:
    return DEFLATOR_COLUMNS[(spec.assumptions.deflator, spec.assumptions.inflation_period)]


def _filtered_ashe(spec: ExperimentSpec, processed_root: Path) -> pd.DataFrame:
    ashe = pd.read_parquet(processed_root / "ashe_age_annual.parquet")
    measure = WAGE_MEASURE_MAP[spec.assumptions.wage_measure]
    if measure not in set(ashe["earnings_measure"]):
        raise ValueError(f"Wage measure {spec.assumptions.wage_measure!r} is not available.")
    result = ashe[
        ashe["earnings_measure"].eq(measure)
        & ashe["work_status"].eq(WORK_STATUS_MAP[spec.assumptions.work_status])
        & ashe["sex"].eq(SEX_MAP[spec.assumptions.sex])
        & ~ashe["age_group"].eq("All employees")
    ].copy()
    if spec.assumptions.age_groups:
        result = result[result["age_group"].isin(spec.assumptions.age_groups)]
    if spec.assumptions.include_years is not None:
        result = result[result["year"].isin(spec.assumptions.include_years)]
    if spec.assumptions.exclude_years:
        result = result[~result["year"].isin(spec.assumptions.exclude_years)]
    if spec.assumptions.end_year is not None:
        result = result[result["year"].le(spec.assumptions.end_year)]
    if result.empty:
        raise ValueError("Experiment filters produced no ASHE rows.")
    if (result["nominal_earnings"] <= 0).any():
        raise ValueError("Nominal earnings must be positive.")
    return result


def _real_earnings_table(spec: ExperimentSpec, processed_root: Path) -> pd.DataFrame:
    ashe = _filtered_ashe(spec, processed_root)
    inflation = pd.read_parquet(processed_root / "inflation_annual.parquet")
    price_col = _price_column(spec)
    price = inflation[["year", price_col]].copy()
    if (price[price_col] <= 0).any():
        raise ValueError("Inflation index values must be positive.")
    joined = ashe.merge(price, on="year", how="inner")
    base_nominal = (
        joined[joined["year"].eq(spec.assumptions.baseline_year)]
        .set_index("age_group")["nominal_earnings"]
        .to_dict()
    )
    if not base_nominal:
        raise ValueError("No baseline ASHE rows found for experiment.")
    base_price_rows = price[price["year"].eq(spec.assumptions.baseline_year)]
    if base_price_rows.empty:
        raise ValueError("No baseline inflation row found for experiment.")
    base_price = float(base_price_rows.iloc[0][price_col])
    joined = joined[joined["age_group"].isin(base_nominal)].copy()
    joined["price_index_since_baseline"] = joined[price_col] / base_price * 100
    joined["nominal_earnings_index_since_baseline"] = joined.apply(
        lambda row: row["nominal_earnings"] / base_nominal[row["age_group"]] * 100,
        axis=1,
    )
    joined["real_earnings_index_since_baseline"] = (
        joined["nominal_earnings_index_since_baseline"] / joined["price_index_since_baseline"] * 100
    )
    joined["real_pct_change_since_baseline"] = joined["real_earnings_index_since_baseline"] - 100
    baseline_rows = joined[joined["year"].eq(spec.assumptions.baseline_year)]
    if not (baseline_rows["real_earnings_index_since_baseline"].round(8) == 100).all():
        raise ValueError("Real wage index must equal 100 in the baseline year.")
    return joined.sort_values(["age_group", "year"]).reset_index(drop=True)


def latest_by_age(table: pd.DataFrame) -> pd.DataFrame:
    latest = table.sort_values("year").groupby("age_group", as_index=False).tail(1).copy()
    latest["rank_vs_other_age_groups"] = latest["real_pct_change_since_baseline"].rank(
        ascending=False, method="dense"
    )
    return latest.sort_values("age_group").reset_index(drop=True)


def _young_gap(latest: pd.DataFrame, comparison_group: str) -> float | None:
    values = latest.set_index("age_group")["real_pct_change_since_baseline"]
    if "18-21" not in values or comparison_group not in values:
        return None
    return float(values["18-21"] - values[comparison_group])


def compare_with_baseline(
    spec: ExperimentSpec,
    latest: pd.DataFrame,
    output_root: Path,
    *,
    threshold_pp: float | None = None,
) -> pd.DataFrame:
    if threshold_pp is None:
        threshold_pp = load_materiality_threshold()
    compare_to = spec.outputs.compare_to
    if not compare_to:
        result = latest.copy()
        result["baseline_real_pct_change"] = result["real_pct_change_since_baseline"]
        result["difference_from_baseline"] = 0.0
        result["sign_flip_vs_baseline"] = False
        result["baseline_rank"] = result["rank_vs_other_age_groups"]
        result["rank_change_by_age_group"] = 0.0
    else:
        baseline_path = output_root / "experiments" / compare_to / "latest_by_age_group.csv"
        if not baseline_path.exists():
            raise FileNotFoundError(f"Baseline comparison output not found: {baseline_path}")
        baseline = pd.read_csv(baseline_path)
        result = latest.merge(
            baseline[
                [
                    "age_group",
                    "real_pct_change_since_baseline",
                    "rank_vs_other_age_groups",
                ]
            ],
            on="age_group",
            how="left",
            suffixes=("", "_baseline"),
        )
        result = result.rename(
            columns={
                "real_pct_change_since_baseline_baseline": "baseline_real_pct_change",
                "rank_vs_other_age_groups_baseline": "baseline_rank",
            }
        )
        result["difference_from_baseline"] = (
            result["real_pct_change_since_baseline"] - result["baseline_real_pct_change"]
        )
        result["sign_flip_vs_baseline"] = result.apply(
            lambda row: sign(row["real_pct_change_since_baseline"])
            != sign(row["baseline_real_pct_change"])
            and sign(row["real_pct_change_since_baseline"]) != 0
            and sign(row["baseline_real_pct_change"]) != 0,
            axis=1,
        )
        result["rank_change_by_age_group"] = result["rank_vs_other_age_groups"] - result["baseline_rank"]

    gap_25_34 = _young_gap(latest, "25-34")
    gap_30_39 = _young_gap(latest, "30-39")
    result["young_worker_gap_vs_25_34"] = gap_25_34
    result["young_worker_gap_vs_30_39"] = gap_30_39
    result["real_pct_change"] = result["real_pct_change_since_baseline"]
    result["baseline_classification"] = result["baseline_real_pct_change"].map(
        lambda value: classify_materiality(float(value), threshold_pp=threshold_pp)
    )
    result["result_classification"] = result["real_pct_change"].map(
        lambda value: classify_materiality(float(value), threshold_pp=threshold_pp)
    )
    result["material_disagreement"] = result.apply(
        lambda row: material_disagreement(
            float(row["baseline_real_pct_change"]),
            float(row["real_pct_change"]),
            threshold_pp=threshold_pp,
        ),
        axis=1,
    )
    result["supports_main_claim"] = ~result["sign_flip_vs_baseline"]
    result["evidence_strength"] = result["sign_flip_vs_baseline"].map(
        {True: "contradicts baseline", False: "supports baseline direction"}
    )
    result["notes"] = result.apply(
        lambda row: (
            "Material sign flip versus baseline."
            if bool(row["sign_flip_vs_baseline"]) and bool(row["material_disagreement"])
            else "Near-zero sign flip versus baseline."
            if bool(row["sign_flip_vs_baseline"])
            else "Material disagreement without a sign flip."
            if bool(row["material_disagreement"])
            else ""
        ),
        axis=1,
    )
    result["experiment_name"] = spec.experiment_name
    result["spec_tier"] = spec.spec_tier
    result["baseline_year"] = spec.assumptions.baseline_year
    result["deflator"] = spec.assumptions.deflator
    result["inflation_period"] = spec.assumptions.inflation_period
    result["wage_measure"] = spec.assumptions.wage_measure
    result["work_status"] = spec.assumptions.work_status
    return result[
        [
            "experiment_name",
            "spec_tier",
            "age_group",
            "baseline_year",
            "deflator",
            "inflation_period",
            "wage_measure",
            "work_status",
            "year",
            "real_pct_change",
            "baseline_real_pct_change",
            "difference_from_baseline",
            "sign_flip_vs_baseline",
            "baseline_classification",
            "result_classification",
            "material_disagreement",
            "rank_vs_other_age_groups",
            "baseline_rank",
            "rank_change_by_age_group",
            "young_worker_gap_vs_25_34",
            "young_worker_gap_vs_30_39",
            "supports_main_claim",
            "evidence_strength",
            "notes",
        ]
    ].rename(columns={"year": "latest_year"})


def _write_evidence_card(spec: ExperimentSpec, comparison: pd.DataFrame, experiment_dir: Path) -> Path:
    focus = comparison[comparison["age_group"].eq("18-21")]
    focus_text = "18-21 unavailable in this specification."
    status = "neutral"
    if not focus.empty:
        row = focus.iloc[0]
        status = "contradicts baseline" if bool(row["sign_flip_vs_baseline"]) else "supports baseline"
        focus_text = (
            f"18-21 real change: {row['real_pct_change']:.2f}% "
            f"(baseline comparison: {row['baseline_real_pct_change']:.2f}%)."
        )
    lines = [
        f"# Evidence card: {spec.experiment_name}",
        "",
        "## Question",
        spec.description,
        "",
        "## Changed assumption",
        (
            f"Deflator={spec.assumptions.deflator}; inflation_period={spec.assumptions.inflation_period}; "
            f"baseline_year={spec.assumptions.baseline_year}; wage_measure={spec.assumptions.wage_measure}; "
            f"work_status={spec.assumptions.work_status}."
        ),
        "",
        "## Result",
        focus_text,
        "",
        "## Evidence status",
        status,
    ]
    path = experiment_dir / "evidence_card.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_experiment(
    spec: ExperimentSpec,
    *,
    processed_root: str | Path = PROCESSED_ROOT,
    output_root: str | Path = OUTPUT_ROOT,
) -> ExperimentResult:
    processed_root = Path(processed_root)
    output_root = Path(output_root)
    experiment_dir = ensure_dir(output_root / "experiments" / spec.experiment_name)
    table = _real_earnings_table(spec, processed_root)
    latest = latest_by_age(table)
    threshold_pp = load_materiality_threshold()
    comparison = compare_with_baseline(spec, latest, output_root, threshold_pp=threshold_pp)
    summary = {
        "experiment_name": spec.experiment_name,
        "description": spec.description,
        "spec_tier": spec.spec_tier,
        "assumptions": asdict(spec.assumptions),
        "outputs": asdict(spec.outputs),
        "age_groups": sorted(table["age_group"].unique().tolist()),
        "latest_year": int(latest["year"].max()),
        "sign_flips": int(comparison["sign_flip_vs_baseline"].sum()),
        "material_disagreements": int(comparison["material_disagreement"].sum()),
    }

    write_json(experiment_dir / "assumption_manifest.json", asdict(spec))
    write_json(experiment_dir / "summary.json", summary)
    write_dataframe(table, experiment_dir / "age_group_real_earnings.csv")
    write_dataframe(latest, experiment_dir / "latest_by_age_group.csv")
    write_dataframe(comparison, experiment_dir / "comparison_vs_baseline.csv")
    _write_evidence_card(spec, comparison, experiment_dir)
    return ExperimentResult(spec, experiment_dir, table, comparison, latest, summary)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run a validated robustness experiment.")
    parser.add_argument("--spec", required=True, help="Path to an experiment YAML file.")
    args = parser.parse_args(argv)
    spec = load_experiment(args.spec)
    result = run_experiment(spec)
    print(result.experiment_dir)


if __name__ == "__main__":
    main()
