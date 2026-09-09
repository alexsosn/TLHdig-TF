"""#52 RED contract: preserve readable words before the first real line.

These tests deliberately describe graph semantics rather than an implementation helper.
Production code is unchanged when this file lands.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert


ROOT = Path(__file__).resolve().parents[2]
PROGRAMS = ROOT / "programs"


def _xml(pre: str, line_word: str = "nu", with_line: bool = True) -> str:
    line = ""
    if with_line:
        line = f'''<lb txtid="PRE 1" lnr="Vs. I 1" lg="Hit" cu="&#x12000;"/>
<w trans="{line_word}">{line_word}</w>'''
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>PRE 1</docID><meta/></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
{pre}
{line}
</text></div1></body></AOxml>'''


def _build(tmp_path: Path, pre: str, *, with_line: bool = True):
    src = tmp_path / "corpus" / "CTH 999_XML_TLH"
    src.mkdir(parents=True)
    (src / "PRE 1.xml").write_text(_xml(pre, with_line=with_line), encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    return api


def _word(api, trans: str):
    return next((w for w in api.F.otype.s("word") if api.F.trans.v(w) == trans), None)


def _word_signs(api, trans: str):
    word = _word(api, trans)
    assert word is not None, f"source word {trans!r} was not represented"
    return list(api.L.d(word, otype="sign"))


def test_readable_preline_word_is_preserved_under_document_without_line(tmp_path):
    api = _build(tmp_path, '<w trans="pre">pa-it</w>')
    signs = _word_signs(api, "pre")
    assert [api.F.sym.v(s) for s in signs] == ["pa", "it"]
    assert all(api.L.u(s, otype="document") for s in signs)
    assert all(not api.L.u(s, otype="line") for s in signs)


def test_marker_layout_only_preline_word_does_not_create_a_linguistic_sign(tmp_path):
    api = _build(tmp_path, '<w><space c="3"/><del_in/><del_fin/></w>')
    line = api.F.otype.s("line")[0]
    line_signs = list(api.L.d(line, otype="sign"))
    # The only source-readable sign is the word after the real lb. A pre-line layout
    # record may be anchored to it, but must not manufacture another linguistic sign.
    assert [api.F.sym.v(s) for s in line_signs if not api.F.anchor.v(s)] == ["nu"]
    assert len([s for s in api.F.otype.s("sign") if not api.F.anchor.v(s)]) == 1


def test_preline_note_anchors_to_preline_source_sign_not_first_line(tmp_path):
    api = _build(
        tmp_path,
        '<w trans="pre">pa-it<note n="P" c="pre-line note"/></w>',
    )
    pre_signs = set(_word_signs(api, "pre"))
    notes = [n for n in api.F.otype.s("note") if api.F.n.v(n) == "P"]
    assert len(notes) == 1
    target = api.E.noteref.f(notes[0])
    assert len(target) == 1
    assert target[0] in pre_signs
    assert not api.L.u(target[0], otype="line")


def test_document_without_lb_still_preserves_readable_preline_content(tmp_path):
    api = _build(tmp_path, '<w trans="pre">pa-it</w>', with_line=False)
    docs = api.F.otype.s("document")
    assert len(docs) == 1
    signs = _word_signs(api, "pre")
    assert [api.F.sym.v(s) for s in signs] == ["pa", "it"]
    assert all(api.L.u(s, otype="document") == tuple(docs) for s in signs)
    assert not api.F.otype.s("line")


def test_source_sign_order_crosses_preline_to_first_line_without_duplication(tmp_path):
    api = _build(tmp_path, '<w trans="pre">pa-it</w>')
    source_signs = [s for s in api.F.otype.s("sign") if not api.F.anchor.v(s)]
    assert [api.F.sym.v(s) for s in source_signs] == ["pa", "it", "nu"]


def test_first_real_line_extent_starts_at_its_own_first_sign(tmp_path):
    api = _build(tmp_path, '<w trans="pre">pa-it</w>')
    pre_signs = set(_word_signs(api, "pre"))
    line = api.F.otype.s("line")[0]
    line_signs = list(api.L.d(line, otype="sign"))
    assert [api.F.sym.v(s) for s in line_signs] == ["nu"]
    assert not pre_signs.intersection(line_signs)


def test_preline_source_signs_are_never_technical_anchors(tmp_path):
    api = _build(tmp_path, '<w trans="pre">pa-it</w>')
    signs = _word_signs(api, "pre")
    assert all(api.F.anchor.v(s) is None for s in signs)


def test_preline_section_navigation_has_document_but_no_synthetic_line(tmp_path):
    api = _build(tmp_path, '<w trans="pre">pa-it</w>')
    sign = _word_signs(api, "pre")[0]
    assert api.L.u(sign, otype="document")
    assert not api.L.u(sign, otype="line")
    section = api.T.sectionFromNode(sign)
    assert section[0] == "PRE 1"
    assert section[1:] == (None, None)


def test_corpus_conservation_checker_is_required_and_freezes_research_population():
    checker = PROGRAMS / "check_preline_words.py"
    assert checker.is_file(), "#52 requires an independent pre-line conservation checker"
    text = checker.read_text(encoding="utf8")
    # Freeze the measured source population rather than silently learning acceptance
    # from the graph produced by the converter under test.
    assert "36" in text
    assert "15" in text
    assert "22" in text
    assert "3_365_151" in text
