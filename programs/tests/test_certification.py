"""Release certification orchestrates the gates that BUILD-COMPLETE claims passed."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import certification, release_policy, stamp


def dataset(tmp_path: Path, body: str = "1\ta\n") -> Path:
    root = tmp_path / "root"
    out = root / "tf" / "9.9.9"
    prov = root / "tf-provenance" / "9.9.9"
    out.mkdir(parents=True)
    prov.mkdir(parents=True)
    (out / "otype.tf").write_text("@node\n\n1\tsign\n", encoding="utf8")
    (out / "sym.tf").write_text("@node\n\n" + body, encoding="utf8")
    (prov / "srcxml.tf").write_text("@node\n\n1\ta\n", encoding="utf8")
    return out


def inputs(tmp_path: Path) -> dict[str, Path]:
    result = {}
    for name in release_policy.REQUIRED_INPUTS:
        path = tmp_path / f"{name}.txt"
        path.write_text(name + "\n", encoding="utf8")
        result[name] = path
    return result


def canonical_gates() -> list[certification.Gate]:
    return [certification.Gate(name, (name,)) for name in release_policy.REQUIRED_GATES]


def zero_defects() -> dict[str, int]:
    return {name: 0 for name in release_policy.FIDELITY_BASELINES}


def passed(_gate):
    return certification.GateOutcome("passed", 0)


def test_regression_valid_can_record_declared_nonzero_known_defects(tmp_path):
    out = dataset(tmp_path)
    report = tmp_path / "attempt.json"
    defects = {"knownLossy": 45, "contractAKnown": 16, "knownWordDeficit": 15}
    rc = certification.certify(
        out=out,
        source_version="0.3",
        tf_version="9.9.9",
        mode="regression-valid",
        gates=[certification.Gate("one", ("one",))],
        runner=passed,
        input_files=inputs(tmp_path),
        known_defects=defects,
        code_commit="a" * 40,
        report_path=report,
    )
    assert rc == 0
    manifest = json.loads((out / certification.MANIFEST).read_text(encoding="utf8"))
    assert manifest["knownDefects"] == defects
    assert manifest["mode"] == "regression-valid"
    assert manifest["policy"] == release_policy.POLICY
    assert manifest["gates"] == [
        {"name": "one", "command": ["one"], "status": "passed", "returncode": 0}
    ]
    # The generic state machine may be exercised with a fake gate set; publication
    # verification intentionally rejects that as non-canonical.
    assert stamp.check(out, require_full=True) is not None


def test_research_ready_runs_common_gates_then_refuses_nonzero_known_defects(tmp_path):
    out = dataset(tmp_path)
    defects = {"knownLossy": 1, "contractAKnown": 0, "knownWordDeficit": 0}
    calls = []

    def runner(gate):
        calls.append(gate.name)
        return certification.GateOutcome("passed", 0)

    report = tmp_path / "attempt.json"
    rc = certification.certify(
        out=out,
        source_version="0.3",
        tf_version="9.9.9",
        mode="research-ready",
        gates=[certification.Gate("one", ("one",))],
        runner=runner,
        input_files=inputs(tmp_path),
        known_defects=defects,
        code_commit="b" * 40,
        report_path=report,
    )
    assert rc == 1
    assert calls == ["one"]
    attempt = json.loads(report.read_text(encoding="utf8"))
    assert attempt["gates"][0]["status"] == "passed"
    assert "policyFailure" in attempt
    assert not (out / stamp.STAMP).exists()
    assert not (out / certification.MANIFEST).exists()


def test_required_gate_failure_leaves_no_stamp(tmp_path):
    out = dataset(tmp_path)
    stamp.write(out, "0.3", "9.9.9")

    def runner(gate):
        return certification.GateOutcome("failed", 7) if gate.name == "bad" else passed(gate)

    rc = certification.certify(
        out=out,
        source_version="0.3",
        tf_version="9.9.9",
        mode="regression-valid",
        gates=[certification.Gate("ok", ("ok",)), certification.Gate("bad", ("bad",))],
        runner=runner,
        input_files=inputs(tmp_path),
        known_defects=zero_defects(),
        code_commit="c" * 40,
        report_path=tmp_path / "attempt.json",
    )
    assert rc == 1
    assert not (out / stamp.STAMP).exists()
    attempt = json.loads((tmp_path / "attempt.json").read_text(encoding="utf8"))
    assert attempt["gates"][-1]["status"] == "failed"


def test_required_skip_is_not_success_even_with_zero_exit_code(tmp_path):
    out = dataset(tmp_path)

    def runner(_gate):
        return certification.GateOutcome("skipped-unavailable", 0)

    rc = certification.certify(
        out=out,
        source_version="0.3",
        tf_version="9.9.9",
        mode="regression-valid",
        gates=[certification.Gate("external-signrefs", ("check",))],
        runner=runner,
        input_files=inputs(tmp_path),
        known_defects=zero_defects(),
        code_commit="d" * 40,
        report_path=tmp_path / "attempt.json",
    )
    assert rc == 1
    assert not (out / stamp.STAMP).exists()


def test_dataset_mutation_during_gate_sequence_prevents_stamp(tmp_path):
    out = dataset(tmp_path)

    def runner(_gate):
        (out / "sym.tf").write_text("@node\n\n1\tCHANGED\n", encoding="utf8")
        return certification.GateOutcome("passed", 0)

    rc = certification.certify(
        out=out,
        source_version="0.3",
        tf_version="9.9.9",
        mode="regression-valid",
        gates=[certification.Gate("mutator", ("mutate",))],
        runner=runner,
        input_files=inputs(tmp_path),
        known_defects=zero_defects(),
        code_commit="e" * 40,
        report_path=tmp_path / "attempt.json",
    )
    assert rc == 1
    assert not (out / stamp.STAMP).exists()
    attempt = json.loads((tmp_path / "attempt.json").read_text(encoding="utf8"))
    assert attempt["artifactStable"] is False


def test_input_identity_mutation_during_gate_sequence_prevents_stamp(tmp_path):
    out = dataset(tmp_path)
    source_inputs = inputs(tmp_path)

    def runner(_gate):
        source_inputs["repairManifest"].write_text("CHANGED\n", encoding="utf8")
        return certification.GateOutcome("passed", 0)

    report = tmp_path / "attempt.json"
    rc = certification.certify(
        out=out,
        source_version="0.3",
        tf_version="9.9.9",
        mode="regression-valid",
        gates=[certification.Gate("input-mutator", ("mutate-input",))],
        runner=runner,
        input_files=source_inputs,
        known_defects=zero_defects(),
        code_commit="f" * 40,
        report_path=report,
    )
    assert rc == 1
    assert not (out / stamp.STAMP).exists()
    attempt = json.loads(report.read_text(encoding="utf8"))
    assert attempt["inputsStable"] is False


def test_successful_state_machine_records_input_identities(tmp_path):
    out = dataset(tmp_path)
    source_inputs = inputs(tmp_path)
    rc = certification.certify(
        out=out,
        source_version="0.3",
        tf_version="9.9.9",
        mode="research-ready",
        gates=[certification.Gate("one", ("python", "one.py"))],
        runner=passed,
        input_files=source_inputs,
        known_defects=zero_defects(),
        code_commit="a" * 40,
        report_path=tmp_path / "attempt.json",
    )
    assert rc == 0
    manifest = json.loads((out / certification.MANIFEST).read_text(encoding="utf8"))
    assert manifest["codeCommit"] == "a" * 40
    assert manifest["policy"] == release_policy.POLICY
    assert set(manifest["inputs"]) == set(source_inputs)
    assert all(value.startswith("sha256:") for value in manifest["inputs"].values())
    assert manifest["inputsStable"] is True
    assert manifest["dataset"]["digest"].startswith("sha256:")


def test_canonical_success_produces_a_publishable_full_stamp(tmp_path):
    out = dataset(tmp_path)
    rc = certification.certify(
        out=out,
        source_version="0.3",
        tf_version="9.9.9",
        mode="research-ready",
        gates=canonical_gates(),
        runner=passed,
        input_files=inputs(tmp_path),
        known_defects=zero_defects(),
        code_commit="b" * 40,
        report_path=tmp_path / "attempt.json",
    )
    assert rc == 0
    assert stamp.check(out, require_full=True) is None
