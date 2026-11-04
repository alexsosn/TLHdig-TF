"""#92 RED contract for TLHdig/HFR morphology control markers."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert, morph


CONTROL_FAMILIES = (
    "①", "②Ⓐ", "ⓐⒸ", "⓶ⓑⒸ", "⓷Ⓐ", "②Ⓑ", "②ⓐⒸ", "②ⓐⒸⓢⓣ",
    "⓶Ⓒⓐ", "⓶", "⓷", "⓷Ⓑ", "②Ⓒⓐ", "⓶ⓐⒸ", "⓷ⓐⒸ", "②ⓑⒸ",
    "②ⓐⒸⓐ", "⓶Ⓒⓑ", "ⓢⓣ", "②Ⓒⓑ", "Ⓑ",
)

GLUED_CONTROL_REMAINDERS = ("kinun", "KÙ.BABBAR", "kattan", "maniaḫḫ=eššar", "lukkatta")


@pytest.mark.parametrize("control", CONTROL_FAMILIES)
def test_known_control_family_is_separated_from_lemma(control: str) -> None:
    a = morph.parse(1, f"{control} apa-@er@DEM2/3.NOM.SG.C@20@")
    assert a.ok
    assert a.control == control
    assert a.base.lemma == "apa-"
    assert a.raw == f"{control} apa-@er@DEM2/3.NOM.SG.C@20@"
    assert a.normalised is True


@pytest.mark.parametrize("lemma", GLUED_CONTROL_REMAINDERS)
def test_only_measured_glued_control_spellings_are_accepted(lemma: str) -> None:
    a = morph.parse(1, f"⓷{lemma}@g@ADV@")
    assert a.ok
    assert a.control == "⓷"
    assert a.base.lemma == lemma
    assert a.normalised is True


def test_future_glued_spelling_fails_closed() -> None:
    a = morph.parse(1, "⓷future@future@ADV@")
    assert not a.ok
    assert a.base.lemma == ""
    assert "control" in a.note.lower()
    assert a.raw == "⓷future@future@ADV@"


@pytest.mark.parametrize("raw", (
    "③ apa-@er@DEM2/3.NOM.SG.C@20@",
    "Ⓓ apa-@er@DEM2/3.NOM.SG.C@20@",
    "②Ⓓ apa-@er@DEM2/3.NOM.SG.C@20@",
))
def test_unknown_control_like_prefix_fails_closed(raw: str) -> None:
    a = morph.parse(1, raw)
    assert not a.ok
    assert a.base.lemma == ""
    assert "control" in a.note.lower()
    assert a.raw == raw


@pytest.mark.parametrize("raw", (
    "① ③ apa-@er@DEM2/3.NOM.SG.C@20@",
    "① ②Ⓐ apa-@er@DEM2/3.NOM.SG.C@20@",
))
def test_second_control_run_after_known_control_fails_closed(raw: str) -> None:
    """A known first run must not whitelist a second control-like run as lexical text."""
    a = morph.parse(1, raw)
    assert not a.ok
    assert a.control == ""
    assert a.base.lemma == ""
    assert "control" in a.note.lower()
    assert a.raw == raw


@pytest.mark.parametrize("lemma", ("½", "½-AM", "=", "°x", "?x", "[x"))
def test_broad_symbol_prefixes_are_not_stripped_as_controls(lemma: str) -> None:
    a = morph.parse(1, f"{lemma}@g@ADV@")
    assert a.ok
    assert a.control == ""
    assert a.base.lemma == lemma


def test_control_only_first_field_is_preserved_without_fake_lemma() -> None:
    a = morph.parse(1, "①@@@@ ")
    assert a.ok
    assert a.control == "①"
    assert a.base.lemma == ""
    assert a.raw == "①@@@@ "
    assert a.normalised is True


DOC = """<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>CTRL 92</docID><meta/></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<AO:Manuscripts><AO:TxtPubl>CTRL 92</AO:TxtPubl></AO:Manuscripts>
<lb txtid="CTRL 92" lnr="1" lg="Hit" cu="&#x12000;"/>
<w trans="apa1" mrp0sel=" 1 "
   mrp1="① apa-@er@DEM2/3.NOM.SG.C@20@">a-pa</w>
<w trans="apa2" mrp0sel=" 1 "
   mrp1="②Ⓐ apa-@er@DEM2/3.NOM.SG.C@20@">a-pa</w>
<w trans="bad" mrp0sel=" 1 "
   mrp1="③ apa-@er@DEM2/3.NOM.SG.C@20@">a-pa</w>
<w trans="control-only" mrp0sel=" 1 "
   mrp1="①@@@@ ">x</w>
<w trans="unselected" mrp0sel=""
   mrp1="ⓐⒸ unselected-@unselected@@ADV@">u</w>
</text></div1></body></AOxml>
"""


def _build(tmp_path: Path):
    src = tmp_path / "corpus" / "CTH 999_XML_TLH"
    src.mkdir(parents=True)
    (src / "CTRL 92.xml").write_text(DOC, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    return api


def test_converter_emits_control_and_merges_only_lexical_identity(tmp_path: Path) -> None:
    api = _build(tmp_path)
    F, E = api.F, api.E

    good = [
        a for a in F.otype.s("analysis")
        if F.parse_ok.v(a) == 1 and F.lemma.v(a) == "apa-"
    ]
    assert len(good) == 2
    assert {F.mrp_control.v(a) for a in good} == {"①", "②Ⓐ"}
    assert all(F.raw.v(a) for a in good), "control normalization must retain exact raw mrpN"

    lex_nodes = {E.lexeme.f(a)[0] for a in good}
    assert len(lex_nodes) == 1, "control variants must not split one lexical identity"
    assert len(good) == 2, "analysis candidates themselves must not collapse"


def test_unknown_control_never_becomes_a_lexeme_key(tmp_path: Path) -> None:
    api = _build(tmp_path)
    F, E = api.F, api.E
    bad_word = next(w for w in F.otype.s("word") if F.trans.v(w) == "bad")
    (a,) = E.analyses.f(bad_word)
    assert F.parse_ok.v(a) == 0
    assert not F.lemma.v(a)
    assert E.lexeme.f(a) == ()
    assert F.raw.v(a) == "③ apa-@er@DEM2/3.NOM.SG.C@20@"


def test_known_control_only_analysis_does_not_create_empty_lexeme(tmp_path: Path) -> None:
    api = _build(tmp_path)
    F, E = api.F, api.E
    word = next(w for w in F.otype.s("word") if F.trans.v(w) == "control-only")
    (a,) = E.analyses.f(word)
    assert F.parse_ok.v(a) == 1
    assert F.mrp_control.v(a) == "①"
    assert not F.lemma.v(a)
    assert F.raw.v(a) == "①@@@@ "
    assert E.lexeme.f(a) == ()


def test_control_normalization_preserves_source_selection_edge(tmp_path: Path) -> None:
    api = _build(tmp_path)
    F, E = api.F, api.E
    word = next(w for w in F.otype.s("word") if F.trans.v(w) == "apa1")
    picked = E.selected.f(word)
    assert len(picked) == 1
    analysis, selector = picked[0]
    assert selector == "1"
    assert F.index.v(analysis) == 1
    assert F.lemma.v(analysis) == "apa-"
    assert F.mrp_control.v(analysis) == "①"


def test_source_attested_control_before_clitic_only_record_parses_as_clitic() -> None:
    # KBo 52.82+ contains four values of this shape, including this exact mrp1.
    a = morph.parse(1, "②Ⓐ += kkan@OBPk@@ D")
    assert a.ok
    assert a.control == "②Ⓐ"
    assert a.base.lemma == ""
    assert a.clitic is not None
    assert a.clitic.lemma == "kkan"
    assert a.clitic.morph == "OBPk"
    assert a.clitic.det == "D"
    assert a.raw == "②Ⓐ += kkan@OBPk@@ D"
    assert a.normalised is True


def test_control_normalization_does_not_invent_selection_for_unselected_candidate(
    tmp_path: Path,
) -> None:
    api = _build(tmp_path)
    F, E = api.F, api.E
    word = next(w for w in F.otype.s("word") if F.trans.v(w) == "unselected")
    (a,) = E.analyses.f(word)
    assert F.mrpsel_kind.v(word) == "none"
    assert E.selected.f(word) == ()
    assert F.parse_ok.v(a) == 1
    assert F.lemma.v(a) == "unselected-"
    assert F.mrp_control.v(a) == "ⓐⒸ"
    assert F.raw.v(a) == "ⓐⒸ unselected-@unselected@@ADV@"
