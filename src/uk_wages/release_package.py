from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

from .utils import ensure_dir, project_path, sha256_file, write_json


@dataclass(frozen=True)
class ReleaseFile:
    source_path: Path
    package_name: str
    description: str


REQUIRED_RELEASE_FILES = [
    ReleaseFile(
        Path("outputs/evidence/final_claims.md"),
        "final_claims.md",
        "Qualified claim wording for public summaries.",
    ),
    ReleaseFile(
        Path("outputs/tables/age_group_real_earnings_change.csv"),
        "age_group_real_earnings_change.csv",
        "Main ASHE real earnings change table by age group.",
    ),
    ReleaseFile(
        Path("outputs/evidence/fragility_scores.csv"),
        "fragility_scores.csv",
        "Robustness and material-disagreement score table.",
    ),
    ReleaseFile(
        Path("outputs/evidence/source_value_checks.csv"),
        "source_value_checks.csv",
        "Raw-to-processed source value audit checks.",
    ),
    ReleaseFile(
        Path("outputs/evidence/headline_lineage.csv"),
        "headline_lineage.csv",
        "Lineage from public headlines to source evidence artifacts.",
    ),
    ReleaseFile(
        Path("reports/research_note.md"),
        "research_note.md",
        "Narrative research note generated from current outputs.",
    ),
]


def _readme_text(release_name: str, files: list[ReleaseFile]) -> str:
    lines = [
        f"# {release_name} Evidence Package",
        "",
        "This folder is the small, committed evidence snapshot for review. It is rebuilt from ignored raw, processed, and output data with:",
        "",
        "```powershell",
        "python -m uk_wages.pipeline --all --locked",
        "```",
        "",
        "Files:",
        "",
    ]
    for spec in files:
        lines.append(f"- `{spec.package_name}` - {spec.description}")
    lines.extend(["", "Use `manifest.json` to verify file sizes and SHA-256 hashes.", ""])
    return "\n".join(lines)


def build_release_package(
    *,
    project_root: str | Path = project_path(),
    release_name: str = "v1",
) -> Path:
    root = Path(project_root)
    package_root = root / "releases" / release_name / "evidence"
    ensure_dir(package_root)

    manifest_files = []
    for spec in REQUIRED_RELEASE_FILES:
        source = root / spec.source_path
        if not source.exists():
            raise FileNotFoundError(f"Missing release evidence source: {spec.source_path.as_posix()}")
        destination = package_root / spec.package_name
        shutil.copy2(source, destination)
        manifest_files.append(
            {
                "source_path": spec.source_path.as_posix(),
                "package_name": spec.package_name,
                "description": spec.description,
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
            }
        )

    (package_root / "README.md").write_text(
        _readme_text(release_name, REQUIRED_RELEASE_FILES),
        encoding="utf-8",
    )
    write_json(
        package_root / "manifest.json",
        {
            "release_name": release_name,
            "files": manifest_files,
        },
    )
    return package_root


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the release evidence package.")
    parser.add_argument("--release-name", default="v1")
    args = parser.parse_args(argv)
    print(build_release_package(release_name=args.release_name))


if __name__ == "__main__":
    main()
