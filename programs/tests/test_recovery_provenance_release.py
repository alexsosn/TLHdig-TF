"""#150 RED: production split-provenance TF must pass source-event audit.

Unlike the isolated four-source gate, this test executes the real production
provenance split and then loads both *on-disk* modules as a consumer.
"""
from pathlib import Path
import sys
import shutil

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build as build_program
import validate_current
from tlhdig import convert, repair
from tlhdig.paths import CORPUS, PATCHES


@pytest.fixture(scope="module")
def split_recovered_tf(tmp_path_factory):
    root = tmp_path_factory.mktemp("split-recovery-current")
    version = build_program.TF_VERSION
    tf_dir = root / "tf" / version
    provenance_dir = root / "tf-provenance" / version
    tf_dir.mkdir(parents=True)
    paths = tuple(sorted(convert.VERIFIED_RECOVERY_PILOTS))
    assert len(paths) == 4

    assert convert.build(
        CORPUS, tf_dir, files=[CORPUS / rel for rel in paths],
        patches=repair.read_manifest(PATCHES),
        terminal_recovery_paths=paths, load=False,
    ) is True

    # Production path: do not fake the module split by manually moving the
    # features. Exercise the exact method full build.py calls after writing TF.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(build_program, "ROOT", root)
        moved = build_program.split_provenance(tf_dir)

    assert set(moved) == {"srcxml", "src_span"}
    assert (provenance_dir / "srcxml.tf").is_file()
    assert (provenance_dir / "src_span.tf").is_file()
    assert not (tf_dir / "srcxml.tf").exists()
    assert not (tf_dir / "src_span.tf").exists()
    return tf_dir, provenance_dir


def test_real_split_current_artifact_source_gate(split_recovered_tf):
    from check_recovery_current import verify_artifact

    tf_dir, provenance_dir = split_recovered_tf
    reports = verify_artifact(tf_dir, provenance_dir)
    assert len(reports) == 4
    assert {r.source for r in reports} == set(convert.VERIFIED_RECOVERY_PILOTS)
    assert sum(r.words for r in reports) == 216
    assert sum(r.lines for r in reports) == 88


def test_recovery_gate_fails_closed_without_separate_provenance(split_recovered_tf, tmp_path):
    from check_recovery_current import verify_artifact

    tf_dir, provenance_dir = split_recovered_tf
    assert not (tf_dir / "srcxml.tf").exists()
    with pytest.raises((ValueError, OSError), match="provenance|srcxml|module"):
        verify_artifact(tf_dir, tmp_path / "missing-provenance")

    incomplete = tmp_path / "missing-span"
    incomplete.mkdir()
    shutil.copyfile(provenance_dir / "srcxml.tf", incomplete / "srcxml.tf")
    with pytest.raises((ValueError, OSError), match="provenance|src_span|module"):
        verify_artifact(tf_dir, incomplete)


def test_full_validation_runs_recovery_gate_after_provenance_split():
    names = [gate.name for gate in validate_current.GATES]
    assert names.count("recovery-source-current") == 1
    assert names.index("provenance-split") < names.index("recovery-source-current")
    command = next(
        gate.command for gate in validate_current.GATES
        if gate.name == "recovery-source-current"
    )
    assert command == ("python", "programs/check_recovery_current.py")
