from __future__ import annotations

import subprocess
import sys

from uk_wages.pipeline import PIPELINE_MODULES, run_modules


def test_pipeline_all_matches_makefile_order() -> None:
    assert PIPELINE_MODULES == [
        "uk_wages.download",
        "uk_wages.clean_cpi",
        "uk_wages.clean_ashe",
        "uk_wages.clean_region_ashe",
        "uk_wages.clean_a05",
        "uk_wages.clean_earn01",
        "uk_wages.clean_rti",
        "uk_wages.ashe_decomposition",
        "uk_wages.ashe_quality",
        "uk_wages.ashe_composition",
        "uk_wages.minimum_wage",
        "uk_wages.analysis",
        "uk_wages.rti_analysis",
        "uk_wages.charts",
        "uk_wages.rti_triangulation",
        "uk_wages.robustness --run-all",
        "uk_wages.source_validation",
        "uk_wages.triangulation",
        "uk_wages.option_b",
        "uk_wages.final_claims",
        "uk_wages.research_note",
        "uk_wages.claim_confidence",
        "uk_wages.robustness --contrarian",
        "uk_wages.lineage",
        "uk_wages.evidence --build-report",
        "pytest",
    ]


def test_pipeline_runner_stops_on_subprocess_error() -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess:
        calls.append(command)
        if command[-1] == "uk_wages.clean_cpi":
            raise subprocess.CalledProcessError(returncode=2, cmd=command)
        return subprocess.CompletedProcess(command, 0)

    try:
        run_modules(["uk_wages.download", "uk_wages.clean_cpi", "uk_wages.clean_ashe"], runner=fake_run)
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError("run_modules should stop when a step fails")

    assert calls == [
        [sys.executable, "-m", "uk_wages.download"],
        [sys.executable, "-m", "uk_wages.clean_cpi"],
    ]
