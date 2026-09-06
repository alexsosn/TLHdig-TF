"""The BUILD-COMPLETE stamp and its full release-certification binding."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import stamp

REQUIRED_GATES = (
    "corpus-identity",
    "repair-manifest",
    "sign-round-trip",
    "morphology",
    "structure",
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


def dataset(tmp_path: Path, body: str = "1\ta\n") -> Path:
    d = tmp_path / "tf"
    d.mkdir()
    (d / "otype.tf").write_text("@node\n\n1\tsign\n", encoding="utf8")
    (d / "sym.tf").write_text("@node\n\n" + body, encoding="utf8")
    return d


def full_manifest(d: Path) -> Path:
    digest, features = stamp.digest(d)
    path = d / stamp.CERTIFICATION
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "policy": "release-v1",
                "mode": "regression-valid",
                "sourceVersion": "0.3",
                "tfVersion": "0.1.0",
                "codeCommit": "a" * 40,
                "dataset": {"digest": f"sha256:{digest}", "features": features},
                "inputs": {
                    "corpusManifest": "sha256:" + "b" * 64,
                    "repairManifest": "sha256:" + "c" * 64,
                    "signrefLock": "sha256:" + "d" * 64,
                },
                "knownDefects": {
                    "knownLossy": 1,
                    "contractAKnown": 2,
                    "knownWordDeficit": 3,
                },
                "requiredGates": list(REQUIRED_GATES),
                "gates": [
                    {
                        "name": name,
                        "command": [name],
                        "status": "passed",
                        "returncode": 0,
                    }
                    for name in REQUIRED_GATES
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
    return path


def restamp(d: Path, manifest: Path, *, mode: str = "regression-valid") -> None:
    stamp.write(
        d,
        "0.3",
        "0.1.0",
        certification=manifest,
        mode=mode,
        commit="a" * 40,
    )


def test_missing_stamp_is_a_problem(tmp_path):
    d = dataset(tmp_path)
    assert "missing" in stamp.check(d)


def test_fresh_legacy_stamp_verifies_for_historical_artifact(tmp_path):
    d = dataset(tmp_path)
    stamp.write(d, "0.3", "0.1.0")
    assert stamp.check(d) is None


def test_legacy_stamp_is_refused_when_full_certification_is_required(tmp_path):
    d = dataset(tmp_path)
    stamp.write(d, "0.3", "0.1.0")
    problem = stamp.check(d, require_full=True)
    assert problem and "legacy census-only" in problem


def test_full_stamp_verifies(tmp_path):
    d = dataset(tmp_path)
    manifest = full_manifest(d)
    restamp(d, manifest)
    assert stamp.check(d, require_full=True) is None


def test_tampered_certification_manifest_invalidates_full_stamp(tmp_path):
    d = dataset(tmp_path)
    manifest = full_manifest(d)
    restamp(d, manifest)
    manifest.write_text(manifest.read_text(encoding="utf8") + " ", encoding="utf8")
    problem = stamp.check(d, require_full=True)
    assert problem and "does not match RELEASE-CERTIFICATION.json" in problem


def test_full_stamp_rejects_manifest_with_required_gate_skip(tmp_path):
    d = dataset(tmp_path)
    manifest = full_manifest(d)
    payload = json.loads(manifest.read_text(encoding="utf8"))
    payload["gates"][0]["status"] = "skipped-unavailable"
    manifest.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf8")
    restamp(d, manifest)
    problem = stamp.check(d, require_full=True)
    assert problem and "did not pass" in problem


def test_full_stamp_rejects_self_declared_reduced_required_gate_set(tmp_path):
    d = dataset(tmp_path)
    manifest = full_manifest(d)
    payload = json.loads(manifest.read_text(encoding="utf8"))
    payload["requiredGates"] = ["census"]
    payload["gates"] = [
        {"name": "census", "command": ["census"], "status": "passed", "returncode": 0}
    ]
    manifest.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf8")
    restamp(d, manifest)
    problem = stamp.check(d, require_full=True)
    assert problem and "release gate policy" in problem


def test_full_stamp_rejects_unstable_release_inputs(tmp_path):
    d = dataset(tmp_path)
    manifest = full_manifest(d)
    payload = json.loads(manifest.read_text(encoding="utf8"))
    payload["inputsStable"] = False
    manifest.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf8")
    restamp(d, manifest)
    problem = stamp.check(d, require_full=True)
    assert problem and "release inputs" in problem


def test_research_ready_stamp_rejects_nonzero_known_defects(tmp_path):
    d = dataset(tmp_path)
    manifest = full_manifest(d)
    payload = json.loads(manifest.read_text(encoding="utf8"))
    payload["mode"] = "research-ready"
    manifest.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf8")
    restamp(d, manifest, mode="research-ready")
    problem = stamp.check(d, require_full=True)
    assert problem and "research-ready" in problem


def test_stamp_does_not_certify_a_later_rebuild(tmp_path):
    """Verify build A, rebuild as B: neither legacy nor full stamp may survive."""
    d = dataset(tmp_path, "1\ta\n")
    stamp.write(d, "0.3", "0.1.0")
    (d / "sym.tf").write_text("@node\n\n1\tCHANGED\n", encoding="utf8")
    problem = stamp.check(d)
    assert problem and "rebuilt after it was verified" in problem


def test_added_feature_file_invalidates_the_stamp(tmp_path):
    d = dataset(tmp_path)
    stamp.write(d, "0.3", "0.1.0")
    (d / "extra.tf").write_text("@node\n\n1\tx\n", encoding="utf8")
    assert stamp.check(d) is not None


def test_legacy_stamp_without_a_digest_is_refused(tmp_path):
    d = dataset(tmp_path)
    (d / stamp.STAMP).write_text("sourceVersion=0.3\ntfVersion=0.1.0\n", encoding="utf8")
    assert "predates content binding" in stamp.check(d)
