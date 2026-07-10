from __future__ import annotations

import re
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT_LINE = re.compile(
    r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(?:\[[^\]]+\])?\s*(?P<specifier>(?:===|==|~=|!=|<=|>=|<|>).+)$"
)


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


def test_ci_uses_python_312_constraints_and_all_quality_commands() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert 'python-version: "3.12"' in workflow
    constrained_install = "python -m pip install -r requirements.txt -c requirements.lock"
    editable_install = "python -m pip install --no-build-isolation --no-deps -e ."
    assert constrained_install in workflow
    assert editable_install in workflow
    assert workflow.index(constrained_install) < workflow.index(editable_install)
    assert "--upgrade pip" not in workflow.lower()
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
        assert re.fullmatch(r"==[^=,;\s]+", lock.get(dependency, ""))

    lock_text = (PROJECT_ROOT / "requirements.lock").read_text(encoding="utf-8")
    assert "python -m pip install -r requirements.txt -c requirements.lock" in lock_text
