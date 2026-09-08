"""Adversarial regressions found during #43 implementation review."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import featuredocs


def write_tf(path: Path, header: str) -> Path:
    path.write_text(header.rstrip("\n") + "\n\n1\tx\n", encoding="utf8")
    return path


def test_explicit_missing_provenance_release_is_not_silently_omitted(tmp_path):
    core = tmp_path / "tf"
    core.mkdir()
    write_tf(core / "otype.tf", "@node\n@version=1")

    with pytest.raises(featuredocs.FeatureDocsError, match="provenance.*does not exist"):
        featuredocs.discover_features(core, provenance_dir=tmp_path / "missing-provenance")


def test_render_rejects_feature_header_from_wrong_release(tmp_path):
    core = tmp_path / "tf"
    core.mkdir()
    write_tf(
        core / "lemma.tf",
        "@node\n@description=lexical lemma\n@valueType=str\n@version=0.9",
    )
    features = featuredocs.discover_features(
        core,
        descriptions={"lemma": "lexical lemma"},
    )

    with pytest.raises(featuredocs.FeatureDocsError, match="lemma.*@version.*0.9.*1.0"):
        featuredocs.render_tree(features, version="1.0")
