"""Adversarial RED for supplemental Text-Fabric config features (#38)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROGRAMS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAMS))

from tlhdig import release_delta, stamp


def _node() -> str:
    return "@node\n@valueType=str\n\n1\tsign\n"


def _config(*, version: str, date: str, fmt: str = "{sym}") -> str:
    return (
        "@config\n"
        f"@fmt:extra={fmt}\n"
        f"@version={version}\n"
        f"@dateWritten={date}\n"
    )


def _pair(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "root"
    old = root / "tf" / "1.0.0"
    new = root / "tf" / "1.1.0"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    (old / "otype.tf").write_text(_node(), encoding="utf8")
    (new / "otype.tf").write_text(_node(), encoding="utf8")
    return root, old, new


def _spec(path: Path, old: Path, expected: list[str]) -> Path:
    digest, _ = stamp.full_digest(old)
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "tfVersion": "1.1.0",
                "predecessorVersion": "1.0.0",
                "predecessorDigest": "sha256:" + digest,
                "expectedChanges": expected,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
    return path


def test_supplemental_config_ignores_only_release_local_metadata(tmp_path):
    root, old, new = _pair(tmp_path)
    (old / "otext@extra.tf").write_text(
        _config(version="1.0.0", date="old"), encoding="utf8"
    )
    # Pin the complete predecessor after adding the supplemental config feature.
    spec = _spec(tmp_path / "delta.json", old, [])
    (new / "otext@extra.tf").write_text(
        _config(version="1.1.0", date="new"), encoding="utf8"
    )
    evidence = release_delta.check(spec, root=root, current_version="1.1.0")
    assert evidence["actualChanges"] == []


def test_supplemental_config_semantic_change_is_exact_delta(tmp_path):
    root, old, new = _pair(tmp_path)
    (old / "otext@extra.tf").write_text(
        _config(version="1.0.0", date="old", fmt="{sym}"), encoding="utf8"
    )
    spec = _spec(tmp_path / "delta.json", old, ["main:otext@extra.tf"])
    (new / "otext@extra.tf").write_text(
        _config(version="1.1.0", date="new", fmt="{sym}{after}"), encoding="utf8"
    )
    evidence = release_delta.check(spec, root=root, current_version="1.1.0")
    assert evidence["actualChanges"] == ["main:otext@extra.tf"]
