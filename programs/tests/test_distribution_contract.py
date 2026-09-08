from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "programs"))

import check_distribution


DIGEST = "sha256:" + "a" * 64


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf8")


def _valid_root(tmp_path: Path) -> Path:
    root = tmp_path
    version = "9.9.9"
    source = "7.7"
    policy = "release-v99"
    for feature in ("otype", "oslots", "otext", "sym", "lemma", "morph"):
        _write(root / "tf" / version / f"{feature}.tf", "@node\n\n")
    for feature in ("srcxml", "src_span"):
        _write(root / "tf-provenance" / version / f"{feature}.tf", "@node\n\n")
    _write(root / "essential", "otype oslots otext sym lemma morph\n")
    _write(
        root / "app" / "config.yaml",
        yaml.safe_dump(
            {
                "provenanceSpec": {
                    "org": "alexsosn",
                    "repo": "TLHdig-TF",
                    "relative": "/tf",
                    "version": version,
                }
            },
            sort_keys=False,
        ),
    )
    cert = {
        "success": True,
        "sourceVersion": source,
        "tfVersion": version,
        "policy": policy,
        "dataset": {"digest": DIGEST},
    }
    _write(
        root / "tf" / version / "RELEASE-CERTIFICATION.json",
        json.dumps(cert),
    )
    meta = {
        "sourceVersion": source,
        "tfVersion": version,
        "releaseTag": f"tlhdig-{source}_tf-{version}",
        "certificationPolicy": policy,
        "releaseCommit": "0123456789abcdef",
        "main": {
            "relative": "tf",
            "version": version,
            "artifactDigest": DIGEST,
            "asset": f"tf-{version}.zip",
        },
        "provenance": {
            "relative": "tf-provenance",
            "version": version,
            "artifactDigest": "sha256:" + "b" * 64,
            "asset": f"tf-provenance-{version}.zip",
            "optional": True,
        },
        "app": {"completeAsset": "complete.zip"},
        "essential": {"manifest": "essential"},
    }
    _write(root / "distribution.json", json.dumps(meta))
    return root


def _check(root: Path):
    return check_distribution.check_distribution(
        root,
        expected_source="7.7",
        expected_tf="9.9.9",
        expected_policy="release-v99",
    )


def test_checker_accepts_one_coherent_distribution_identity(tmp_path):
    root = _valid_root(tmp_path)
    assert _check(root) == []


def test_checker_rejects_tag_and_asset_version_drift(tmp_path):
    root = _valid_root(tmp_path)
    path = root / "distribution.json"
    meta = json.loads(path.read_text())
    meta["releaseTag"] = "tlhdig-7.7_tf-1.2.3"
    meta["main"]["asset"] = "tf-1.2.3.zip"
    path.write_text(json.dumps(meta), encoding="utf8")
    problems = _check(root)
    assert any("releaseTag does not encode" in p for p in problems)
    assert any("main asset filename" in p for p in problems)


def test_checker_rejects_uncertified_or_wrong_digest(tmp_path):
    root = _valid_root(tmp_path)
    path = root / "distribution.json"
    meta = json.loads(path.read_text())
    meta["main"]["artifactDigest"] = "sha256:" + "c" * 64
    path.write_text(json.dumps(meta), encoding="utf8")
    assert any("does not match release certification" in p for p in _check(root))


def test_checker_rejects_provenance_as_default_dependency(tmp_path):
    root = _valid_root(tmp_path)
    app_path = root / "app" / "config.yaml"
    app = yaml.safe_load(app_path.read_text())
    app["provenanceSpec"]["moduleSpecs"] = [
        {"org": "alexsosn", "repo": "TLHdig-TF", "relative": "/tf-provenance"}
    ]
    app_path.write_text(yaml.safe_dump(app), encoding="utf8")
    assert any("implicit dependency" in p for p in _check(root))


def test_checker_rejects_bad_essential_features_and_provenance_leak(tmp_path):
    root = _valid_root(tmp_path)
    (root / "essential").write_text(
        "otype oslots otext sym imaginary srcxml srcxml\n", encoding="utf8"
    )
    problems = _check(root)
    assert any("missing main features" in p and "imaginary" in p for p in problems)
    assert any("provenance-only" in p and "srcxml" in p for p in problems)
    assert any("duplicate" in p for p in problems)


def test_checker_rejects_mismatched_provenance_version(tmp_path):
    root = _valid_root(tmp_path)
    path = root / "distribution.json"
    meta = json.loads(path.read_text())
    meta["provenance"]["version"] = "9.9.8"
    meta["provenance"]["asset"] = "tf-provenance-9.9.8.zip"
    path.write_text(json.dumps(meta), encoding="utf8")
    problems = _check(root)
    assert any("provenance distribution path/version" in p for p in problems)
    assert any("provenance asset filename" in p for p in problems)


def test_agora_projection_rejects_floating_historical_path(tmp_path):
    root = _valid_root(tmp_path)
    meta = json.loads((root / "distribution.json").read_text())
    problems = check_distribution.validate_agora_projection(
        meta,
        {
            "upstream": {
                "repository": "alexsosn/TLHdig-TF",
                "tf_path": "tf/0.1.0",
                "ref": "main",
            }
        },
    )
    assert any("tf_path" in p for p in problems)
    assert any("release tag or exact release commit" in p for p in problems)


def test_repository_distribution_contract_is_green():
    # RED gate for #47. Production implementation must create the canonical metadata
    # and essential manifest only after this failure is demonstrated in hosted CI.
    problems = check_distribution.check_distribution(ROOT)
    assert problems == [], "\n".join(problems)
