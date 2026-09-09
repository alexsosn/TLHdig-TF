"""RED contract for predecessor-aware release certification (#38)."""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest

PROGRAMS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAMS))

import release_check
from tlhdig import certification, release_policy, stamp


V3_GATES = (
    "corpus-identity",
    "repair-manifest",
    "sign-round-trip",
    "morphology",
    "structure",
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
    "code-tree-stable",
)
V3_INPUTS = ("corpusManifest", "repairManifest", "signrefLock")
V3_DEFECTS = ("knownLossy", "contractAKnown", "knownWordDeficit")


def _delta_module():
    # Import inside tests so the RED run reports the missing implementation as test
    # failures rather than aborting collection before the rest of the suite can run.
    return importlib.import_module("tlhdig.release_delta")


def _tf(body: str, *, extra_meta: tuple[str, ...] = ()) -> str:
    return "@node\n" + "".join(f"@{line}\n" for line in extra_meta) + "\n" + body


def _otext(*, version: str, date: str, sections: str = "docid,collabel,lnno") -> str:
    return (
        "@config\n"
        f"@sectionFeatures={sections}\n"
        "@sectionTypes=document,column,line\n"
        "@fmt:text-orig-plain={sym}{after}\n"
        f"@version={version}\n"
        f"@dateWritten={date}\n"
    )


def _write_version(
    root: Path,
    version: str,
    *,
    main: dict[str, str],
    provenance: dict[str, str] | None = None,
) -> Path:
    out = root / "tf" / version
    prov = root / "tf-provenance" / version
    out.mkdir(parents=True)
    prov.mkdir(parents=True)
    for name, content in main.items():
        (out / name).write_text(content, encoding="utf8")
    for name, content in (provenance or {}).items():
        (prov / name).write_text(content, encoding="utf8")
    return out


def _digest(out: Path) -> str:
    value, _ = stamp.full_digest(out)
    return "sha256:" + value


def _spec(
    path: Path,
    *,
    current: str,
    predecessor: str,
    predecessor_digest: str,
    expected: list[str],
) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "tfVersion": current,
                "predecessorVersion": predecessor,
                "predecessorDigest": predecessor_digest,
                "expectedChanges": expected,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf8",
    )
    return path


def _check(spec: Path, root: Path, current: str):
    module = _delta_module()
    return module.check(spec, root=root, current_version=current)


def _pair(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "root"
    old = _write_version(
        root,
        "1.0.0",
        main={
            "otype.tf": _tf("1\tsign\n"),
            "sym.tf": _tf("1\ta\n"),
            "otext.tf": _otext(version="1.0.0", date="old"),
        },
        provenance={"srcxml.tf": _tf("1\t<a/>\n")},
    )
    new = _write_version(
        root,
        "1.1.0",
        main={
            "otype.tf": _tf("1\tsign\n"),
            "sym.tf": _tf("1\ta\n"),
            "otext.tf": _otext(version="1.1.0", date="new"),
        },
        provenance={"srcxml.tf": _tf("1\t<a/>\n")},
    )
    return root, old, new


def test_current_policy_retains_predecessor_contract_and_historical_v4():
    assert release_policy.POLICY == "release-v6"
    assert "predecessor-delta" in release_policy.REQUIRED_GATES
    assert "sign-language" in release_policy.REQUIRED_GATES
    assert release_policy.REQUIRED_GATES[-1] == "code-tree-stable"
    assert "releaseDelta" in release_policy.REQUIRED_INPUTS
    assert release_policy.DELTA_BASELINE_TF_VERSION == "0.3.0"
    historical_v4 = release_policy.policy_contract("release-v4")
    assert historical_v4 is not None
    assert "predecessor-delta" in historical_v4.required_gates
    assert "releaseDelta" in historical_v4.required_inputs
    assert "sign-language" not in historical_v4.required_gates


def test_future_version_cannot_claim_baseline(tmp_path):
    root, _old, _new = _pair(tmp_path)
    spec = tmp_path / "delta.json"
    spec.write_text(
        json.dumps({"schema": 1, "tfVersion": "1.1.0", "baseline": True}) + "\n",
        encoding="utf8",
    )
    module = _delta_module()
    with pytest.raises(module.DeltaError, match="baseline"):
        module.check(spec, root=root, current_version="1.1.0")


def test_wrong_predecessor_digest_is_rejected(tmp_path):
    root, _old, _new = _pair(tmp_path)
    spec = _spec(
        tmp_path / "delta.json",
        current="1.1.0",
        predecessor="1.0.0",
        predecessor_digest="sha256:" + "0" * 64,
        expected=[],
    )
    module = _delta_module()
    with pytest.raises(module.DeltaError, match="digest"):
        module.check(spec, root=root, current_version="1.1.0")


def test_missing_predecessor_digest_is_rejected(tmp_path):
    root, _old, _new = _pair(tmp_path)
    spec = tmp_path / "delta.json"
    spec.write_text(
        json.dumps(
            {
                "schema": 1,
                "tfVersion": "1.1.0",
                "predecessorVersion": "1.0.0",
                "expectedChanges": [],
            }
        )
        + "\n",
        encoding="utf8",
    )
    module = _delta_module()
    with pytest.raises(module.DeltaError, match="predecessorDigest"):
        module.check(spec, root=root, current_version="1.1.0")


def test_unexpected_changed_feature_is_rejected(tmp_path):
    root, old, new = _pair(tmp_path)
    (new / "sym.tf").write_text(_tf("1\tb\n"), encoding="utf8")
    spec = _spec(
        tmp_path / "delta.json",
        current="1.1.0",
        predecessor="1.0.0",
        predecessor_digest=_digest(old),
        expected=[],
    )
    module = _delta_module()
    with pytest.raises(module.DeltaError, match="main:sym.tf"):
        module.check(spec, root=root, current_version="1.1.0")


def test_declared_change_that_did_not_occur_is_rejected(tmp_path):
    root, old, _new = _pair(tmp_path)
    spec = _spec(
        tmp_path / "delta.json",
        current="1.1.0",
        predecessor="1.0.0",
        predecessor_digest=_digest(old),
        expected=["main:sym.tf"],
    )
    module = _delta_module()
    with pytest.raises(module.DeltaError, match="main:sym.tf"):
        module.check(spec, root=root, current_version="1.1.0")


def test_added_and_removed_features_are_exact_changes(tmp_path):
    root, old, new = _pair(tmp_path)
    (old / "oldonly.tf").write_text(_tf("1\tx\n"), encoding="utf8")
    digest = _digest(old)
    (new / "newonly.tf").write_text(_tf("1\ty\n"), encoding="utf8")
    spec = _spec(
        tmp_path / "delta.json",
        current="1.1.0",
        predecessor="1.0.0",
        predecessor_digest=digest,
        expected=["main:newonly.tf", "main:oldonly.tf"],
    )
    evidence = _check(spec, root, "1.1.0")
    assert evidence["actualChanges"] == ["main:newonly.tf", "main:oldonly.tf"]


def test_provenance_change_is_module_qualified(tmp_path):
    root, old, _new = _pair(tmp_path)
    prov = root / "tf-provenance" / "1.1.0"
    (prov / "srcxml.tf").write_text(_tf("1\t<b/>\n"), encoding="utf8")
    spec = _spec(
        tmp_path / "delta.json",
        current="1.1.0",
        predecessor="1.0.0",
        predecessor_digest=_digest(old),
        expected=["provenance:srcxml.tf"],
    )
    evidence = _check(spec, root, "1.1.0")
    assert evidence["actualChanges"] == ["provenance:srcxml.tf"]


def test_node_order_change_in_otype_is_detected(tmp_path):
    root, old, new = _pair(tmp_path)
    (old / "otype.tf").write_text(_tf("1\tsign\n2\tword\n"), encoding="utf8")
    digest = _digest(old)
    (new / "otype.tf").write_text(_tf("1\tword\n2\tsign\n"), encoding="utf8")
    spec = _spec(
        tmp_path / "delta.json",
        current="1.1.0",
        predecessor="1.0.0",
        predecessor_digest=digest,
        expected=["main:otype.tf"],
    )
    evidence = _check(spec, root, "1.1.0")
    assert evidence["actualChanges"] == ["main:otype.tf"]


def test_otext_semantic_config_change_is_detected(tmp_path):
    root, old, new = _pair(tmp_path)
    (new / "otext.tf").write_text(
        _otext(version="1.1.0", date="new", sections="record,collabel,lnno"),
        encoding="utf8",
    )
    spec = _spec(
        tmp_path / "delta.json",
        current="1.1.0",
        predecessor="1.0.0",
        predecessor_digest=_digest(old),
        expected=["main:otext.tf"],
    )
    evidence = _check(spec, root, "1.1.0")
    assert evidence["actualChanges"] == ["main:otext.tf"]


def test_otext_only_version_and_date_changes_do_not_count(tmp_path):
    root, old, _new = _pair(tmp_path)
    spec = _spec(
        tmp_path / "delta.json",
        current="1.1.0",
        predecessor="1.0.0",
        predecessor_digest=_digest(old),
        expected=[],
    )
    evidence = _check(spec, root, "1.1.0")
    assert evidence["actualChanges"] == []


def _historical_v3_manifest(out: Path) -> Path:
    digest, features = stamp.full_digest(out)
    manifest = out / stamp.CERTIFICATION
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "policy": "release-v3",
                "mode": "regression-valid",
                "sourceVersion": "0.3",
                "tfVersion": "9.9.9",
                "codeCommit": "a" * 40,
                "dataset": {
                    "algorithm": release_policy.ARTIFACT_DIGEST_ALGORITHM,
                    "digest": "sha256:" + digest,
                    "features": features,
                },
                "inputs": {name: "sha256:" + hashlib.sha256(name.encode()).hexdigest() for name in V3_INPUTS},
                "knownDefects": {name: 0 for name in V3_DEFECTS},
                "requiredGates": list(V3_GATES),
                "gates": [
                    {"name": name, "command": [name], "status": "passed", "returncode": 0}
                    for name in V3_GATES
                ],
                "artifactStable": True,
                "inputsStable": True,
                "success": True,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
    return manifest


def _cert_dataset(tmp_path: Path) -> Path:
    root = tmp_path / "cert-root"
    out = root / "tf" / "9.9.9"
    prov = root / "tf-provenance" / "9.9.9"
    out.mkdir(parents=True)
    prov.mkdir(parents=True)
    (out / "otype.tf").write_text(_tf("1\tsign\n"), encoding="utf8")
    (prov / "srcxml.tf").write_text(_tf("1\t<a/>\n"), encoding="utf8")
    return out


def test_historical_release_v3_full_stamp_still_verifies_under_v4(monkeypatch, tmp_path):
    out = _cert_dataset(tmp_path)
    manifest = _historical_v3_manifest(out)
    stamp.write(
        out,
        "0.3",
        "9.9.9",
        certification=manifest,
        mode="regression-valid",
        commit="a" * 40,
    )
    monkeypatch.setattr(release_policy, "POLICY", "release-v4")
    monkeypatch.setattr(release_policy, "REQUIRED_GATES", V3_GATES + ("predecessor-delta",))
    monkeypatch.setattr(release_policy, "REQUIRED_INPUTS", V3_INPUTS + ("releaseDelta",))
    assert stamp.check(out, require_full=True) is None


def test_unknown_full_certification_policy_is_rejected(tmp_path):
    out = _cert_dataset(tmp_path)
    manifest = _historical_v3_manifest(out)
    payload = json.loads(manifest.read_text(encoding="utf8"))
    payload["policy"] = "release-v999"
    manifest.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf8")
    stamp.write(
        out,
        "0.3",
        "9.9.9",
        certification=manifest,
        mode="regression-valid",
        commit="a" * 40,
    )
    problem = stamp.check(out, require_full=True)
    assert problem and "unsupported" in problem.lower()


def test_v4_full_stamp_requires_structured_predecessor_evidence(monkeypatch, tmp_path):
    out = _cert_dataset(tmp_path)
    manifest = _historical_v3_manifest(out)
    payload = json.loads(manifest.read_text(encoding="utf8"))
    v4_gates = V3_GATES[:-1] + ("predecessor-delta", "code-tree-stable")
    payload["policy"] = "release-v4"
    payload["requiredGates"] = list(v4_gates)
    payload["gates"] = [
        {"name": name, "command": [name], "status": "passed", "returncode": 0}
        for name in v4_gates
    ]
    payload["inputs"]["releaseDelta"] = "sha256:" + "e" * 64
    manifest.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf8")
    stamp.write(
        out,
        "0.3",
        "9.9.9",
        certification=manifest,
        mode="regression-valid",
        commit="a" * 40,
    )
    monkeypatch.setattr(release_policy, "POLICY", "release-v4")
    monkeypatch.setattr(release_policy, "REQUIRED_GATES", v4_gates)
    monkeypatch.setattr(release_policy, "REQUIRED_INPUTS", V3_INPUTS + ("releaseDelta",))
    problem = stamp.check(out, require_full=True)
    assert problem and "predecessor" in problem.lower() and "evidence" in problem.lower()


def test_gate_outcome_evidence_is_bound_into_successful_manifest(tmp_path):
    out = _cert_dataset(tmp_path)
    source_inputs = {}
    for name in release_policy.REQUIRED_INPUTS:
        path = tmp_path / f"{name}.txt"
        path.write_text(name + "\n", encoding="utf8")
        source_inputs[name] = path

    def runner(gate):
        return certification.GateOutcome(
            "passed",
            0,
            evidence={"baseline": True, "actualChanges": []} if gate.name == "one" else None,
        )

    rc = certification.certify(
        out=out,
        source_version="0.3",
        tf_version="9.9.9",
        mode="regression-valid",
        gates=[certification.Gate("one", ("one",))],
        runner=runner,
        input_files=source_inputs,
        known_defects={name: 0 for name in release_policy.FIDELITY_BASELINES},
        code_commit="a" * 40,
        report_path=tmp_path / "attempt.json",
    )
    assert rc == 0
    payload = json.loads((out / certification.MANIFEST).read_text(encoding="utf8"))
    assert payload["gates"][0]["evidence"] == {"baseline": True, "actualChanges": []}


def test_canonical_release_check_has_hard_predecessor_gate_before_tree_stability():
    names = tuple(gate.name for gate in release_check.GATES)
    assert names[-2:] == ("predecessor-delta", "code-tree-stable")
    assert "releaseDelta" in release_check.release_inputs()


def test_canonical_predecessor_gate_failure_is_hard(monkeypatch, tmp_path):
    module = _delta_module()
    monkeypatch.setattr(release_check, "ROOT", tmp_path)
    monkeypatch.setattr(release_check, "TF_VERSION", "1.1.0")
    monkeypatch.setattr(release_check, "PROGRAMS", tmp_path)
    (tmp_path / "release-delta.json").write_text("{}\n", encoding="utf8")

    def fail(*_args, **_kwargs):
        raise module.DeltaError("wrong predecessor")

    monkeypatch.setattr(module, "check", fail)
    outcome = release_check.run_gate(
        certification.Gate("predecessor-delta", ("internal", "release-delta"))
    )
    assert outcome.status == "failed"
    assert outcome.returncode != 0
    assert outcome.evidence and "wrong predecessor" in outcome.evidence["error"]
