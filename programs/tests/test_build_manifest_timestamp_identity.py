"""Regression contract for volatile Text-Fabric write timestamps in output identity."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import build_manifest


def _dirs(tmp_path: Path) -> tuple[Path, Path]:
    main = tmp_path / "tf" / "9.9.9"
    provenance = tmp_path / "tf-provenance" / "9.9.9"
    main.mkdir(parents=True)
    provenance.mkdir(parents=True)
    return main, provenance


def test_tf_datewritten_is_not_part_of_current_output_identity(tmp_path: Path) -> None:
    main, provenance = _dirs(tmp_path)
    feature = main / "sym.tf"
    feature.write_text(
        "@node\n@description=sign text\n@dateWritten=2026-09-08T15:59:37+00:00Z\n\n1\ta\n",
        encoding="utf8",
    )
    before = build_manifest.output_identity(main, provenance)

    feature.write_text(
        "@node\n@description=sign text\n@dateWritten=2026-09-11T08:00:00+00:00Z\n\n1\ta\n",
        encoding="utf8",
    )
    timestamp_only = build_manifest.output_identity(main, provenance)
    assert timestamp_only == before

    feature.write_text(
        "@node\n@description=sign text\n@dateWritten=2026-09-11T08:00:00+00:00Z\n\n1\tb\n",
        encoding="utf8",
    )
    changed_data = build_manifest.output_identity(main, provenance)
    assert changed_data["digest"] != before["digest"]


def test_non_tf_files_remain_byte_exact_in_output_identity(tmp_path: Path) -> None:
    main, provenance = _dirs(tmp_path)
    license_file = main / "LICENSE"
    license_file.write_text("@dateWritten=first\n", encoding="utf8")
    before = build_manifest.output_identity(main, provenance)

    license_file.write_text("@dateWritten=second\n", encoding="utf8")
    after = build_manifest.output_identity(main, provenance)
    assert after["digest"] != before["digest"]
