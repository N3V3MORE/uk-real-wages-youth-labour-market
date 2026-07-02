from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from uk_wages.experiment_runner import run_experiment
from uk_wages.experiment_schema import ExperimentSpec, validate_experiment
from uk_wages.robustness import build_contrarian_report, compute_fragility_scores, sign_flipped
from uk_wages.utils import sha256_file


def _write_toy_processed(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for year in [2019, 2020, 2021]:
        for age_group, base in [("18-21", 100.0), ("25-34", 150.0), ("30-39", 200.0)]:
            nominal = base * {2019: 1.0, 2020: 1.1, 2021: 1.18}[year]
            rows.append(
                {
                    "year": year,
                    "age_group": age_group,
                    "sex": "All",
                    "work_status": "All",
                    "earnings_measure": "median_weekly_gross",
                    "nominal_earnings": nominal,
                    "unit": "GBP per week",
                    "source_file": "toy.xlsx",
                    "source_release": "toy",
                }
            )
            rows.append(
                {
                    "year": year,
                    "age_group": age_group,
                    "sex": "All",
                    "work_status": "Full-Time",
                    "earnings_measure": "median_weekly_gross",
                    "nominal_earnings": nominal * 1.2,
                    "unit": "GBP per week",
                    "source_file": "toy.xlsx",
                    "source_release": "toy",
                }
            )
            rows.append(
                {
                    "year": year,
                    "age_group": age_group,
                    "sex": "All",
                    "work_status": "All",
                    "earnings_measure": "mean_weekly_gross",
                    "nominal_earnings": nominal * 1.1,
                    "unit": "GBP per week",
                    "source_file": "toy.xlsx",
                    "source_release": "toy",
                }
            )
    pd.DataFrame(rows).to_parquet(root / "ashe_age_annual.parquet", index=False)
    pd.DataFrame(
        {
            "year": [2019, 2020, 2021],
            "cpih_april_index": [100.0, 104.0, 120.0],
            "cpi_april_index": [100.0, 106.0, 122.0],
            "cpih_calendar_year_avg": [100.0, 105.0, 118.0],
            "cpi_calendar_year_avg": [100.0, 107.0, 121.0],
        }
    ).to_parquet(root / "inflation_annual.parquet", index=False)
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2019-01-01", "2020-01-01", "2021-01-01"]),
            "sector": ["Whole Economy", "Whole Economy", "Whole Economy"],
            "real_regular_pay_index_jan2019_100": [100.0, 101.0, 103.0],
            "real_total_pay_index_jan2019_100": [100.0, 100.5, 102.0],
        }
    ).to_parquet(root / "awe_real_monthly.parquet", index=False)


def _baseline_spec() -> ExperimentSpec:
    return validate_experiment(
        {
            "experiment_name": "baseline",
            "description": "Toy baseline.",
            "assumptions": {
                "deflator": "cpih",
                "inflation_period": "april",
                "baseline_year": 2019,
                "wage_measure": "median_weekly",
                "work_status": "all",
                "sex": "all",
                "age_groups": ["18-21", "25-34", "30-39"],
            },
            "outputs": {"compare_to": None},
        }
    )


def test_experiment_yaml_validation_rejects_unsupported_values() -> None:
    base = {
        "experiment_name": "bad",
        "description": "bad",
        "assumptions": {
            "deflator": "rpi",
            "inflation_period": "april",
            "baseline_year": 2019,
            "wage_measure": "median_weekly",
            "work_status": "all",
            "sex": "all",
        },
    }
    with pytest.raises(ValueError, match="deflator"):
        validate_experiment(base)
    base["assumptions"]["deflator"] = "cpih"
    base["assumptions"]["baseline_year"] = 2018
    with pytest.raises(ValueError, match="baseline_year"):
        validate_experiment(base)
    base["assumptions"]["baseline_year"] = 2019
    base["assumptions"]["wage_measure"] = "hourly"
    with pytest.raises(ValueError, match="wage_measure"):
        validate_experiment(base)


def test_baseline_experiment_real_index_equals_100(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    output = tmp_path / "outputs"
    _write_toy_processed(processed)

    result = run_experiment(_baseline_spec(), processed_root=processed, output_root=output)

    baseline_rows = result.age_group_table[result.age_group_table["year"].eq(2019)]
    assert baseline_rows["real_earnings_index_since_baseline"].tolist() == [100.0, 100.0, 100.0]


def test_cpi_and_cpih_sensitivity_runs_produce_outputs(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    output = tmp_path / "outputs"
    _write_toy_processed(processed)
    run_experiment(_baseline_spec(), processed_root=processed, output_root=output)
    cpi_spec = validate_experiment(
        {
            "experiment_name": "sensitivity_cpi",
            "description": "Use CPI.",
            "assumptions": {
                "deflator": "cpi",
                "inflation_period": "april",
                "baseline_year": 2019,
                "wage_measure": "median_weekly",
                "work_status": "all",
                "sex": "all",
            },
            "outputs": {"compare_to": "baseline"},
        }
    )

    result = run_experiment(cpi_spec, processed_root=processed, output_root=output)

    assert (output / "experiments" / "sensitivity_cpi" / "age_group_real_earnings.csv").exists()
    assert (output / "experiments" / "sensitivity_cpi" / "summary.json").exists()
    assert not result.comparison_table.empty


def test_sign_flip_logic_on_toy_values() -> None:
    assert sign_flipped(-0.1, 0.2)
    assert sign_flipped(0.1, -0.2)
    assert not sign_flipped(0.0, 0.2)
    assert not sign_flipped(0.1, 0.2)


def test_fragility_score_logic_on_toy_matrix() -> None:
    matrix = pd.DataFrame(
        {
            "experiment_name": ["a", "b", "c", "d"],
            "age_group": ["18-21", "18-21", "18-21", "18-21"],
            "sign_flip_vs_baseline": [False, True, False, True],
            "supports_main_claim": [True, False, True, False],
        }
    )

    scores = compute_fragility_scores(matrix)

    assert scores.loc[0, "fragility_score"] == 0.5
    assert scores.loc[0, "assessment"] == "not robust"


def test_contrarian_report_is_created(tmp_path: Path) -> None:
    matrix = pd.DataFrame(
        {
            "experiment_name": ["baseline", "shift_2020"],
            "age_group": ["18-21", "18-21"],
            "real_pct_change": [-1.0, 2.0],
            "baseline_real_pct_change": [-1.0, -1.0],
            "difference_from_baseline": [0.0, 3.0],
            "sign_flip_vs_baseline": [False, True],
            "supports_main_claim": [True, False],
            "notes": ["", float("nan")],
        }
    )

    output = build_contrarian_report(matrix, tmp_path)

    assert output.exists()
    assert "shift_2020" in output.read_text(encoding="utf-8")
    assert "Magnitude changes materially" in output.read_text(encoding="utf-8")


def test_experiment_runner_does_not_modify_processed_sources(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    output = tmp_path / "outputs"
    _write_toy_processed(processed)
    before = {path.name: sha256_file(path) for path in processed.glob("*.parquet")}

    run_experiment(_baseline_spec(), processed_root=processed, output_root=output)

    after = {path.name: sha256_file(path) for path in processed.glob("*.parquet")}
    assert after == before
