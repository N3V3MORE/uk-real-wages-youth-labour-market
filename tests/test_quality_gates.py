from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_defines_lint_type_and_coverage_gates() -> None:
    text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.ruff]" in text
    assert "[tool.mypy]" in text
    assert "[tool.coverage.run]" in text
    assert 'source = ["uk_wages"]' in text
    assert "fail_under = 55" in text


def test_ci_runs_lint_typecheck_and_coverage_commands() -> None:
    text = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "python -m ruff check" in text
    assert "python -m mypy src" in text
    assert "python -m pytest --cov=uk_wages" in text
    assert "--cov=uk_wages" in text
    assert "--cov-fail-under=55" in text


def test_quality_dependencies_are_pinned() -> None:
    requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")
    lock = (PROJECT_ROOT / "requirements.lock").read_text(encoding="utf-8")

    for dependency in ["pytest-cov", "ruff", "mypy"]:
        assert dependency in requirements
        assert f"{dependency}==" in lock
