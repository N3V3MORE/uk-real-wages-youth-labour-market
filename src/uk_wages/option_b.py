from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .utils import ensure_dir, project_path, write_dataframe


PROCESSED_ROOT = project_path("data", "processed")
OUTPUT_ROOT = project_path("outputs")
NOTEBOOK_ROOT = project_path("notebooks")

STRUCTURAL_BREAK_COLUMNS = [
    "age_group",
    "model",
    "model_note",
    "break_year",
    "pre_years",
    "post_years",
    "pre_mean_index",
    "post_mean_index",
    "level_shift_pp",
    "rss",
    "log_likelihood",
    "relative_weight",
]

FORECAST_COLUMNS = [
    "age_group",
    "forecast_year",
    "forecast_index",
    "rough_residual_band_lower",
    "rough_residual_band_upper",
    "model",
    "interval_note",
    "caveat",
]


def _ashe_series(real_age: pd.DataFrame) -> pd.DataFrame:
    required = {"year", "age_group", "real_earnings_index_2019_100"}
    missing = required.difference(real_age.columns)
    if missing:
        raise ValueError(f"Missing ASHE real-age columns: {sorted(missing)}")
    return real_age[list(required)].dropna().sort_values(["age_group", "year"])


def _log_likelihood(values: np.ndarray, groups: np.ndarray) -> tuple[float, float]:
    fitted = np.zeros_like(values, dtype=float)
    for group_value in np.unique(groups):
        mask = groups == group_value
        fitted[mask] = values[mask].mean()
    residuals = values - fitted
    rss = float(np.square(residuals).sum())
    sigma2 = max(rss / len(values), 1e-9)
    log_likelihood = -0.5 * len(values) * (math.log(2 * math.pi * sigma2) + 1)
    return log_likelihood, rss


def compute_structural_break_weights(
    real_age: pd.DataFrame,
    *,
    min_segment_years: int = 2,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    data = _ashe_series(real_age)
    for age_group, group in data.groupby("age_group"):
        ordered = group.sort_values("year")
        years = ordered["year"].astype(int).to_numpy()
        values = ordered["real_earnings_index_2019_100"].astype(float).to_numpy()
        if len(years) < min_segment_years * 2:
            continue
        candidates = [
            year
            for year in years[1:-1]
            if (years < year).sum() >= min_segment_years
            and (years >= year).sum() >= min_segment_years
        ]
        scored: list[dict[str, object]] = []
        for break_year in candidates:
            groups = np.where(years >= break_year, 1, 0)
            log_likelihood, rss = _log_likelihood(values, groups)
            pre_values = values[years < break_year]
            post_values = values[years >= break_year]
            scored.append(
                {
                    "age_group": age_group,
                    "model": "two_mean_level_shift",
                    "model_note": (
                        "relative likelihood weight conditional on one break; no no-break comparator"
                    ),
                    "break_year": int(break_year),
                    "pre_years": int(len(pre_values)),
                    "post_years": int(len(post_values)),
                    "pre_mean_index": round(float(pre_values.mean()), 4),
                    "post_mean_index": round(float(post_values.mean()), 4),
                    "level_shift_pp": round(float(post_values.mean() - pre_values.mean()), 4),
                    "rss": round(rss, 6),
                    "log_likelihood": log_likelihood,
                }
            )
        if not scored:
            continue
        max_log = max(float(row["log_likelihood"]) for row in scored)
        weights = [math.exp(float(row["log_likelihood"]) - max_log) for row in scored]
        total = sum(weights)
        for row, weight in zip(scored, weights):
            row["relative_weight"] = weight / total
            row["log_likelihood"] = round(float(row["log_likelihood"]), 6)
            rows.append(row)
    frame = pd.DataFrame(rows, columns=STRUCTURAL_BREAK_COLUMNS)
    if frame.empty:
        return frame
    return frame.sort_values(
        ["age_group", "relative_weight", "break_year"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def _index_at(real_age: pd.DataFrame, age_group: str, year: int) -> float:
    row = real_age[real_age["age_group"].eq(age_group) & real_age["year"].eq(year)]
    if row.empty:
        raise ValueError(f"Missing ASHE real index for {age_group} in {year}.")
    return float(row.iloc[0]["real_earnings_index_2019_100"])


def _minimum_wage_index(
    minimum_wage: pd.DataFrame,
    policy_series: str,
    year: int,
) -> float | pd.NA:
    if minimum_wage.empty:
        return pd.NA
    focus = minimum_wage[
        minimum_wage["policy_series"].astype(str).eq(policy_series)
        & minimum_wage["effective_year"].eq(year)
    ]
    if focus.empty or "real_statutory_wage_index_2019_100" not in focus.columns:
        return pd.NA
    return float(focus.iloc[0]["real_statutory_wage_index_2019_100"])


def _minimum_wage_change(minimum_wage: pd.DataFrame, policy_series: str, pre_year: int, post_year: int):
    floor_pre = _minimum_wage_index(minimum_wage, policy_series, pre_year)
    floor_post = _minimum_wage_index(minimum_wage, policy_series, post_year)
    if pd.isna(floor_pre) or pd.isna(floor_post):
        return pd.NA
    return round(float(floor_post) - float(floor_pre), 4)


def compute_minimum_wage_event_study(
    real_age: pd.DataFrame,
    minimum_wage: pd.DataFrame,
    *,
    treated_age_group: str = "18-21",
    comparison_age_group: str = "22-29",
    pre_year: int = 2023,
    post_year: int = 2025,
    policy_series: str = "18 to 20",
    adult_policy_series: str = "adult threshold",
) -> pd.DataFrame:
    data = _ashe_series(real_age)
    treated_pre = _index_at(data, treated_age_group, pre_year)
    treated_post = _index_at(data, treated_age_group, post_year)
    comparison_pre = _index_at(data, comparison_age_group, pre_year)
    comparison_post = _index_at(data, comparison_age_group, post_year)
    treated_change = treated_post - treated_pre
    comparison_change = comparison_post - comparison_pre
    floor_change_18_to_20 = _minimum_wage_change(
        minimum_wage, policy_series, pre_year, post_year
    )
    adult_floor_change = _minimum_wage_change(
        minimum_wage, adult_policy_series, pre_year, post_year
    )
    return pd.DataFrame(
        [
            {
                "treated_age_group": treated_age_group,
                "comparison_age_group": comparison_age_group,
                "policy_series_18_to_20": policy_series,
                "policy_series_adult_threshold": adult_policy_series,
                "pre_year": pre_year,
                "post_year": post_year,
                "treated_change_pp": round(treated_change, 4),
                "comparison_change_pp": round(comparison_change, 4),
                "descriptive_did_pp": round(treated_change - comparison_change, 4),
                "wage_floor_18_to_20_change_pp": floor_change_18_to_20,
                "wage_floor_adult_threshold_change_pp": adult_floor_change,
                "threshold_context": (
                    "Mixed threshold context: ASHE 18-21 includes 18-20 workers and "
                    "21-year-olds; the adult threshold applies to 21-year-olds from "
                    "2024 onward."
                ),
                "caveat": (
                    "Descriptive difference-in-differences framing only; not causal because "
                    "ASHE age bands, policy thresholds, hours, and composition do not cleanly identify treatment."
                ),
            }
        ]
    )


def forecast_ashe_real_earnings(
    real_age: pd.DataFrame,
    *,
    horizon: int = 2,
) -> pd.DataFrame:
    data = _ashe_series(real_age)
    rows: list[dict[str, object]] = []
    for age_group, group in data.groupby("age_group"):
        ordered = group.sort_values("year")
        if len(ordered) < 3:
            continue
        years = ordered["year"].astype(int).to_numpy()
        values = ordered["real_earnings_index_2019_100"].astype(float).to_numpy()
        x = years - years.min()
        slope, intercept = np.polyfit(x, values, 1)
        fitted = intercept + slope * x
        residuals = values - fitted
        residual_sd = float(np.sqrt(np.square(residuals).sum() / max(len(values) - 2, 1)))
        latest_year = int(years.max())
        for step in range(1, horizon + 1):
            forecast_year = latest_year + step
            x_future = forecast_year - years.min()
            point = float(intercept + slope * x_future)
            margin = 1.96 * residual_sd
            rows.append(
                {
                    "age_group": age_group,
                    "forecast_year": forecast_year,
                    "forecast_index": round(point, 2),
                    "rough_residual_band_lower": round(point - margin, 2),
                    "rough_residual_band_upper": round(point + margin, 2),
                    "model": "linear_trend_baseline",
                    "interval_note": "rough residual band",
                    "caveat": (
                        "Simple trend baseline for project framing; not an official forecast "
                        "and not a structural time-series model. The band is based only on "
                        "historical residual spread, not parameter uncertainty."
                    ),
                }
            )
    frame = pd.DataFrame(rows, columns=FORECAST_COLUMNS)
    if frame.empty:
        return frame
    return frame.sort_values(["age_group", "forecast_year"]).reset_index(drop=True)


def write_option_b_report(
    structural_breaks: pd.DataFrame,
    event_study: pd.DataFrame,
    forecast: pd.DataFrame,
    *,
    output_root: str | Path = OUTPUT_ROOT,
) -> Path:
    evidence = ensure_dir(Path(output_root) / "evidence")
    lines = [
        "# Option B Modelling Diagnostics",
        "",
        "This report adds a small modelling layer on top of the descriptive ASHE/RTI pipeline. It keeps the same source boundaries and treats the results as diagnostics, not as causal proof.",
        "",
        "## Structural-Break Relative-Weight Screen",
        "",
    ]
    if structural_breaks.empty:
        lines.append("No structural-break candidates were available.")
    else:
        for age_group, group in structural_breaks.groupby("age_group"):
            top = group.sort_values("relative_weight", ascending=False).iloc[0]
            lines.append(
                f"- {age_group}: highest relative-weight break year {int(top['break_year'])} "
                f"with relative weight {float(top['relative_weight']):.1%}; "
                f"estimated level shift {float(top['level_shift_pp']):.2f} index points."
            )
        lines.append(
            "- Boundary: weights are conditional on one two-mean break with at least two years "
            "on each side; they are not no-break posterior probabilities."
        )
    lines.extend(["", "## Minimum-Wage Event Framing", ""])
    if event_study.empty:
        lines.append("No minimum-wage event-study row was available.")
    else:
        row = event_study.iloc[0]
        lines.append(
            f"- {row['treated_age_group']} versus {row['comparison_age_group']}, "
            f"{int(row['pre_year'])}-{int(row['post_year'])}: descriptive DID "
            f"{float(row['descriptive_did_pp']):.2f} index points."
        )
        floor_bits = []
        if not pd.isna(row["wage_floor_18_to_20_change_pp"]):
            floor_bits.append(
                f"18 to 20 floor {float(row['wage_floor_18_to_20_change_pp']):.2f}pp"
            )
        if not pd.isna(row["wage_floor_adult_threshold_change_pp"]):
            floor_bits.append(
                "adult-threshold floor "
                f"{float(row['wage_floor_adult_threshold_change_pp']):.2f}pp"
            )
        if floor_bits:
            lines.append(f"- Wage-floor context: {'; '.join(floor_bits)}.")
        lines.append(f"- Threshold context: {row['threshold_context']}")
        lines.append(f"- Caveat: {row['caveat']}")
    lines.extend(["", "## Forecast Baseline", ""])
    if forecast.empty:
        lines.append("No forecast rows were available.")
    else:
        focus = forecast[forecast["age_group"].isin(["18-21", "22-29"])]
        focus = focus if not focus.empty else forecast
        for row in focus.sort_values(["age_group", "forecast_year"]).itertuples(index=False):
            lines.append(
                f"- {row.age_group} {int(row.forecast_year)}: forecast index "
                f"{float(row.forecast_index):.2f} "
                f"(rough residual band {float(row.rough_residual_band_lower):.2f} "
                f"to {float(row.rough_residual_band_upper):.2f})."
            )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "These outputs are modelling diagnostics and decision-support framing. They do not convert the descriptive project into a causal estimate, and they do not replace ASHE as the main annual age-specific wage source.",
        ]
    )
    path = evidence / "option_b_ds_report.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_option_b_notebook(*, notebook_root: str | Path = NOTEBOOK_ROOT) -> Path:
    notebook_root = ensure_dir(notebook_root)
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# Option B Modelling Walkthrough\n",
                    "\n",
                    "Rebuild the pipeline, then inspect structural-break, event-study, and forecast outputs.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import pandas as pd\n",
                    "from pathlib import Path\n",
                    "ROOT = Path('..').resolve()\n",
                    "tables = ROOT / 'outputs' / 'tables'\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "pd.read_csv(tables / 'structural_break_weights.csv').head()\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "pd.read_csv(tables / 'minimum_wage_event_study.csv')\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "pd.read_csv(tables / 'ashe_forecast_baseline.csv').head()\n",
                ],
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path = notebook_root / "option_b_walkthrough.ipynb"
    path.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")
    return path


def build_option_b_outputs(
    *,
    processed_root: str | Path = PROCESSED_ROOT,
    output_root: str | Path = OUTPUT_ROOT,
    notebook_root: str | Path = NOTEBOOK_ROOT,
) -> dict[str, Path]:
    processed_root = Path(processed_root)
    output_root = Path(output_root)
    tables = ensure_dir(output_root / "tables")
    real_age = pd.read_parquet(processed_root / "age_group_real_earnings.parquet")
    minimum_wage_path = output_root / "tables" / "minimum_wage_real_rates.csv"
    minimum_wage = pd.read_csv(minimum_wage_path) if minimum_wage_path.exists() else pd.DataFrame()
    structural_breaks = compute_structural_break_weights(real_age)
    event_study = compute_minimum_wage_event_study(real_age, minimum_wage)
    forecast = forecast_ashe_real_earnings(real_age)
    structural_path = tables / "structural_break_weights.csv"
    event_path = tables / "minimum_wage_event_study.csv"
    forecast_path = tables / "ashe_forecast_baseline.csv"
    write_dataframe(structural_breaks, structural_path)
    write_dataframe(event_study, event_path)
    write_dataframe(forecast, forecast_path)
    report_path = write_option_b_report(
        structural_breaks,
        event_study,
        forecast,
        output_root=output_root,
    )
    notebook_path = write_option_b_notebook(notebook_root=notebook_root)
    return {
        "structural_breaks": structural_path,
        "event_study": event_path,
        "forecast": forecast_path,
        "report": report_path,
        "notebook": notebook_path,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build Option B data-science upgrade outputs.")
    parser.parse_args(argv)
    outputs = build_option_b_outputs()
    print(outputs["report"])
    print(outputs["notebook"])


if __name__ == "__main__":
    main()
