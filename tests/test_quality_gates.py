from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml
from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT_LINE = re.compile(
    r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(?:\[[^\]]+\])?\s*(?P<specifier>(?:===|==|~=|!=|<=|>=|<|>).+)$"
)
REQUIRED_CI_STEP_NAMES = ("Install", "Lint", "Type check", "Tests with coverage")


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


def _required_ci_steps(steps: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    required: dict[str, dict[str, object]] = {}
    positions: list[int] = []
    for name in REQUIRED_CI_STEP_NAMES:
        matches = [(index, step) for index, step in enumerate(steps) if step.get("name") == name]
        assert len(matches) == 1
        index, step = matches[0]
        assert "if" not in step
        continue_on_error = step.get("continue-on-error")
        assert continue_on_error is None or continue_on_error is False
        required[name] = step
        positions.append(index)
    assert positions == sorted(positions)
    return required


def _is_concrete_pin(specifier: str) -> bool:
    if not specifier.startswith("=="):
        return False
    version = specifier[2:]
    try:
        Version(version)
    except InvalidVersion:
        return False
    return "*" not in version


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
    assert not _is_concrete_pin("==1..2")
    assert not _is_concrete_pin("==1foo")
    assert not _is_concrete_pin("==1---2")
    assert not _is_concrete_pin(">=1.2.3")
    assert not _is_concrete_pin("==1.2.3,==1.2.4")
    assert not _is_concrete_pin("==1.2.3; python_version >= '3.12'")
    assert not _is_concrete_pin("==")


@pytest.mark.parametrize("unsafe_setting", ["if: false", "continue-on-error: true"])
def test_required_ci_steps_reject_disabled_or_nonblocking_steps(
    unsafe_setting: str,
) -> None:
    workflow = f"""
    jobs:
      tests:
        steps:
          - name: Install
            {unsafe_setting}
            run: python -m pip install -r requirements.txt -c requirements.lock
          - name: Lint
            run: python -m ruff check
          - name: Type check
            run: python -m mypy src
          - name: Tests with coverage
            run: python -m pytest --cov=uk_wages
    """

    with pytest.raises(AssertionError):
        _required_ci_steps(_ci_job_steps(workflow))


def test_required_ci_steps_reject_duplicate_names() -> None:
    workflow = """
    jobs:
      tests:
        steps:
          - name: Install
            run: python -m pip install -r requirements.txt -c requirements.lock
          - name: Install
            run: python -m pip install --no-build-isolation --no-deps -e .
          - name: Lint
            run: python -m ruff check
          - name: Type check
            run: python -m mypy src
          - name: Tests with coverage
            run: python -m pytest --cov=uk_wages
    """

    with pytest.raises(AssertionError):
        _required_ci_steps(_ci_job_steps(workflow))


def test_required_ci_steps_allow_harmless_extra_steps() -> None:
    workflow = """
    jobs:
      tests:
        steps:
          - name: Prepare cache
            run: python -V
          - name: Install
            run: python -m pip install -r requirements.txt -c requirements.lock
          - name: Report environment
            run: python -m pip list
          - name: Lint
            run: python -m ruff check
          - name: Type check
            run: python -m mypy src
          - name: Tests with coverage
            run: python -m pytest --cov=uk_wages
          - name: Summarize
            run: python -V
    """

    required = _required_ci_steps(_ci_job_steps(workflow))

    assert list(required) == ["Install", "Lint", "Type check", "Tests with coverage"]


def test_ci_uses_python_312_constraints_and_all_quality_commands() -> None:
    steps = _ci_job_steps(
        (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
    )

    required = _required_ci_steps(steps)
    checkout_matches = [
        (index, step)
        for index, step in enumerate(steps)
        if step.get("uses") == "actions/checkout@v6"
    ]
    setup_matches = [
        (index, step)
        for index, step in enumerate(steps)
        if step.get("uses") == "actions/setup-python@v6"
    ]
    assert len(checkout_matches) == 1
    assert len(setup_matches) == 1
    checkout_index, _ = checkout_matches[0]
    setup_index, setup_step = setup_matches[0]
    install_index = next(
        index for index, step in enumerate(steps) if step is required["Install"]
    )
    assert checkout_index < setup_index < install_index
    setup_options = setup_step.get("with")
    assert isinstance(setup_options, dict)
    assert setup_options.get("python-version") == "3.12"
    assert _step_run_lines(required["Install"]) == [
        "python -m pip install -r requirements.txt -c requirements.lock",
        "python -m pip install --no-build-isolation --no-deps -e .",
    ]
    assert _step_run_lines(required["Lint"]) == ["python -m ruff check"]
    assert _step_run_lines(required["Type check"]) == ["python -m mypy src"]
    assert _step_run_lines(required["Tests with coverage"]) == [
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
        "packaging",
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


def test_linux_terminal_dependencies_are_explicit_and_locked() -> None:
    requirement_lines = [
        line.strip()
        for line in (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    parsed = {Requirement(line).name.lower(): Requirement(line) for line in requirement_lines}
    lock = _parse_requirement_lines(
        (PROJECT_ROOT / "requirements.lock").read_text(encoding="utf-8")
    )

    posix_dependency = parsed["ptyprocess"]
    ipython_posix_dependency = parsed["pexpect"]
    windows_dependency = parsed["pywinpty"]
    assert posix_dependency.marker is not None
    assert posix_dependency.marker.evaluate({"os_name": "posix"})
    assert not posix_dependency.marker.evaluate({"os_name": "nt"})
    assert ipython_posix_dependency.marker is not None
    assert ipython_posix_dependency.marker.evaluate({"sys_platform": "linux"})
    assert not ipython_posix_dependency.marker.evaluate({"sys_platform": "win32"})
    assert not ipython_posix_dependency.marker.evaluate({"sys_platform": "emscripten"})
    assert windows_dependency.marker is not None
    assert windows_dependency.marker.evaluate({"os_name": "nt"})
    assert not windows_dependency.marker.evaluate({"os_name": "posix"})
    assert lock["pexpect"] == "==4.9.0"
    assert lock["ptyprocess"] == "==0.7.0"
    assert _is_concrete_pin(lock["pywinpty"])
