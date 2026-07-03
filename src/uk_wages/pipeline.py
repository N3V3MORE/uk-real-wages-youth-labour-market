from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .utils import project_path


PIPELINE_STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("uk_wages.download", ()),
    ("uk_wages.clean_cpi", ()),
    ("uk_wages.clean_ashe", ()),
    ("uk_wages.clean_region_ashe", ()),
    ("uk_wages.clean_a05", ()),
    ("uk_wages.clean_earn01", ()),
    ("uk_wages.clean_rti", ()),
    ("uk_wages.ashe_decomposition", ()),
    ("uk_wages.minimum_wage", ()),
    ("uk_wages.analysis", ()),
    ("uk_wages.rti_analysis", ()),
    ("uk_wages.charts", ()),
    ("uk_wages.rti_triangulation", ()),
    ("uk_wages.robustness", ("--run-all",)),
    ("uk_wages.source_validation", ()),
    ("uk_wages.triangulation", ()),
    ("uk_wages.final_claims", ()),
    ("uk_wages.research_note", ()),
    ("uk_wages.robustness", ("--contrarian",)),
    ("uk_wages.evidence", ("--build-report",)),
)


def _run_module(module: str, args: tuple[str, ...] = ()) -> None:
    subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=project_path(),
        check=True,
    )


def _require_lockfile(lockfile: Path) -> None:
    if not lockfile.exists():
        raise FileNotFoundError(
            "Locked pipeline requested, but requirements.lock is missing."
        )


def run_all(*, locked: bool = False) -> None:
    if locked:
        _require_lockfile(project_path("requirements.lock"))

    for module, args in PIPELINE_STEPS:
        _run_module(module, args)
    _run_module("pytest")
    _run_module("uk_wages.release_package")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the UK wages evidence pipeline.")
    parser.add_argument("--all", action="store_true", help="Run the full evidence pipeline.")
    parser.add_argument(
        "--locked",
        action="store_true",
        help="Require the committed requirements.lock before running.",
    )
    args = parser.parse_args(argv)

    if not args.all:
        parser.error("Only the full pipeline is currently supported; pass --all.")

    run_all(locked=args.locked)


if __name__ == "__main__":
    main()
