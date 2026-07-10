from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT_LINE = re.compile(
    r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(?:\[[^\]]+\])?\s*(?P<specifier>(?:===|==|~=|!=|<=|>=|<|>).+)$"
)
CONCRETE_PIN = re.compile(r"^==\d(?:[A-Za-z0-9.!+_-]*[A-Za-z0-9])?$")


def _parse_requirement_lines(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.partition("#")[0].strip()
        if not line:
            continue
        match = REQUIREMENT_LINE.fullmatch(line)
        if match is None:
            continue
        name = re.sub(r"[-_.]+", "-", match.group("name")).lower()
        parsed[name] = match.group("specifier").replace(" ", "")
    return parsed


def _ci_job_steps(text: str) -> list[dict[str, object]]:
    workflow = yaml.safe_load(text)
    assert isinstance(workflow, dict)
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    tests_job = jobs.get("tests")
    assert isinstance(tests_job, dict)
    steps = tests_job.get("steps")
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) for step in steps)
    return steps


def _step_run_lines(step: dict[str, object]) -> list[str]:
    run = step.get("run")
    if not isinstance(run, str):
        return []
    return [
        line.strip()
        for line in run.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _is_concrete_pin(specifier: str) -> bool:
    return CONCRETE_PIN.fullmatch(specifier) is not None


def test_requirement_parser_rejects_prefix_and_comment_false_positives() -> None:
    parsed = _parse_requirement_lines(
        """
        # pytest==9.1.1
        pytest-cov==7.1.0
        mypy-helper==1.0  # mypy==2.1.0
        coverage[toml]>=7.10
        """
    )

    assert "pytest" not in parsed
    assert "mypy" not in parsed
    assert parsed["pytest-cov"] == "==7.1.0"
    assert parsed["coverage"] == ">=7.10"


def test_ci_run_line_parser_ignores_commented_commands() -> None:
    workflow = """
    jobs:
      tests:
        steps:
          - name: Lint
            run: |
              # python -m mypy src
              python -m ruff check
    """

    steps = _ci_job_steps(workflow)

    assert _step_run_lines(steps[0]) == ["python -m ruff check"]


def test_concrete_lock_pin_rejects_wildcards_ranges_and_multiple_versions() -> None:
    assert _is_concrete_pin("==1.2.3")
    assert _is_concrete_pin("==2.9.0.post0")
    assert not _is_concrete_pin("==1.*")
    assert not _is_concrete_pin(">=1.2.3")
    assert not _is_concrete_pin("==1.2.3,==1.2.4")
    assert not _is_concrete_pin("==")


def test_ci_uses_python_312_constraints_and_all_quality_commands() -> None:
    steps = _ci_job_steps(
        (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
    )

    assert [step.get("uses") or step.get("name") for step in steps] == [
        "actions/checkout@v4",
        "actions/setup-python@v5",
        "Install",
        "Lint",
        "Type check",
        "Tests with coverage",
    ]
    setup_options = steps[1].get("with")
    assert isinstance(setup_options, dict)
    assert setup_options.get("python-version") == "3.12"
    assert _step_run_lines(steps[2]) == [
        "python -m pip install -r requirements.txt -c requirements.lock",
        "python -m pip install --no-build-isolation --no-deps -e .",
    ]
    assert _step_run_lines(steps[3]) == ["python -m ruff check"]
    assert _step_run_lines(steps[4]) == ["python -m mypy src"]
    assert _step_run_lines(steps[5]) == [
        "python -m pytest --cov=uk_wages --cov-report=term-missing --cov-fail-under=55"
    ]


def test_pyproject_configures_ruff_mypy_and_branch_coverage() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)["tool"]

    assert {"E9", "F"} <= set(config["ruff"]["lint"]["select"])
    assert config["mypy"]["python_version"] == "3.12"
    assert config["mypy"]["check_untyped_defs"] is True
    assert config["coverage"]["run"]["branch"] is True
    assert config["coverage"]["report"]["fail_under"] == 55


def test_quality_dependencies_are_declared_and_exactly_constrained() -> None:
    requirements = _parse_requirement_lines(
        (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")
    )
    lock = _parse_requirement_lines(
        (PROJECT_ROOT / "requirements.lock").read_text(encoding="utf-8")
    )

    required = {
        "coverage",
        "mypy",
        "pandas-stubs",
        "pytest",
        "pytest-cov",
        "ruff",
        "setuptools",
        "types-pyyaml",
        "types-requests",
        "wheel",
    }
    for dependency in required:
        assert dependency in requirements
        assert _is_concrete_pin(lock.get(dependency, ""))

    lock_text = (PROJECT_ROOT / "requirements.lock").read_text(encoding="utf-8")
    assert "python -m pip install -r requirements.txt -c requirements.lock" in lock_text
