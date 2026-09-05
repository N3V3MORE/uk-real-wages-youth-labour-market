from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence


PIPELINE_MODULES = [
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
    "uk_wages.release_package",
]


Runner = Callable[[list[str]], subprocess.CompletedProcess]


def _command_for_step(step: str, *, executable: str = sys.executable) -> list[str]:
    parts = shlex.split(step)
    if parts[0] == "pytest":
        return [executable, "-m", "pytest", *parts[1:]]
    return [executable, "-m", *parts]


def run_modules(
    modules: Sequence[str],
    *,
    executable: str = sys.executable,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> None:
    for step in modules:
        command = _command_for_step(step, executable=executable)
        print(" ".join(command), flush=True)
        runner(command, check=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the project pipeline without requiring make.")
    parser.add_argument("--all", action="store_true", help="Run the same steps as make all.")
    parser.add_argument(
        "--locked",
        action="store_true",
        help="Use config/sources.lock.yaml for the download step.",
    )
    args = parser.parse_args(argv)
    if not args.all:
        parser.error("Only --all is currently supported.")

    modules = list(PIPELINE_MODULES)
    if args.locked:
        modules[0] = "uk_wages.download --locked"
    run_modules(modules)


if __name__ == "__main__":
    main()
