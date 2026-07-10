from __future__ import annotations

import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_ci_uses_python_312_constraints_and_all_quality_commands() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert 'python-version: "3.12"' in workflow
    assert "python -m pip install -r requirements.txt -c requirements.lock" in workflow
    assert "python -m ruff check" in workflow
    assert "python -m mypy src" in workflow
    assert (
        "python -m pytest --cov=uk_wages --cov-report=term-missing "
        "--cov-fail-under=55"
    ) in workflow


def test_pyproject_configures_ruff_mypy_and_branch_coverage() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)["tool"]

    assert {"E9", "F"} <= set(config["ruff"]["lint"]["select"])
    assert config["mypy"]["python_version"] == "3.12"
    assert config["mypy"]["check_untyped_defs"] is True
    assert config["coverage"]["run"]["branch"] is True
    assert config["coverage"]["report"]["fail_under"] == 55


def test_quality_dependencies_are_declared_and_exactly_constrained() -> None:
    requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    lock = (PROJECT_ROOT / "requirements.lock").read_text(encoding="utf-8").lower()

    required = {
        "coverage[toml]",
        "mypy",
        "pandas-stubs",
        "pytest",
        "pytest-cov",
        "ruff",
        "types-pyyaml",
        "types-requests",
    }
    for dependency in required:
        assert dependency in requirements
        lock_name = dependency.removesuffix("[toml]")
        assert f"{lock_name}==" in lock

    assert "python -m pip install -r requirements.txt -c requirements.lock" in lock
