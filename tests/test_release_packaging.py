from __future__ import annotations

import json
from pathlib import Path

import pytest

from uk_wages.release_package import REQUIRED_RELEASE_FILES, build_release_package


def _write_required_source_files(root: Path) -> None:
    for spec in REQUIRED_RELEASE_FILES:
        path = root / spec.source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{spec.package_name}\n", encoding="utf-8")


def test_release_package_copies_required_evidence_and_manifest(tmp_path: Path) -> None:
    _write_required_source_files(tmp_path)

    package_root = build_release_package(project_root=tmp_path, release_name="v1")

    expected_names = {spec.package_name for spec in REQUIRED_RELEASE_FILES}
    assert {path.name for path in package_root.iterdir() if path.is_file()} >= expected_names
    assert "headline_lineage.csv" in expected_names

    manifest = json.loads((package_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["release_name"] == "v1"
    assert {entry["package_name"] for entry in manifest["files"]} == expected_names
    assert all(len(entry["sha256"]) == 64 for entry in manifest["files"])
    assert (package_root / "README.md").exists()


def test_release_package_fails_when_evidence_file_is_missing(tmp_path: Path) -> None:
    _write_required_source_files(tmp_path)
    (tmp_path / REQUIRED_RELEASE_FILES[0].source_path).unlink()

    with pytest.raises(FileNotFoundError, match=REQUIRED_RELEASE_FILES[0].source_path.as_posix()):
        build_release_package(project_root=tmp_path, release_name="v1")
