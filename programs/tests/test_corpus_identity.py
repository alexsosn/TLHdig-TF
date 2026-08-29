"""The corpus is an immutable release, so its identity is pinned, not re-derived.

`files = corpus_files()` builds the input list dynamically, so deleting a source XML
reduced both the total and the converted count and the ledger balanced perfectly. A
checksum manifest makes that a build failure instead.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import corpusid


def test_detects_a_missing_file(tmp_path):
    (tmp_path / "a.xml").write_text("<r/>", encoding="utf8")
    man = corpusid.build_manifest(tmp_path)
    (tmp_path / "a.xml").unlink()
    problems = corpusid.verify(tmp_path, man)
    assert any("missing" in p for p in problems)


def test_detects_an_altered_file(tmp_path):
    f = tmp_path / "a.xml"
    f.write_text("<r/>", encoding="utf8")
    man = corpusid.build_manifest(tmp_path)
    f.write_text("<r>changed</r>", encoding="utf8")
    problems = corpusid.verify(tmp_path, man)
    assert any("altered" in p for p in problems)


def test_detects_an_extra_file(tmp_path):
    (tmp_path / "a.xml").write_text("<r/>", encoding="utf8")
    man = corpusid.build_manifest(tmp_path)
    (tmp_path / "b.xml").write_text("<r/>", encoding="utf8")
    problems = corpusid.verify(tmp_path, man)
    assert any("unexpected" in p for p in problems)


def test_clean_corpus_has_no_problems(tmp_path):
    (tmp_path / "a.xml").write_text("<r/>", encoding="utf8")
    (tmp_path / "b.xml").write_text("<r>x</r>", encoding="utf8")
    man = corpusid.build_manifest(tmp_path)
    assert corpusid.verify(tmp_path, man) == []


def test_manifest_roundtrips(tmp_path):
    (tmp_path / "a.xml").write_text("<r/>", encoding="utf8")
    man = corpusid.build_manifest(tmp_path)
    p = tmp_path / "m.sha256"
    corpusid.write_manifest(p, man)
    assert corpusid.read_manifest(p) == man
