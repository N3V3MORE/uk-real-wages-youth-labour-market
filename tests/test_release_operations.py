from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _target_prerequisites(makefile_text: str, target: str) -> list[str]:
    match = re.search(rf"(?m)^{re.escape(target)}:\s*(?P<prerequisites>[^\n]*)$", makefile_text)
    assert match is not None, f"Missing Makefile target: {target}"
    return match.group("prerequisites").split()


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


def test_full_pipeline_is_the_only_pipeline_workflow_and_publishes_v2_evidence() -> None:
    pipeline_workflows = sorted(path.name for path in WORKFLOWS.glob("*pipeline*.yml"))
    assert pipeline_workflows == ["full_pipeline.yml"]

    workflow = (WORKFLOWS / "full_pipeline.yml").read_text(encoding="utf-8")
    required_fragments = [
        "schedule:",
        "workflow_dispatch:",
        'python-version: "3.12"',
        "python -m pip install -r requirements.txt -c requirements.lock",
        "python -m pip install --no-build-isolation --no-deps -e .",
        "python -m uk_wages.pipeline --all --locked",
        "actions/upload-artifact@v4",
        "releases/v2/evidence",
        "if-no-files-found: error",
    ]
    for fragment in required_fragments:
        assert fragment in workflow


def test_public_metadata_identifies_the_v2_official_source_release() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    assert project["version"] == "2.0.0"
    assert project["description"] == (
        "Reproducible analysis of UK real wages and youth labour market stress "
        "using official UK public sources since 2019."
    )
