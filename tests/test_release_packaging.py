from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

import pytest

from uk_wages import release_package
from uk_wages.release_package import build_release_package, verify_release_package_integrity
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
        if package_name == "sources.lock.yaml":
            continue
        path = project_root / source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"review evidence for {package_name}\n", encoding="utf-8")

    locked_source = project_root / "data/raw/fixture/official-source.bin"
    locked_source.parent.mkdir(parents=True, exist_ok=True)
    locked_source.write_bytes(b"official locked source bytes\n")
    source_lock = project_root / EXPECTED_V2_SOURCES["sources.lock.yaml"]
    source_lock.parent.mkdir(parents=True, exist_ok=True)
    source_lock.write_text(
        "\n".join(
            [
                "version: 1",
                "sources:",
                "  fixture_official_source:",
                "    source_key: fixture",
                "    source_url: https://example.com/official-source.bin",
                "    downloaded_file: fixture/official-source.bin",
                "    release: fixture",
                f"    sha256: {sha256_file(locked_source)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _package_hashes(package_root: Path) -> dict[str, str]:
    return {
        path.name: sha256_file(path)
        for path in package_root.iterdir()
        if path.is_file()
    }


def _package_bytes(package_root: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in package_root.iterdir()
        if path.is_file()
    }


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
    assert "/current/" in readme
    assert "availability" in readme
    assert "hash mismatch" in readme


def test_committed_v2_package_matches_current_generated_sources() -> None:
    project_root = Path(__file__).resolve().parents[1]
    package_root = project_root / "releases/v2/evidence"
    manifest_path = package_root / "manifest.json"
    if not manifest_path.exists():
        pytest.skip("Committed release package is not available in this checkout.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing_sources = [
        entry["source_path"]
        for entry in manifest["files"]
        if not (project_root / entry["source_path"]).is_file()
    ]
    if missing_sources:
        pytest.skip(
            "Generated release sources are genuinely unavailable: " + ", ".join(missing_sources)
        )

    verified = verify_release_package_integrity(project_root=project_root)

    assert verified == package_root


def test_rebuild_removes_files_not_declared_by_v2_package(tmp_path: Path) -> None:
    _write_release_inputs(tmp_path)
    package_root = build_release_package(project_root=tmp_path)
    (package_root / "obsolete-v1-file.csv").write_text("obsolete\n", encoding="utf-8")

    rebuilt_root = build_release_package(project_root=tmp_path)

    assert rebuilt_root == package_root
    assert not (rebuilt_root / "obsolete-v1-file.csv").exists()
    assert {path.name for path in rebuilt_root.iterdir()} == EXPECTED_V2_FILES | {
        "README.md",
        "manifest.json",
    }


def test_failed_rebuild_preserves_last_successful_package(tmp_path: Path) -> None:
    _write_release_inputs(tmp_path)
    package_root = build_release_package(project_root=tmp_path)
    original_hashes = _package_hashes(package_root)
    (tmp_path / EXPECTED_V2_SOURCES["final_claims.md"]).write_text(
        "changed early source\n",
        encoding="utf-8",
    )
    (tmp_path / EXPECTED_V2_SOURCES["requirements.lock"]).unlink()

    with pytest.raises(FileNotFoundError, match="requirements.lock"):
        build_release_package(project_root=tmp_path)

    assert _package_hashes(package_root) == original_hashes


def test_locked_source_hash_mismatch_preserves_previous_package_byte_for_byte(
    tmp_path: Path,
) -> None:
    _write_release_inputs(tmp_path)
    package_root = build_release_package(project_root=tmp_path)
    previous_package = _package_bytes(package_root)
    locked_source = tmp_path / "data/raw/fixture/official-source.bin"
    locked_source.write_bytes(b"tampered source bytes\n")

    with pytest.raises(ValueError, match="Locked file hash mismatch"):
        build_release_package(project_root=tmp_path)

    assert _package_bytes(package_root) == previous_package


def test_missing_locked_source_preserves_previous_package_byte_for_byte(
    tmp_path: Path,
) -> None:
    _write_release_inputs(tmp_path)
    package_root = build_release_package(project_root=tmp_path)
    previous_package = _package_bytes(package_root)
    locked_source = tmp_path / "data/raw/fixture/official-source.bin"
    locked_source.unlink()

    with pytest.raises(FileNotFoundError, match="fixture/official-source.bin"):
        build_release_package(project_root=tmp_path)

    assert _package_bytes(package_root) == previous_package


@pytest.mark.parametrize(
    "release_name",
    [
        "",
        ".",
        "..",
        "nested/v2",
        r"nested\v2",
        "/tmp/release",
        r"C:\tmp\release",
        "C:relative",
    ],
)
def test_release_name_must_be_one_relative_path_component(
    tmp_path: Path,
    release_name: str,
) -> None:
    _write_release_inputs(tmp_path)

    with pytest.raises(ValueError, match="release_name"):
        build_release_package(project_root=tmp_path, release_name=release_name)


@pytest.mark.parametrize(
    "release_name",
    ["nested/v2", r"nested\v2", "/tmp/release", r"C:\tmp\release", "C:relative"],
)
def test_release_name_validation_rejects_both_path_flavours_on_posix(
    monkeypatch: pytest.MonkeyPatch,
    release_name: str,
) -> None:
    monkeypatch.setattr(release_package, "Path", PurePosixPath)

    with pytest.raises(ValueError, match="release_name"):
        release_package._validate_release_name(release_name)


def test_absolute_release_name_is_rejected_before_metadata_generation(
    tmp_path: Path,
) -> None:
    _write_release_inputs(tmp_path)
    absolute_release_name = (tmp_path / "releases/absolute-v2").resolve()

    with pytest.raises(ValueError, match="release_name"):
        build_release_package(
            project_root=tmp_path,
            release_name=str(absolute_release_name),
        )

    assert not (absolute_release_name / "evidence").exists()

    package_root = build_release_package(project_root=tmp_path)
    manifest = json.loads((package_root / "manifest.json").read_text(encoding="utf-8"))
    readme = (package_root / "README.md").read_text(encoding="utf-8")
    metadata_paths = [
        manifest["release_name"],
        *(entry["source_path"] for entry in manifest["files"]),
    ]

    assert all(not Path(value).is_absolute() for value in metadata_paths)
    assert str(tmp_path.resolve()) not in readme


def test_backup_cleanup_failure_warns_after_successful_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_release_inputs(tmp_path)
    package_root = build_release_package(project_root=tmp_path)
    changed_source = tmp_path / EXPECTED_V2_SOURCES["final_claims.md"]
    changed_source.write_text("changed evidence for promotion\n", encoding="utf-8")
    real_rmtree = release_package.shutil.rmtree

    def fail_backup_cleanup(path: str | Path, *args: object, **kwargs: object) -> None:
        if Path(path).name.endswith(".previous"):
            raise OSError("simulated locked backup")
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(release_package.shutil, "rmtree", fail_backup_cleanup)

    with pytest.warns(RuntimeWarning) as warning_records:
        rebuilt_root = build_release_package(project_root=tmp_path)

    manifest = json.loads((package_root / "manifest.json").read_text(encoding="utf-8"))
    leftover_backups = list((tmp_path / "releases/v2").glob(".evidence-*.previous"))
    assert rebuilt_root == package_root
    assert sha256_file(package_root / "final_claims.md") == sha256_file(changed_source)
    assert all(
        entry["sha256"] == sha256_file(package_root / entry["package_name"])
        for entry in manifest["files"]
    )
    assert len(leftover_backups) == 1
    assert str(leftover_backups[0]) in str(warning_records[0].message)
