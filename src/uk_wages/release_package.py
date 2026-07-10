from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from .download import verify_locked_sources
from .utils import ensure_dir, project_path, sha256_file, write_json


@dataclass(frozen=True)
class ReleaseFile:
    source_path: Path
    package_name: str
    description: str


@dataclass(frozen=True)
class ReleaseIntegrityResult:
    package_root: Path
    compared_sources: frozenset[str]
    missing_generated_sources: frozenset[str]


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

MANIFEST_KEYS = {
    "release_name",
    "source_lock_sha256",
    "requirements_lock_sha256",
    "files",
}
MANIFEST_FILE_KEYS = {
    "source_path",
    "package_name",
    "description",
    "bytes",
    "sha256",
}
CLEAN_CHECKOUT_GENERATED_SOURCES = frozenset(
    spec.source_path.as_posix()
    for spec in V2_RELEASE_FILES
    if spec.source_path.parts and spec.source_path.parts[0] == "outputs"
)


def _readme_text(release_name: str, files: list[ReleaseFile]) -> str:
    lines = [
        f"# {release_name} Evidence Package",
        "",
        "This folder is packaged evidence for reviewer inspection.",
        "Raw data, processed data, and chart paths referenced by the lineage files are rebuild-only and are not copied into this folder.",
        "sources.lock.yaml fixes source bytes; requirements.lock constrains Python dependencies.",
        "Some ONS source URLs use mutable /current/ aliases. This is an availability risk: a changed upstream file causes an exact hash mismatch, and the locked rebuild fails until the source-lock update is reviewed.",
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


def _validate_release_name(release_name: str) -> None:
    posix_path = PurePosixPath(release_name)
    windows_path = PureWindowsPath(release_name)
    if (
        not release_name.strip()
        or posix_path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or posix_path.parts != (release_name,)
        or windows_path.parts != (release_name,)
        or release_name in {".", ".."}
    ):
        raise ValueError("release_name must be one non-empty relative path component")


def _replace_package_directory(temporary_root: Path, package_root: Path) -> None:
    if not package_root.exists():
        temporary_root.replace(package_root)
        return

    previous_root = temporary_root.with_name(f"{temporary_root.name}.previous")
    package_root.replace(previous_root)
    try:
        temporary_root.replace(package_root)
    except BaseException:
        previous_root.replace(package_root)
        raise
    try:
        shutil.rmtree(previous_root)
    except OSError as exc:
        warnings.warn(
            f"Could not remove release package backup {previous_root}: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )


def verify_release_package_integrity(
    project_root: str | Path = project_path(),
    release_name: str = "v2",
) -> ReleaseIntegrityResult:
    _validate_release_name(release_name)
    root = Path(project_root).resolve()
    package_root = root / "releases" / release_name / "evidence"
    manifest_path = package_root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing release manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        raise ValueError("Release manifest top-level schema is invalid")
    if manifest.get("release_name") != release_name:
        raise ValueError(
            f"Release manifest release_name must be {release_name!r}, got "
            f"{manifest.get('release_name')!r}"
        )
    files = manifest.get("files")
    if (
        not isinstance(files, list)
        or not all(isinstance(entry, dict) for entry in files)
        or any(set(entry) != MANIFEST_FILE_KEYS for entry in files)
    ):
        raise ValueError("Release manifest file-entry schema is invalid")

    expected_specs = {spec.package_name: spec for spec in V2_RELEASE_FILES}
    expected_sources = {
        package_name: spec.source_path.as_posix()
        for package_name, spec in expected_specs.items()
    }
    declared_names = [str(entry.get("package_name", "")) for entry in files]
    if len(declared_names) != len(set(declared_names)) or set(declared_names) != set(
        expected_sources
    ):
        raise ValueError("Release manifest does not declare the exact v2 evidence set")
    entries_by_name: dict[str, dict[str, object]] = {}
    for entry in files:
        package_name = str(entry["package_name"])
        spec = expected_specs[package_name]
        if entry["source_path"] != spec.source_path.as_posix():
            raise ValueError(
                f"Unexpected source_path for {package_name}: {entry['source_path']}"
            )
        if entry["description"] != spec.description:
            raise ValueError(f"Unexpected description for {package_name}")
        byte_count = entry["bytes"]
        sha256 = entry["sha256"]
        if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0:
            raise ValueError(f"Invalid byte count for {package_name}")
        if not isinstance(sha256, str) or re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
            raise ValueError(f"Invalid sha256 for {package_name}")
        entries_by_name[package_name] = entry

    for lock_key in ["source_lock_sha256", "requirements_lock_sha256"]:
        lock_hash = manifest[lock_key]
        if not isinstance(lock_hash, str) or re.fullmatch(r"[0-9a-f]{64}", lock_hash) is None:
            raise ValueError(f"Invalid manifest lock hash: {lock_key}")

    actual_names = {path.name for path in package_root.iterdir() if path.is_file()}
    if actual_names != set(expected_sources) | {"README.md", "manifest.json"}:
        raise ValueError("Committed release package contains missing or undeclared files")
    expected_readme = _readme_text(release_name, V2_RELEASE_FILES)
    if (package_root / "README.md").read_text(encoding="utf-8") != expected_readme:
        raise ValueError("Release package README does not match the generator")

    compared_sources: set[str] = set()
    missing_generated_sources: set[str] = set()
    for package_name, spec in expected_specs.items():
        entry = entries_by_name[package_name]
        source_path = spec.source_path.as_posix()
        packaged = package_root / package_name
        if not packaged.is_file():
            raise FileNotFoundError(f"Missing packaged evidence file: {package_name}")
        packaged_bytes = packaged.read_bytes()
        expected_bytes = entry["bytes"]
        expected_hash = entry["sha256"]
        if expected_bytes != len(packaged_bytes):
            raise ValueError(f"Release byte-size mismatch for {package_name}")
        if expected_hash != sha256_file(packaged):
            raise ValueError(f"Release content mismatch for {package_name}")

        source = (root / spec.source_path).resolve()
        if not source.is_relative_to(root):
            raise ValueError(f"Release source must stay inside the project: {source_path}")
        if not source.is_file():
            if source_path in CLEAN_CHECKOUT_GENERATED_SOURCES:
                missing_generated_sources.add(source_path)
                continue
            raise FileNotFoundError(f"Missing tracked release source: {source_path}")
        source_bytes = source.read_bytes()
        if (
            expected_bytes != len(source_bytes)
            or expected_hash != sha256_file(source)
            or packaged_bytes != source_bytes
        ):
            raise ValueError(f"Release source mismatch for {package_name}")
        compared_sources.add(source_path)

    lock_checks = {
        "source_lock_sha256": "sources.lock.yaml",
        "requirements_lock_sha256": "requirements.lock",
    }
    for manifest_key, package_name in lock_checks.items():
        source = root / expected_sources[package_name]
        packaged = package_root / package_name
        if manifest.get(manifest_key) != sha256_file(source) or manifest.get(
            manifest_key
        ) != sha256_file(packaged):
            raise ValueError(f"Release lock hash mismatch for {package_name}")
    return ReleaseIntegrityResult(
        package_root=package_root,
        compared_sources=frozenset(compared_sources),
        missing_generated_sources=frozenset(missing_generated_sources),
    )


def build_release_package(
    project_root: str | Path = project_path(),
    release_name: str = "v2",
) -> Path:
    _validate_release_name(release_name)
    root = Path(project_root).resolve()
    releases_root = (root / "releases").resolve()
    release_root = (releases_root / release_name).resolve()
    if not release_root.is_relative_to(releases_root):
        raise ValueError("release_name must resolve inside the project's releases directory")
    package_root = release_root / "evidence"

    verify_locked_sources(
        lock_path=root / "config/sources.lock.yaml",
        raw_root=root / "data/raw",
    )

    sources: list[tuple[ReleaseFile, Path]] = []
    for spec in V2_RELEASE_FILES:
        source = root / spec.source_path
        if not source.exists():
            raise FileNotFoundError(
                f"Missing release evidence source: {spec.source_path.as_posix()}"
            )
        sources.append((spec, source))

    ensure_dir(release_root)
    temporary_root = Path(
        tempfile.mkdtemp(prefix=".evidence-", dir=release_root)
    )

    manifest_files = []
    try:
        for spec, source in sources:
            destination = temporary_root / spec.package_name
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

        (temporary_root / "README.md").write_text(
            _readme_text(release_name, V2_RELEASE_FILES),
            encoding="utf-8",
        )
        write_json(
            temporary_root / "manifest.json",
            {
                "release_name": release_name,
                "source_lock_sha256": sha256_file(
                    temporary_root / "sources.lock.yaml"
                ),
                "requirements_lock_sha256": sha256_file(
                    temporary_root / "requirements.lock"
                ),
                "files": manifest_files,
            },
        )
        _replace_package_directory(temporary_root, package_root)
    except BaseException:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)
        raise
    return package_root


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the release evidence package.")
    parser.add_argument("--release-name", default="v2")
    args = parser.parse_args(argv)
    print(build_release_package(release_name=args.release_name))


if __name__ == "__main__":
    main()
