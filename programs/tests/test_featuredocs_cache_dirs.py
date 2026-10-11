"""TDD contract for generated feature-file discovery (#110)."""
from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import featuredocs


def _write_tf(path: Path, *, name: str | None = None) -> None:
    feature = name or path.stem
    path.write_text(
        f"@node\n@description={feature} description\n@valueType=str\n\n1\tx\n",
        encoding="utf8",
    )


def test_discovery_ignores_suffix_matching_directories_in_both_modules(tmp_path):
    core = tmp_path / "core"
    provenance = tmp_path / "provenance"
    core.mkdir()
    provenance.mkdir()
    _write_tf(core / "lemma.tf")
    _write_tf(provenance / "srcxml.tf")

    for directory in (core, provenance):
        (directory / ".tf").mkdir()
        (directory / "scratch.tf").mkdir()

    features = featuredocs.discover_features(
        core,
        provenance_dir=provenance,
        descriptions={
            "lemma": "lemma description",
            "srcxml": "srcxml description",
        },
    )
    assert [(feature.module, feature.name) for feature in features] == [
        ("core", "lemma"),
        ("provenance", "srcxml"),
    ]


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="platform has no symlink support")
def test_discovery_rejects_tf_named_symlink_instead_of_following_it(tmp_path):
    core = tmp_path / "core"
    core.mkdir()
    target = tmp_path / "outside"
    target.mkdir()
    _write_tf(target / "external.tf", name="alias")
    (core / "alias.tf").symlink_to(target / "external.tf")

    with pytest.raises(featuredocs.FeatureDocsError, match="symlink|regular"):
        featuredocs.discover_features(core, descriptions={"alias": "alias description"})


def test_malformed_regular_feature_file_still_fails_closed(tmp_path):
    core = tmp_path / "core"
    core.mkdir()
    (core / "broken.tf").write_text("not-a-tf-header\n\n1\tx\n", encoding="utf8")
    with pytest.raises(featuredocs.FeatureDocsError, match="malformed"):
        featuredocs.discover_features(core, descriptions={"broken": "broken description"})


def test_regular_feature_order_stays_deterministic(tmp_path):
    core = tmp_path / "core"
    core.mkdir()
    for name in ("zeta", "alpha", "middle"):
        _write_tf(core / f"{name}.tf")
    features = featuredocs.discover_features(
        core,
        descriptions={name: f"{name} description" for name in ("zeta", "alpha", "middle")},
    )
    assert [feature.name for feature in features] == ["alpha", "middle", "zeta"]
