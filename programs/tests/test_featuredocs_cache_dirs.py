"""Regression: generated feature docs must ignore TF runtime cache directories."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import featuredocs


def _write_tf(path: Path, header: str) -> None:
    path.write_text(header.rstrip("\n") + "\n\n1\tx\n", encoding="utf8")


def test_discover_features_ignores_tf_named_runtime_cache_directories(tmp_path):
    core = tmp_path / "core"
    provenance = tmp_path / "provenance"
    core.mkdir()
    provenance.mkdir()

    _write_tf(core / "lemma.tf", "@node\n@description=lexical lemma\n@valueType=str")
    _write_tf(
        provenance / "srcxml.tf",
        "@node\n@description=source XML\n@valueType=str",
    )

    # Text-Fabric creates runtime cache directories named `.tf`; Path.glob("*.tf")
    # matches them even though they are not feature files. Other directory names ending
    # in `.tf` must likewise never be interpreted as feature files.
    (core / ".tf").mkdir()
    (core / "scratch.tf").mkdir()
    (provenance / ".tf").mkdir()
    (provenance / "scratch.tf").mkdir()

    features = featuredocs.discover_features(
        core,
        provenance_dir=provenance,
        descriptions={"lemma": "lexical lemma", "srcxml": "source XML"},
    )

    assert {(item.module, item.name) for item in features} == {
        ("core", "lemma"),
        ("provenance", "srcxml"),
    }
