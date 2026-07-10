from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from uk_wages import pipeline
from uk_wages.pipeline import PIPELINE_MODULES, run_modules


ROOT = Path(__file__).resolve().parents[1]


def _make_modules_for_target(makefile_text: str, target: str) -> list[str]:
    lines = makefile_text.splitlines()
    target_header = f"{target}:"
    try:
        start = next(index for index, line in enumerate(lines) if line.startswith(target_header))
    except StopIteration as exc:
        raise AssertionError(f"Missing Makefile target: {target}") from exc
    modules: list[str] = []
    for line in lines[start + 1 :]:
        if line and not line.startswith("\t") and ":" in line:
            break
        stripped = line.strip()
        if stripped.startswith("$(PYTHON) -m "):
            modules.append(stripped.removeprefix("$(PYTHON) -m "))
    return modules


def _make_all_modules(makefile_text: str) -> list[str]:
    targets = ["data", "clean", "analysis", "charts", "evidence", "test", "release-evidence"]
    modules: list[str] = []
    for target in targets:
        if target == "test":
            modules.append("pytest")
        else:
            modules.extend(_make_modules_for_target(makefile_text, target))
    return modules


def test_pipeline_all_matches_makefile_order() -> None:
    assert PIPELINE_MODULES == _make_all_modules((ROOT / "Makefile").read_text(encoding="utf-8"))


def test_pipeline_finishes_with_tests_then_v2_release_packaging() -> None:
    assert PIPELINE_MODULES[-2:] == ["pytest", "uk_wages.release_package"]


def test_locked_pipeline_changes_only_the_download_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []
    monkeypatch.setattr(
        pipeline,
        "run_modules",
        lambda modules: captured.extend(modules),
    )

    pipeline.main(["--all", "--locked"])

    assert captured[0] == "uk_wages.download --locked"
    assert captured[1:] == PIPELINE_MODULES[1:]
    assert [step for step in captured if "--locked" in step] == [
        "uk_wages.download --locked"
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
