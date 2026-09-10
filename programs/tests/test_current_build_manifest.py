"""Current-build manifest contract for the mutable pre-alpha artifact (#116)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import build_manifest


def dataset(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    main = root / "tf" / "9.9.9"
    prov = root / "tf-provenance" / "9.9.9"
    main.mkdir(parents=True)
    prov.mkdir(parents=True)
    (main / "otype.tf").write_text("@node\n\n1\tsign\n", encoding="utf8")
    (main / "LICENSE").write_text("license\n", encoding="utf8")
    (prov / "srcxml.tf").write_text("@node\n\n1\t<w>a</w>\n", encoding="utf8")
    return main, prov


def inputs(tmp_path: Path) -> dict[str, Path]:
    result = {}
    for name in ("corpusManifest", "repairManifest", "exclusions", "signrefLock", "dependencies"):
        path = tmp_path / f"{name}.txt"
        path.write_text(name + "\n", encoding="utf8")
        result[name] = path
    return result


def write_valid(tmp_path: Path):
    main, prov = dataset(tmp_path)
    source_inputs = inputs(tmp_path)
    path = main / build_manifest.MANIFEST
    build_manifest.write_manifest(
        path,
        source_version="0.3",
        tf_version="9.9.9",
        code_commit="a" * 40,
        main_dir=main,
        provenance_dir=prov,
        input_files=source_inputs,
        gate_names=("one", "two"),
        root=main.parents[1],
    )
    return main, prov, source_inputs, path


def verify(main, prov, source_inputs, path):
    return build_manifest.verify_manifest(
        path,
        source_version="0.3",
        tf_version="9.9.9",
        main_dir=main,
        provenance_dir=prov,
        input_files=source_inputs,
        gate_names=("one", "two"),
        root=main.parents[1],
    )


def test_manifest_is_direct_nonrecursive_current_build_identity(tmp_path):
    main, prov, source_inputs, path = write_valid(tmp_path)
    payload = json.loads(path.read_text(encoding="utf8"))
    assert payload["schema"] == 1
    assert payload["sourceVersion"] == "0.3"
    assert payload["tfVersion"] == "9.9.9"
    assert payload["codeCommit"] == "a" * 40
    assert payload["paths"] == {
        "main": "tf/9.9.9",
        "provenance": "tf-provenance/9.9.9",
    }
    assert payload["outputs"]["algorithm"] == "tlhdig-current-tree-v1"
    assert set(payload["outputs"]["files"]) == {
        "main:LICENSE",
        "main:otype.tf",
        "provenance:srcxml.tf",
    }
    assert build_manifest.MANIFEST not in "\n".join(payload["outputs"]["files"])
    assert payload["validation"] == {"success": True, "gates": ["one", "two"]}
    assert verify(main, prov, source_inputs, path) is None


def test_output_identity_binds_module_membership(tmp_path):
    main, prov = dataset(tmp_path)
    before = build_manifest.output_identity(main, prov)
    (main / "otype.tf").replace(prov / "otype.tf")
    after = build_manifest.output_identity(main, prov)
    assert before["digest"] != after["digest"]
    assert "main:otype.tf" in before["files"]
    assert "provenance:otype.tf" in after["files"]


def test_manifest_verifier_rejects_changed_extra_and_missing_output(tmp_path):
    main, prov, source_inputs, path = write_valid(tmp_path)

    (main / "otype.tf").write_text("CHANGED\n", encoding="utf8")
    assert "output" in verify(main, prov, source_inputs, path).lower()
    (main / "otype.tf").write_text("@node\n\n1\tsign\n", encoding="utf8")
    assert verify(main, prov, source_inputs, path) is None

    extra = main / "unexpected.txt"
    extra.write_text("extra\n", encoding="utf8")
    assert "output" in verify(main, prov, source_inputs, path).lower()
    extra.unlink()

    (prov / "srcxml.tf").unlink()
    assert "output" in verify(main, prov, source_inputs, path).lower()


def test_manifest_verifier_rejects_changed_input(tmp_path):
    main, prov, source_inputs, path = write_valid(tmp_path)
    source_inputs["repairManifest"].write_text("changed\n", encoding="utf8")
    assert "input" in verify(main, prov, source_inputs, path).lower()


def test_manifest_verifier_rejects_changed_gate_contract(tmp_path):
    main, prov, source_inputs, path = write_valid(tmp_path)
    problem = build_manifest.verify_manifest(
        path,
        source_version="0.3",
        tf_version="9.9.9",
        main_dir=main,
        provenance_dir=prov,
        input_files=source_inputs,
        gate_names=("one",),
        root=main.parents[1],
    )
    assert problem and "gate" in problem.lower()


def test_manifest_verifier_does_not_require_producing_commit_to_equal_later_head(tmp_path):
    main, prov, source_inputs, path = write_valid(tmp_path)
    payload = json.loads(path.read_text(encoding="utf8"))
    assert payload["codeCommit"] == "a" * 40
    # Verification deliberately has no current-HEAD argument. Committing the generated
    # manifest creates a later commit; explicit inputs/outputs are the drift contract.
    assert verify(main, prov, source_inputs, path) is None


def test_output_inventory_ignores_only_manifest_and_tf_cache(tmp_path):
    main, prov = dataset(tmp_path)
    (main / build_manifest.MANIFEST).write_text("{}\n", encoding="utf8")
    cache = main / ".tf"
    cache.mkdir()
    (cache / "otype.tfx").write_bytes(b"machine cache")
    identity = build_manifest.output_identity(main, prov)
    assert build_manifest.MANIFEST not in "\n".join(identity["files"])
    assert not any(".tf/" in name for name in identity["files"])


def test_output_inventory_rejects_symlink(tmp_path):
    main, prov = dataset(tmp_path)
    target = tmp_path / "outside.txt"
    target.write_text("outside\n", encoding="utf8")
    try:
        (main / "escape.tf").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")
    with pytest.raises(build_manifest.ManifestError, match="symlink"):
        build_manifest.output_identity(main, prov)
