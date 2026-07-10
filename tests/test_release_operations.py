from __future__ import annotations

import copy
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
LOCKED_PIPELINE_COMMAND = "python -m uk_wages.pipeline --all --locked"


def _target_prerequisites(makefile_text: str, target: str) -> list[str]:
    match = re.search(rf"(?m)^{re.escape(target)}:\s*(?P<prerequisites>[^\n]*)$", makefile_text)
    assert match is not None, f"Missing Makefile target: {target}"
    return match.group("prerequisites").split()


def _load_workflow(text: str) -> dict[str, Any]:
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert isinstance(workflow, dict)
    return workflow


def _run_lines(step: dict[str, Any]) -> list[str]:
    run = step.get("run")
    if not isinstance(run, str):
        return []
    return [
        line.strip()
        for line in run.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _assert_blocking(item: dict[str, Any]) -> None:
    assert "if" not in item
    continue_on_error = str(item.get("continue-on-error", "false")).strip().lower()
    assert continue_on_error in {"", "false", "no", "off", "0"}


def _one_step(
    steps: list[dict[str, Any]],
    *,
    name: str | None = None,
    uses: str | None = None,
) -> tuple[int, dict[str, Any]]:
    matches = [
        (index, step)
        for index, step in enumerate(steps)
        if (name is None or step.get("name") == name)
        and (uses is None or step.get("uses") == uses)
    ]
    assert len(matches) == 1
    return matches[0]


def _assert_full_pipeline_contract(workflow: dict[str, Any]) -> None:
    triggers = workflow.get("on")
    assert isinstance(triggers, dict)
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert triggers["workflow_dispatch"] in {"", None}
    assert triggers["schedule"] == [{"cron": "0 6 * * 1"}]

    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    assert len(jobs) == 1
    job = next(iter(jobs.values()))
    assert isinstance(job, dict)
    _assert_blocking(job)

    steps = job.get("steps")
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) for step in steps)
    for step in steps:
        _assert_blocking(step)

    checkout_index, _ = _one_step(steps, uses="actions/checkout@v4")
    setup_index, setup = _one_step(steps, uses="actions/setup-python@v5")
    install_index, install = _one_step(steps, name="Install")
    rebuild_index, rebuild = _one_step(
        steps,
        name="Rebuild locked pipeline and package evidence",
    )
    upload_index, upload = _one_step(steps, uses="actions/upload-artifact@v4")
    assert [checkout_index, setup_index, install_index, rebuild_index, upload_index] == sorted(
        [checkout_index, setup_index, install_index, rebuild_index, upload_index]
    )

    setup_options = setup.get("with")
    assert isinstance(setup_options, dict)
    assert setup_options.get("python-version") == "3.12"
    assert _run_lines(install) == [
        "python -m pip install -r requirements.txt -c requirements.lock",
        "python -m pip install --no-build-isolation --no-deps -e .",
    ]
    assert _run_lines(rebuild) == [LOCKED_PIPELINE_COMMAND]
    upload_options = upload.get("with")
    assert isinstance(upload_options, dict)
    assert upload_options.get("path") == "releases/v2/evidence"
    assert upload_options.get("if-no-files-found") == "error"


def _current_workflow_text() -> str:
    return (WORKFLOWS / "full_pipeline.yml").read_text(encoding="utf-8")


def test_makefile_exposes_quality_release_and_complete_all_targets() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert _target_prerequisites(makefile, "quality") == ["lint", "typecheck", "coverage"]
    assert "$(PYTHON) -m uk_wages.release_package" in makefile
    assert _target_prerequisites(makefile, "all") == [
        "data",
        "clean",
        "analysis",
        "charts",
        "evidence",
        "test",
        "release-evidence",
    ]


def test_full_pipeline_is_the_only_structurally_valid_pipeline_workflow() -> None:
    pipeline_workflows = sorted(
        path.name
        for path in WORKFLOWS.iterdir()
        if path.suffix.lower() in {".yml", ".yaml"} and "pipeline" in path.stem.lower()
    )
    assert pipeline_workflows == ["full_pipeline.yml"]

    _assert_full_pipeline_contract(_load_workflow(_current_workflow_text()))


def test_commented_locked_command_cannot_mask_an_unlocked_pipeline() -> None:
    mutated = _current_workflow_text().replace(
        f"run: {LOCKED_PIPELINE_COMMAND}",
        "run: python -m uk_wages.pipeline --all\n"
        f"        # run: {LOCKED_PIPELINE_COMMAND}",
    )

    with pytest.raises(AssertionError):
        _assert_full_pipeline_contract(_load_workflow(mutated))


@pytest.mark.parametrize("scope", ["job", "step"])
def test_disabled_job_or_step_fails_the_workflow_contract(scope: str) -> None:
    workflow = _load_workflow(_current_workflow_text())
    job = next(iter(workflow["jobs"].values()))
    if scope == "job":
        job["if"] = "false"
    else:
        job["steps"][3]["if"] = "false"

    with pytest.raises(AssertionError):
        _assert_full_pipeline_contract(workflow)


@pytest.mark.parametrize("scope", ["job", "step"])
def test_nonblocking_job_or_step_fails_the_workflow_contract(scope: str) -> None:
    workflow = copy.deepcopy(_load_workflow(_current_workflow_text()))
    job = next(iter(workflow["jobs"].values()))
    if scope == "job":
        job["continue-on-error"] = "true"
    else:
        job["steps"][3]["continue-on-error"] = "true"

    with pytest.raises(AssertionError):
        _assert_full_pipeline_contract(workflow)


def test_public_metadata_identifies_the_v2_official_source_release() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    assert project["version"] == "2.0.0"
    assert project["description"] == (
        "Reproducible analysis of UK real wages and youth labour market stress "
        "using official UK public sources since 2019."
    )


def test_reviewer_guide_uses_current_locked_release_and_quality_commands() -> None:
    guide = (ROOT / "docs" / "reviewer_guide.md").read_text(encoding="utf-8")

    required = [
        "python -m pip install -r requirements.txt -c requirements.lock",
        "python -m pip install --no-build-isolation --no-deps -e .",
        "python -m ruff check",
        "python -m mypy src",
        "python -m pytest --cov=uk_wages --cov-report=term-missing --cov-fail-under=55",
        LOCKED_PIPELINE_COMMAND,
        "Full pipeline evidence",
        "releases/v2/evidence",
    ]
    assert all(fragment in guide for fragment in required)
    assert "Full pipeline smoke" not in guide
    assert "runs unit tests on push" not in guide
    assert re.search(r"python -m uk_wages\.pipeline --all(?! --locked)", guide) is None


def test_public_docs_disclose_mutable_current_alias_risk() -> None:
    for path in [ROOT / "README.md", ROOT / "docs/reviewer_guide.md"]:
        text = path.read_text(encoding="utf-8").lower()
        assert "/current/" in text, path
        assert "availability" in text, path
        assert "hash mismatch" in text, path
