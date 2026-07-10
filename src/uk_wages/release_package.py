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


V2_RELEASE_FILES = [
    ReleaseFile(
        Path("outputs/evidence/final_claims.md"),
        "final_claims.md",
        "Qualified claim wording for public summaries.",
    ),
    ReleaseFile(
        Path("reports/research_note.md"),
        "research_note.md",
        "Narrative research note generated from current outputs.",
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
        Path("outputs/evidence/fragility_diagnostics.md"),
        "fragility_diagnostics.md",
        "Detailed diagnostics for robustness specifications.",
    ),
    ReleaseFile(
        Path("outputs/evidence/source_value_checks.csv"),
        "source_value_checks.csv",
        "Raw-to-processed source value audit checks.",
    ),
    ReleaseFile(
        Path("outputs/evidence/ashe_quality_availability.md"),
        "ashe_quality_availability.md",
        "Availability of ASHE quality and reliability fields.",
    ),
    ReleaseFile(
        Path("outputs/evidence/ashe_uncertainty_bands.md"),
        "ashe_uncertainty_bands.md",
        "Approximate ASHE uncertainty bands from published quality measures.",
    ),
    ReleaseFile(
        Path("outputs/evidence/ashe_composition_audit.md"),
        "ashe_composition_audit.md",
        "Audit of ASHE composition and coverage changes.",
    ),
    ReleaseFile(
        Path("outputs/evidence/triangulation_summary.csv"),
        "triangulation_summary.csv",
        "ASHE and EARN01 triangulation summary.",
    ),
    ReleaseFile(
        Path("outputs/evidence/rti_ashe_annual_summary.csv"),
        "rti_ashe_annual_summary.csv",
        "Annual RTI and ASHE triangulation summary.",
    ),
    ReleaseFile(
        Path("outputs/evidence/claim_confidence_ladder.csv"),
        "claim_confidence_ladder.csv",
        "Structured confidence classification for reviewer claims.",
    ),
    ReleaseFile(
        Path("outputs/evidence/claim_confidence.md"),
        "claim_confidence.md",
        "Reviewer-facing explanation of claim confidence.",
    ),
    ReleaseFile(
        Path("outputs/evidence/headline_number_lineage.csv"),
        "headline_number_lineage.csv",
        "Structured lineage from headline numbers to source evidence.",
    ),
    ReleaseFile(
        Path("outputs/evidence/headline_number_lineage.md"),
        "headline_number_lineage.md",
        "Reviewer-facing headline-number lineage.",
    ),
    ReleaseFile(
        Path("outputs/evidence/option_b_ds_report.md"),
        "option_b_ds_report.md",
        "Option B diagnostic report and modelling caveats.",
    ),
    ReleaseFile(
        Path("config/sources.lock.yaml"),
        "sources.lock.yaml",
        "Locked source URLs and SHA-256 hashes.",
    ),
    ReleaseFile(
        Path("requirements.lock"),
        "requirements.lock",
        "Python dependency constraints for the release environment.",
    ),
]


def _readme_text(release_name: str, files: list[ReleaseFile]) -> str:
    lines = [
        f"# {release_name} Evidence Package",
        "",
        "This folder is packaged evidence for reviewer inspection.",
        "Raw data, processed data, and chart paths referenced by the lineage files are rebuild-only and are not copied into this folder.",
        "sources.lock.yaml fixes source bytes; requirements.lock constrains Python dependencies.",
        "Rebuild the package with:",
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
    project_root: str | Path = project_path(),
    release_name: str = "v2",
) -> Path:
    root = Path(project_root)
    package_root = root / "releases" / release_name / "evidence"
    ensure_dir(package_root)

    manifest_files = []
    for spec in V2_RELEASE_FILES:
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
        _readme_text(release_name, V2_RELEASE_FILES),
        encoding="utf-8",
    )
    write_json(
        package_root / "manifest.json",
        {
            "release_name": release_name,
            "source_lock_sha256": sha256_file(package_root / "sources.lock.yaml"),
            "requirements_lock_sha256": sha256_file(package_root / "requirements.lock"),
            "files": manifest_files,
        },
    )
    return package_root


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the release evidence package.")
    parser.add_argument("--release-name", default="v2")
    args = parser.parse_args(argv)
    print(build_release_package(release_name=args.release_name))


if __name__ == "__main__":
    main()
