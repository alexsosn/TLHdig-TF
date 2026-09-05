"""Release certification orchestrates the gates that BUILD-COMPLETE claims passed."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import certification, stamp


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
    for name in ("corpusManifest", "repairManifest", "signrefLock"):
        path = tmp_path / f"{name}.txt"
        path.write_text(name + "\n", encoding="utf8")
        result[name] = path
    return result


def passed(_gate):
    return certification.GateOutcome("passed", 0)


def test_regression_valid_can_certify_declared_nonzero_known_defects(tmp_path):
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
    assert manifest["gates"] == [
        {"name": "one", "command": ["one"], "status": "passed", "returncode": 0}
    ]
    assert stamp.check(out, require_full=True) is None


def test_research_ready_refuses_the_same_nonzero_known_defects(tmp_path):
    out = dataset(tmp_path)
    defects = {"knownLossy": 1, "contractAKnown": 0, "knownWordDeficit": 0}
    rc = certification.certify(
        out=out,
        source_version="0.3",
        tf_version="9.9.9",
        mode="research-ready",
        gates=[certification.Gate("one", ("one",))],
        runner=passed,
        input_files=inputs(tmp_path),
        known_defects=defects,
        code_commit="b" * 40,
        report_path=tmp_path / "attempt.json",
    )
    assert rc == 1
    assert not (out / stamp.STAMP).exists()
    assert not (out / certification.MANIFEST).exists()


def test_required_gate_failure_leaves_no_stamp(tmp_path):
    out = dataset(tmp_path)
    stamp.write(out, "0.3", "9.9.9")  # simulate stale certification from an older run

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
        known_defects={"knownLossy": 0, "contractAKnown": 0, "knownWordDeficit": 0},
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
        known_defects={"knownLossy": 0, "contractAKnown": 0, "knownWordDeficit": 0},
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
        known_defects={"knownLossy": 0, "contractAKnown": 0, "knownWordDeficit": 0},
        code_commit="e" * 40,
        report_path=tmp_path / "attempt.json",
    )
    assert rc == 1
    assert not (out / stamp.STAMP).exists()
    attempt = json.loads((tmp_path / "attempt.json").read_text(encoding="utf8"))
    assert attempt["artifactStable"] is False


def test_successful_certification_records_input_identities(tmp_path):
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
        known_defects={"knownLossy": 0, "contractAKnown": 0, "knownWordDeficit": 0},
        code_commit="f" * 40,
        report_path=tmp_path / "attempt.json",
    )
    assert rc == 0
    manifest = json.loads((out / certification.MANIFEST).read_text(encoding="utf8"))
    assert manifest["codeCommit"] == "f" * 40
    assert set(manifest["inputs"]) == set(source_inputs)
    assert all(value.startswith("sha256:") for value in manifest["inputs"].values())
    assert manifest["dataset"]["digest"].startswith("sha256:")
    assert stamp.check(out, require_full=True) is None
