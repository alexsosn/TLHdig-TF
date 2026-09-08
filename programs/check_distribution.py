#!/usr/bin/env python3
"""Fail-closed validation of the supported consumer distribution contract.

This checker is intentionally local/deterministic. Networked GitHub Release and Agora
integration checks consume the same metadata in separate hosted tests; ordinary CI must
not become dependent on live APIs.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

PROGRAMS = Path(__file__).resolve().parent
ROOT = PROGRAMS.parent
sys.path.insert(0, str(PROGRAMS))

from tlhdig import SOURCE_VERSION, TF_VERSION
from tlhdig.release_policy import POLICY

TAG_RE = re.compile(r"^tlhdig-(?P<source>[^_]+)_tf-(?P<tf>\d+\.\d+\.\d+)$")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _load_json(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, f"missing {path.name}"
    try:
        value = json.loads(path.read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid {path.name}: {exc}"
    if not isinstance(value, dict):
        return None, f"invalid {path.name}: top level must be an object"
    return value, None


def _feature_names(root: Path, relative: str, version: str) -> set[str]:
    directory = root / relative / version
    if not directory.is_dir():
        return set()
    return {p.stem for p in directory.glob("*.tf") if p.is_file()}


def _load_app(root: Path) -> tuple[dict | None, str | None]:
    path = root / "app" / "config.yaml"
    if not path.is_file():
        return None, "missing app/config.yaml"
    try:
        value = yaml.safe_load(path.read_text(encoding="utf8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, f"invalid app/config.yaml: {exc}"
    if not isinstance(value, dict):
        return None, "invalid app/config.yaml: top level must be a mapping"
    return value, None


def _asset_version(name: object, prefix: str) -> str | None:
    if not isinstance(name, str):
        return None
    match = re.fullmatch(re.escape(prefix) + r"-(\d+\.\d+\.\d+)\.zip", name)
    return match.group(1) if match else None


def _essential_tokens(path: Path) -> list[str]:
    if not path.is_file():
        return []
    tokens: list[str] = []
    for raw in path.read_text(encoding="utf8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            tokens.extend(line.split())
    return tokens


def validate_agora_projection(meta: dict, agora: dict) -> list[str]:
    """Validate an Agora-side projection without importing Agora implementation code."""
    problems: list[str] = []
    tf_version = meta.get("tfVersion")
    tag = meta.get("releaseTag")
    upstream = agora.get("upstream") if isinstance(agora, dict) else None
    if not isinstance(upstream, dict):
        return ["Agora projection has no upstream mapping"]
    tf_path = upstream.get("tf_path")
    ref = upstream.get("ref")
    if tf_path != f"tf/{tf_version}":
        problems.append(f"Agora tf_path {tf_path!r} != 'tf/{tf_version}'")
    if ref not in {tag, meta.get("releaseCommit")}:
        problems.append("Agora ref is not the release tag or exact release commit")
    return problems


def check_distribution(
    root: Path = ROOT,
    *,
    expected_source: str = SOURCE_VERSION,
    expected_tf: str = TF_VERSION,
    expected_policy: str = POLICY,
) -> list[str]:
    root = Path(root)
    problems: list[str] = []

    meta, error = _load_json(root / "distribution.json")
    if error:
        return [error]
    assert meta is not None

    source_version = meta.get("sourceVersion")
    tf_version = meta.get("tfVersion")
    release_tag = meta.get("releaseTag")
    policy = meta.get("certificationPolicy")

    if source_version != expected_source:
        problems.append(f"sourceVersion {source_version!r} != {expected_source!r}")
    if tf_version != expected_tf:
        problems.append(f"tfVersion {tf_version!r} != {expected_tf!r}")
    if policy != expected_policy:
        problems.append(f"certificationPolicy {policy!r} != {expected_policy!r}")

    tag_match = TAG_RE.fullmatch(release_tag) if isinstance(release_tag, str) else None
    if tag_match is None:
        problems.append(f"invalid releaseTag {release_tag!r}")
    elif tag_match.group("source") != str(source_version) or tag_match.group("tf") != str(tf_version):
        problems.append("releaseTag does not encode sourceVersion/tfVersion")

    main = meta.get("main")
    provenance = meta.get("provenance")
    app_meta = meta.get("app")
    essential_meta = meta.get("essential")
    if not isinstance(main, dict):
        problems.append("missing main distribution mapping")
        main = {}
    if not isinstance(provenance, dict):
        problems.append("missing provenance distribution mapping")
        provenance = {}
    if not isinstance(app_meta, dict):
        problems.append("missing app distribution mapping")
        app_meta = {}
    if not isinstance(essential_meta, dict):
        problems.append("missing essential distribution mapping")
        essential_meta = {}

    if main.get("relative") != "tf" or main.get("version") != tf_version:
        problems.append("main distribution path/version does not match tfVersion")
    if _asset_version(main.get("asset"), "tf") != tf_version:
        problems.append("main asset filename does not encode tfVersion")
    if not SHA256_RE.fullmatch(main.get("artifactDigest", "") if isinstance(main.get("artifactDigest"), str) else ""):
        problems.append("main artifactDigest is missing or not sha256")

    if provenance.get("relative") != "tf-provenance" or provenance.get("version") != tf_version:
        problems.append("provenance distribution path/version does not match tfVersion")
    if provenance.get("optional") is not True:
        problems.append("provenance must be explicitly optional")
    if _asset_version(provenance.get("asset"), "tf-provenance") != tf_version:
        problems.append("provenance asset filename does not encode tfVersion")
    if not SHA256_RE.fullmatch(
        provenance.get("artifactDigest", "") if isinstance(provenance.get("artifactDigest"), str) else ""
    ):
        problems.append("provenance artifactDigest is missing or not sha256")

    if app_meta.get("completeAsset") != "complete.zip":
        problems.append("app complete asset must be complete.zip")

    app, app_error = _load_app(root)
    if app_error:
        problems.append(app_error)
    else:
        assert app is not None
        prov_spec = app.get("provenanceSpec")
        if not isinstance(prov_spec, dict) or prov_spec.get("version") != tf_version:
            problems.append("app provenanceSpec.version does not match tfVersion")
        if "tf-provenance" in json.dumps(app, sort_keys=True):
            problems.append("app config makes or advertises tf-provenance as an implicit dependency")

    cert_path = root / "tf" / str(tf_version) / "RELEASE-CERTIFICATION.json"
    cert, cert_error = _load_json(cert_path)
    if cert_error:
        problems.append(f"missing/invalid certification for tf/{tf_version}: {cert_error}")
    else:
        assert cert is not None
        if cert.get("success") is not True or cert.get("tfVersion") != tf_version:
            problems.append("release certification does not certify tfVersion successfully")
        if cert.get("sourceVersion") != source_version:
            problems.append("release certification sourceVersion mismatch")
        if cert.get("policy") != policy:
            problems.append("release certification policy mismatch")
        dataset = cert.get("dataset")
        cert_digest = dataset.get("digest") if isinstance(dataset, dict) else None
        if main.get("artifactDigest") != cert_digest:
            problems.append("main artifactDigest does not match release certification")

    manifest_name = essential_meta.get("manifest")
    if manifest_name != "essential":
        problems.append("essential manifest must be named 'essential'")
    essential_path = root / str(manifest_name) if isinstance(manifest_name, str) else root / "essential"
    tokens = _essential_tokens(essential_path)
    if not tokens:
        problems.append("essential manifest is missing or empty")
    else:
        main_features = _feature_names(root, "tf", str(tf_version))
        provenance_features = _feature_names(root, "tf-provenance", str(tf_version)) - main_features
        unknown = sorted(set(tokens) - main_features)
        if unknown:
            problems.append("essential names missing main features: " + ", ".join(unknown))
        leaked = sorted(set(tokens) & provenance_features)
        if leaked:
            problems.append("essential includes provenance-only features: " + ", ".join(leaked))
        if len(tokens) != len(set(tokens)):
            problems.append("essential contains duplicate feature names")
        for required in ("otype", "oslots", "otext"):
            if required not in tokens:
                problems.append(f"essential omits required structural feature {required}")

    return problems


def main() -> int:
    problems = check_distribution()
    if problems:
        for problem in problems:
            print(f"distribution: ERROR: {problem}")
        return 1
    print(f"distribution contract verified for TLHdig-TF {TF_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
