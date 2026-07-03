from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pipeline_workflow_rebuilds_and_uploads_release_evidence() -> None:
    workflow = PROJECT_ROOT / ".github" / "workflows" / "pipeline-evidence.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" in text
    assert "python -m uk_wages.pipeline --all --locked" in text
    assert "actions/upload-artifact@v4" in text
    assert "releases/v1/evidence" in text
    assert "requirements.lock" in text


def test_makefile_exposes_release_evidence_target() -> None:
    text = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert ".PHONY:" in text and "release-evidence" in text
    assert "release-evidence:" in text
    assert "$(PYTHON) -m uk_wages.release_package" in text


def test_pipeline_module_exposes_locked_full_pipeline_command() -> None:
    source = (PROJECT_ROOT / "src" / "uk_wages" / "pipeline.py").read_text(encoding="utf-8")

    assert "--all" in source
    assert "--locked" in source
    assert "requirements.lock" in source
    assert "uk_wages.release_package" in source


def test_requirements_lock_uses_exact_pins() -> None:
    lockfile = PROJECT_ROOT / "requirements.lock"
    lines = [
        line.strip()
        for line in lockfile.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    assert "pandas==3.0.3" in lines
    assert "pytest==9.1.1" in lines
    assert all("==" in line or line.startswith("-") for line in lines)
