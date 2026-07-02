from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .utils import load_yaml


ALLOWED_DEFLATORS = ["cpih", "cpi"]
ALLOWED_INFLATION_PERIODS = ["april", "calendar_year_average"]
ALLOWED_BASELINE_YEARS = [2019, 2020, 2021]
ALLOWED_WAGE_MEASURES = ["median_weekly", "mean_weekly", "annual"]
ALLOWED_WORK_STATUSES = ["all", "full_time"]
ALLOWED_SEXES = ["all", "male", "female"]
ALLOWED_AGE_GROUPS = ["16-17", "18-21", "22-29", "25-34", "30-39", "40-49", "50-59", "60+"]
ALLOWED_SPEC_TIERS = ["core", "stress"]


@dataclass(frozen=True)
class ExperimentAssumptions:
    deflator: str
    inflation_period: str
    baseline_year: int
    wage_measure: str
    work_status: str
    sex: str = "all"
    age_groups: list[str] = field(default_factory=list)
    include_years: list[int] | None = None
    exclude_years: list[int] = field(default_factory=list)
    end_year: int | None = None


@dataclass(frozen=True)
class ExperimentOutputs:
    compare_to: str | None = None
    metrics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExperimentSpec:
    experiment_name: str
    description: str
    spec_tier: str
    assumptions: ExperimentAssumptions
    outputs: ExperimentOutputs = field(default_factory=ExperimentOutputs)


def _require_allowed(name: str, value: Any, allowed: list[Any]) -> None:
    if value not in allowed:
        raise ValueError(f"Unsupported {name}: {value!r}. Allowed values: {allowed}")


def validate_experiment(payload: dict[str, Any]) -> ExperimentSpec:
    if not isinstance(payload, dict):
        raise ValueError("Experiment spec must be a mapping.")
    name = str(payload.get("experiment_name", "")).strip()
    if not name:
        raise ValueError("experiment_name is required.")
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("experiment_name must contain only letters, numbers, dashes, or underscores.")
    description = str(payload.get("description", "")).strip()
    if not description:
        raise ValueError("description is required.")
    spec_tier = str(payload.get("spec_tier", "core")).lower()
    _require_allowed("spec_tier", spec_tier, ALLOWED_SPEC_TIERS)

    raw_assumptions = payload.get("assumptions")
    if not isinstance(raw_assumptions, dict):
        raise ValueError("assumptions must be a mapping.")

    assumptions = ExperimentAssumptions(
        deflator=str(raw_assumptions.get("deflator", "")).lower(),
        inflation_period=str(raw_assumptions.get("inflation_period", "")).lower(),
        baseline_year=int(raw_assumptions.get("baseline_year", 0)),
        wage_measure=str(raw_assumptions.get("wage_measure", "")).lower(),
        work_status=str(raw_assumptions.get("work_status", "")).lower(),
        sex=str(raw_assumptions.get("sex", "all")).lower(),
        age_groups=list(raw_assumptions.get("age_groups") or []),
        include_years=(
            [int(year) for year in raw_assumptions["include_years"]]
            if raw_assumptions.get("include_years") is not None
            else None
        ),
        exclude_years=[int(year) for year in raw_assumptions.get("exclude_years", [])],
        end_year=(
            int(raw_assumptions["end_year"]) if raw_assumptions.get("end_year") is not None else None
        ),
    )

    _require_allowed("deflator", assumptions.deflator, ALLOWED_DEFLATORS)
    _require_allowed("inflation_period", assumptions.inflation_period, ALLOWED_INFLATION_PERIODS)
    _require_allowed("baseline_year", assumptions.baseline_year, ALLOWED_BASELINE_YEARS)
    _require_allowed("wage_measure", assumptions.wage_measure, ALLOWED_WAGE_MEASURES)
    _require_allowed("work_status", assumptions.work_status, ALLOWED_WORK_STATUSES)
    _require_allowed("sex", assumptions.sex, ALLOWED_SEXES)
    for age_group in assumptions.age_groups:
        _require_allowed("age_group", age_group, ALLOWED_AGE_GROUPS)
    if assumptions.include_years is not None and assumptions.baseline_year not in assumptions.include_years:
        raise ValueError("include_years must contain baseline_year.")
    if assumptions.baseline_year in assumptions.exclude_years:
        raise ValueError("exclude_years cannot remove baseline_year.")
    if assumptions.end_year is not None and assumptions.end_year < assumptions.baseline_year:
        raise ValueError("end_year cannot be earlier than baseline_year.")

    raw_outputs = payload.get("outputs") or {}
    if not isinstance(raw_outputs, dict):
        raise ValueError("outputs must be a mapping.")
    outputs = ExperimentOutputs(
        compare_to=raw_outputs.get("compare_to"),
        metrics=list(raw_outputs.get("metrics") or []),
    )
    return ExperimentSpec(name, description, spec_tier, assumptions, outputs)


def load_experiment(path: str | Path) -> ExperimentSpec:
    return validate_experiment(load_yaml(path))
