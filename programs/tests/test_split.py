"""The provenance module.

`srcxml` and `src_span` are 56 MB of 412 -- more than the whole lexical and
morphological layer -- and they serve validation, not query. Splitting them out is only
safe because everything inside `srcxml` is modelled elsewhere: wrappers as
`sgr`/`agr`/`det`/`num`, damage as `cluster` nodes with offsets, `corr` and `note` as
their own features. `check_tags.py` is what keeps that true.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build as buildmod
from tlhdig import PROVENANCE_DIR, PROVENANCE_FEATURES, TF_VERSION, appcheck, tags


def test_the_features_moved_are_the_ones_declared():
    assert set(PROVENANCE_FEATURES) == {"srcxml", "src_span"}


def test_split_moves_only_the_provenance_features(tmp_path, monkeypatch):
    out = tmp_path / "tf" / TF_VERSION
    out.mkdir(parents=True)
    for name in ("otype", "sym", "lemma", *PROVENANCE_FEATURES):
        (out / f"{name}.tf").write_text("@node\n\n1\tx\n", encoding="utf8")
    monkeypatch.setattr(buildmod, "ROOT", tmp_path)
    moved = buildmod.split_provenance(out)

    assert sorted(moved) == ["src_span", "srcxml"]
    assert not (out / "srcxml.tf").exists()
    assert not (out / "src_span.tf").exists()
    for kept in ("otype", "sym", "lemma"):
        assert (out / f"{kept}.tf").is_file(), f"{kept} must stay in the dataset"
    prov = tmp_path / PROVENANCE_DIR / TF_VERSION
    assert (prov / "srcxml.tf").is_file()
    assert (prov / "src_span.tf").is_file()


def test_split_is_idempotent(tmp_path, monkeypatch):
    out = tmp_path / "tf" / TF_VERSION
    out.mkdir(parents=True)
    (out / "srcxml.tf").write_text("@node\n\n1\tx\n", encoding="utf8")
    monkeypatch.setattr(buildmod, "ROOT", tmp_path)
    assert buildmod.split_provenance(out) == ["srcxml"]
    assert buildmod.split_provenance(out) == []


def test_a_feature_in_the_module_is_still_found(tmp_path, monkeypatch):
    """The gates must resolve a provenance feature, or check_app reports it missing."""
    out = tmp_path / "tf" / TF_VERSION
    out.mkdir(parents=True)
    (out / "src_span.tf").write_text("@node\n\n1\tx\n", encoding="utf8")
    monkeypatch.setattr(buildmod, "ROOT", tmp_path)
    buildmod.split_provenance(out)
    assert appcheck.feature_path(out, "src_span") is not None
    assert appcheck.feature_path(out, "not_a_feature") is None


def test_nothing_in_srcxml_is_unmodelled():
    """The precondition for the split: every element that can appear inside a <w>, and
    therefore inside `srcxml`, must have a destination other than `raw`.

    The long-form gram wrappers were the last exception -- 212 signs whose srcxml held
    the only record of an `AO:Sumgram` / `AO:Akkgram`. They are now `sgr` / `agr`.
    """
    inline = {
        "w", "sGr", "aGr", "d", "num", "c", "Sumgram", "Akkgram",
        "del_in", "del_fin", "laes_in", "laes_fin", "ras_in", "ras_fin",
        "add_in", "add_fin", "QUOT_HurInHit_in", "QUOT_HurInHit_fin",
        "corr", "subscr", "materlect", "surpl", "note", "space", "gap",
    }
    unmodelled = sorted(
        t for t in inline
        if tags.DESTINATION.get(t) in (None, "raw", "malformed")
    )
    assert not unmodelled, f"srcxml would be the only record of: {unmodelled}"
