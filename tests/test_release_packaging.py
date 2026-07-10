from __future__ import annotations

import json
from pathlib import Path

from uk_wages.release_package import build_release_package
from uk_wages.utils import sha256_file


EXPECTED_V2_SOURCES = {
    "final_claims.md": "outputs/evidence/final_claims.md",
    "research_note.md": "reports/research_note.md",
    "age_group_real_earnings_change.csv": (
        "outputs/tables/age_group_real_earnings_change.csv"
    ),
    "fragility_scores.csv": "outputs/evidence/fragility_scores.csv",
    "fragility_diagnostics.md": "outputs/evidence/fragility_diagnostics.md",
    "source_value_checks.csv": "outputs/evidence/source_value_checks.csv",
    "ashe_quality_availability.md": "outputs/evidence/ashe_quality_availability.md",
    "ashe_uncertainty_bands.md": "outputs/evidence/ashe_uncertainty_bands.md",
    "ashe_composition_audit.md": "outputs/evidence/ashe_composition_audit.md",
    "triangulation_summary.csv": "outputs/evidence/triangulation_summary.csv",
    "rti_ashe_annual_summary.csv": "outputs/evidence/rti_ashe_annual_summary.csv",
    "claim_confidence_ladder.csv": "outputs/evidence/claim_confidence_ladder.csv",
    "claim_confidence.md": "outputs/evidence/claim_confidence.md",
    "headline_number_lineage.csv": "outputs/evidence/headline_number_lineage.csv",
    "headline_number_lineage.md": "outputs/evidence/headline_number_lineage.md",
    "option_b_ds_report.md": "outputs/evidence/option_b_ds_report.md",
    "sources.lock.yaml": "config/sources.lock.yaml",
    "requirements.lock": "requirements.lock",
}

EXPECTED_V2_FILES = set(EXPECTED_V2_SOURCES)


def _write_release_inputs(project_root: Path) -> None:
    for package_name, source_path in EXPECTED_V2_SOURCES.items():
        path = project_root / source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"review evidence for {package_name}\n", encoding="utf-8")


def test_release_package_defaults_to_v2(tmp_path: Path) -> None:
    _write_release_inputs(tmp_path)

    package_root = build_release_package(project_root=tmp_path)

    assert package_root == tmp_path / "releases/v2/evidence"


def test_manifest_describes_exact_v2_package_with_verified_hashes(tmp_path: Path) -> None:
    _write_release_inputs(tmp_path)
    package_root = build_release_package(project_root=tmp_path, release_name="v2")

    manifest = json.loads((package_root / "manifest.json").read_text(encoding="utf-8"))

    assert set(manifest) == {
        "release_name",
        "source_lock_sha256",
        "requirements_lock_sha256",
        "files",
    }
    assert manifest["release_name"] == "v2"
    assert {entry["package_name"] for entry in manifest["files"]} == EXPECTED_V2_FILES
    assert {path.name for path in package_root.iterdir()} == EXPECTED_V2_FILES | {
        "README.md",
        "manifest.json",
    }
    for entry in manifest["files"]:
        assert entry["source_path"] == EXPECTED_V2_SOURCES[entry["package_name"]]
        assert len(entry["sha256"]) == 64
        assert entry["sha256"] == sha256_file(package_root / entry["package_name"])


def test_manifest_lock_hashes_match_packaged_lockfiles(tmp_path: Path) -> None:
    _write_release_inputs(tmp_path)
    package_root = build_release_package(project_root=tmp_path, release_name="v2")

    manifest = json.loads((package_root / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["source_lock_sha256"] == sha256_file(
        package_root / "sources.lock.yaml"
    )
    assert manifest["requirements_lock_sha256"] == sha256_file(
        package_root / "requirements.lock"
    )


def test_readme_distinguishes_packaged_evidence_from_rebuild_only_inputs(
    tmp_path: Path,
) -> None:
    _write_release_inputs(tmp_path)
    package_root = build_release_package(project_root=tmp_path, release_name="v2")

    readme = (package_root / "README.md").read_text(encoding="utf-8").lower()

    assert "packaged evidence" in readme
    assert "rebuild-only" in readme
    assert "sources.lock.yaml fixes source bytes" in readme
    assert "requirements.lock constrains python dependencies" in readme
