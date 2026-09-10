"""Canonical current-artifact validation contract after release simplification (#116)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate_current
from tlhdig import build_manifest


EXPECTED_GATES = (
    "corpus-identity",
    "repair-manifest",
    "sign-round-trip",
    "morphology",
    "structure",
    "sign-language",
    "manuscript-joins",
    "contract-a-graph",
    "marker-conservation",
    "tag-inventory",
    "provenance-split",
    "alignment",
    "fetch-signrefs",
    "check-signrefs",
    "app",
    "census",
)


def synthetic(tmp_path: Path):
    root = tmp_path / "repo"
    main = root / "tf" / "9.9.9"
    prov = root / "tf-provenance" / "9.9.9"
    main.mkdir(parents=True)
    prov.mkdir(parents=True)
    (main / "otype.tf").write_text("@node\n\n1\tsign\n", encoding="utf8")
    (prov / "srcxml.tf").write_text("@node\n\n1\ta\n", encoding="utf8")
    inputs = {}
    for name in ("corpusManifest", "repairManifest", "exclusions", "signrefLock", "dependencies"):
        path = root / f"{name}.txt"
        path.write_text(name + "\n", encoding="utf8")
        inputs[name] = path
    return root, main, prov, inputs


def passed(_gate):
    return validate_current.GateOutcome("passed", 0)


def run_synthetic(tmp_path, *, runner=passed, clean=lambda: [], head=lambda: "a" * 40):
    root, main, prov, inputs = synthetic(tmp_path)
    rc = validate_current.validate(
        main_dir=main,
        provenance_dir=prov,
        source_version="0.3",
        tf_version="9.9.9",
        code_commit="a" * 40,
        gates=(validate_current.Gate("one", ("one",)),),
        runner=runner,
        input_files=inputs,
        root=root,
        tracked_changes=clean,
        current_head=head,
    )
    return rc, root, main, prov, inputs


def test_current_gate_set_is_substantive_and_has_no_predecessor_policy():
    assert tuple(gate.name for gate in validate_current.GATES) == EXPECTED_GATES
    assert "predecessor-delta" not in EXPECTED_GATES
    commands = {gate.name: gate.command for gate in validate_current.GATES}
    assert commands["manuscript-joins"] == ("python", "programs/check_manuscript_joins.py")
    assert commands["sign-language"] == ("python", "programs/check_sign_language.py")


def test_external_signref_gates_use_hard_complete_validation_mode():
    commands = {gate.name: gate.command for gate in validate_current.GATES}
    for name in ("fetch-signrefs", "check-signrefs"):
        assert commands[name][-2:] == ("--mode", "release")


def test_signref_runner_uses_explicit_status_not_zero_exit(monkeypatch, tmp_path):
    status = tmp_path / "signrefs-status.json"
    monkeypatch.setattr(validate_current, "STATUS", status)

    def fake_run(*_args, **_kwargs):
        status.write_text(
            json.dumps({"mode": "release", "state": "skipped-unavailable", "sources": []}),
            encoding="utf8",
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(validate_current.subprocess, "run", fake_run)
    outcome = validate_current.run_gate(
        validate_current.Gate(
            "fetch-signrefs", ("python", "programs/fetch_signrefs.py", "--mode", "release")
        )
    )
    assert outcome.status == "skipped-unavailable"
    assert outcome.returncode == 0


def test_success_writes_manifest_that_verifies(tmp_path):
    rc, root, main, prov, inputs = run_synthetic(tmp_path)
    assert rc == 0
    manifest = main / build_manifest.MANIFEST
    assert manifest.is_file()
    assert build_manifest.verify_manifest(
        manifest,
        source_version="0.3",
        tf_version="9.9.9",
        main_dir=main,
        provenance_dir=prov,
        input_files=inputs,
        gate_names=("one",),
        root=root,
    ) is None


def test_required_skip_does_not_write_manifest(tmp_path):
    def skipped(_gate):
        return validate_current.GateOutcome("skipped-unavailable", 0)

    rc, _root, main, _prov, _inputs = run_synthetic(tmp_path, runner=skipped)
    assert rc == 1
    assert not (main / build_manifest.MANIFEST).exists()


def test_output_mutation_during_validation_does_not_write_manifest(tmp_path):
    root, main, prov, inputs = synthetic(tmp_path)

    def mutate(_gate):
        (main / "otype.tf").write_text("CHANGED\n", encoding="utf8")
        return validate_current.GateOutcome("passed", 0)

    rc = validate_current.validate(
        main_dir=main,
        provenance_dir=prov,
        source_version="0.3",
        tf_version="9.9.9",
        code_commit="a" * 40,
        gates=(validate_current.Gate("mutate", ("mutate",)),),
        runner=mutate,
        input_files=inputs,
        root=root,
        tracked_changes=lambda: [],
        current_head=lambda: "a" * 40,
    )
    assert rc == 1
    assert not (main / build_manifest.MANIFEST).exists()


def test_input_mutation_during_validation_does_not_write_manifest(tmp_path):
    root, main, prov, inputs = synthetic(tmp_path)

    def mutate(_gate):
        inputs["repairManifest"].write_text("CHANGED\n", encoding="utf8")
        return validate_current.GateOutcome("passed", 0)

    rc = validate_current.validate(
        main_dir=main,
        provenance_dir=prov,
        source_version="0.3",
        tf_version="9.9.9",
        code_commit="a" * 40,
        gates=(validate_current.Gate("mutate", ("mutate",)),),
        runner=mutate,
        input_files=inputs,
        root=root,
        tracked_changes=lambda: [],
        current_head=lambda: "a" * 40,
    )
    assert rc == 1
    assert not (main / build_manifest.MANIFEST).exists()


def test_dirty_checkout_before_validation_does_not_write_manifest(tmp_path):
    rc, _root, main, _prov, _inputs = run_synthetic(
        tmp_path,
        clean=lambda: ["M programs/check_alignment.py"],
    )
    assert rc == 1
    assert not (main / build_manifest.MANIFEST).exists()


def test_head_change_during_validation_does_not_write_manifest(tmp_path):
    calls = iter(("a" * 40, "b" * 40))
    rc, _root, main, _prov, _inputs = run_synthetic(
        tmp_path,
        head=lambda: next(calls),
    )
    assert rc == 1
    assert not (main / build_manifest.MANIFEST).exists()
