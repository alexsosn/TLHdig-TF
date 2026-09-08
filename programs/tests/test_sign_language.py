"""Issue #19 RED/GREEN fixtures for source-faithful sign language propagation."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert
from tlhdig.paths import PROGRAMS


DOC = """<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>LANG 1</docID><meta/></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<AO:Manuscripts><AO:TxtPubl>LANG 1</AO:TxtPubl></AO:Manuscripts>
<lb txtid="LANG 1" lnr="Vs. I 1" cu="𒀀"/>
<w trans="textinherit">ta</w>
<lb txtid="LANG 1" lnr="Vs. I 2" lg="Akk"/>
<w trans="lineoverride">ka</w>
<lb txtid="LANG 1" lnr="Vs. I 3" lg="Hit"/>
<clb lg="Hur"/>
<w trans="colonoverride">hu</w>
<w trans="wordoverride" lg="Akk">ak</w>
<w trans="returncolon">nu</w>
<w trans="emptyword" lg="">e</w>
<w trans="unknownword" lg="XXXlang">u</w>
<lb txtid="LANG 1" lnr="Vs. I 4" lg="Hit"/>
<w trans="colonacrossline">zi</w>
<clb lg=""/>
<w trans="clearedcolon">pa</w>
<clb lg="Hur"/>
<w trans="beforecolumn">ha</w>
<lb txtid="LANG 1" lnr="Vs. II 1" lg="Hit"/>
<w trans="aftercolumn">ki</w>
<lb txtid="LANG 1" lnr="Vs. II 2" lg=""/>
<w trans="emptyline">li</w>
<lb txtid="LANG 1" lnr="Vs. II 3" lg="ign"/>
<w trans="ignraw">in</w>
<lb txtid="LANG 1" lnr="Vs. II 4" lg="Hit"/>
<w trans="outer_nested">a<lb txtid="LANG 1" lnr="Vs. II 5" lg="Akk"/>b</w>
<w trans="after_nested">c</w>
</text></div1></body></AOxml>
"""

# Include one later determined sign so a real `lang.tf` exists while the first sign is
# genuinely undetermined. An all-undetermined tiny fixture correctly omits the feature
# file altogether, which is a TF serialization detail rather than the semantic case
# this test is meant to exercise.
UNLABELLED = """<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>LANG NONE</docID><meta/></AOHeader>
<body><div1 type="transliteration"><text xml:lang="XXXlang">
<AO:Manuscripts><AO:TxtPubl>LANG NONE</AO:TxtPubl></AO:Manuscripts>
<lb txtid="LANG NONE" lnr="Vs. I 1" cu="𒀀"/>
<w trans="nolanguage">na</w>
<lb txtid="LANG NONE" lnr="Vs. I 2" lg="Hit"/>
<w trans="determinedcontrol">ta</w>
</text></div1></body></AOxml>
"""

ANCHOR_ONLY = """<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>LANG ANCHOR</docID><meta/></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<AO:Manuscripts><AO:TxtPubl>LANG ANCHOR</AO:TxtPubl></AO:Manuscripts>
<lb txtid="LANG ANCHOR" lnr="Vs. I 1" lg="Hit" cu="𒀀"/>
<w><del_in/></w>
</text></div1></body></AOxml>
"""


def _build(tmp, xml: str, name: str):
    src = tmp / "corpus" / "CTH 999_XML_TLH"
    src.mkdir(parents=True)
    (src / f"{name}.xml").write_text(xml, encoding="utf8")
    api = convert.build(src.parent, tmp / "tf")
    assert api is not None
    return api


@pytest.fixture(scope="module")
def scope_api(tmp_path_factory):
    return _build(tmp_path_factory.mktemp("sign-lang-scope"), DOC, "LANG")


@pytest.fixture(scope="module")
def unlabelled_api(tmp_path_factory):
    return _build(tmp_path_factory.mktemp("sign-lang-none"), UNLABELLED, "NONE")


def _langs(api, trans: str) -> list[str | None]:
    word = next(w for w in api.F.otype.s("word") if api.F.trans.v(w) == trans)
    signs = api.L.d(word, otype="sign")
    assert signs, trans
    return [api.F.lang.v(s) for s in signs]


def _all(api, trans: str, expected: str | None) -> None:
    got = _langs(api, trans)
    assert got and all(v == expected for v in got), f"{trans}: {got!r} != {expected!r}"


def _checker_module():
    checker = PROGRAMS / "check_sign_language.py"
    assert checker.is_file(), "issue #19 requires an independent permanent corpus checker"
    spec = importlib.util.spec_from_file_location("check_sign_language_test", checker)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Python 3.13 dataclasses resolve postponed annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_text_level_inheritance(scope_api):
    _all(scope_api, "textinherit", "Hit")


def test_line_override_beats_text(scope_api):
    _all(scope_api, "lineoverride", "Akk")


def test_colon_override_beats_line(scope_api):
    _all(scope_api, "colonoverride", "Hur")


def test_word_override_beats_colon(scope_api):
    _all(scope_api, "wordoverride", "Akk")


def test_word_override_returns_to_outer_scope(scope_api):
    _all(scope_api, "returncolon", "Hur")


def test_empty_word_declaration_does_not_block_outer_scope(scope_api):
    _all(scope_api, "emptyword", "Hur")


def test_xxxlang_word_declaration_does_not_block_outer_scope(scope_api):
    _all(scope_api, "unknownword", "Hur")


def test_colon_persists_across_line_in_same_column(scope_api):
    _all(scope_api, "colonacrossline", "Hur")


def test_empty_new_colon_clears_previous_colon(scope_api):
    _all(scope_api, "clearedcolon", "Hit")


def test_column_change_clears_active_colon(scope_api):
    _all(scope_api, "beforecolumn", "Hur")
    _all(scope_api, "aftercolumn", "Hit")


def test_empty_line_declaration_falls_back_to_text(scope_api):
    _all(scope_api, "emptyline", "Hit")


def test_nonempty_unknownish_raw_value_is_preserved(scope_api):
    _all(scope_api, "ignraw", "ign")


def test_recovered_nested_line_boundary_is_an_event_for_following_word(scope_api):
    # text.iter() sees the outer word before its nested recovered <lb>, so the boundary
    # must not retroactively relabel the outer word; it does control the following word.
    _all(scope_api, "outer_nested", "Hit")
    _all(scope_api, "after_nested", "Akk")


def test_genuinely_unlabelled_sign_stays_unlabelled(unlabelled_api):
    _all(unlabelled_api, "nolanguage", None)
    _all(unlabelled_api, "determinedcontrol", "Hit")


def test_technical_anchor_never_receives_language(tmp_path):
    api = _build(tmp_path, ANCHOR_ONLY, "ANCHOR")
    anchors = [s for s in api.F.otype.s("sign") if api.F.anchor.v(s) == 1]
    assert anchors
    # This fixture contains no readable signs, so the dataset may legitimately omit
    # lang.tf entirely. Either way an anchor must never have a language value.
    lang = getattr(api.F, "lang", None)
    assert lang is None or all(lang.v(s) is None for s in anchors)


def test_permanent_checker_exposes_the_frozen_corpus_contract():
    module = _checker_module()
    assert module.TARGET_SOURCE_SIGNS == 3_365_129
    assert module.TARGET_WITH_LANG == 3_364_981
    assert module.TARGET_ANCHORS == 21_215
    assert module.TARGET_LEVELS == {
        "line": 3_259_913,
        "colon": 64_686,
        "word": 40_187,
        "text": 195,
        "absent": 148,
    }


def test_checker_rejects_wrong_or_missing_or_fabricated_language():
    module = _checker_module()
    SourceRow, GraphRow = module.SourceRow, module.GraphRow
    expected = [
        SourceRow("a", "Hit", "line"),
        SourceRow("b", None, "absent"),
    ]
    assert not module.compare_rows(
        "fixture.xml", expected, [GraphRow("a", "Hit"), GraphRow("b", None)]
    )
    assert module.compare_rows(
        "fixture.xml", expected, [GraphRow("a", "Akk"), GraphRow("b", None)]
    )
    assert module.compare_rows(
        "fixture.xml", expected, [GraphRow("a", None), GraphRow("b", None)]
    )
    assert module.compare_rows(
        "fixture.xml", expected, [GraphRow("a", "Hit"), GraphRow("b", "Hit")]
    )


def test_checker_rejects_sign_order_or_symbol_drift():
    module = _checker_module()
    SourceRow, GraphRow = module.SourceRow, module.GraphRow
    expected = [SourceRow("a", "Hit", "line"), SourceRow("b", "Akk", "word")]
    assert module.compare_rows(
        "fixture.xml", expected, [GraphRow("b", "Akk"), GraphRow("a", "Hit")]
    )


def test_checker_rejects_language_on_technical_anchor():
    module = _checker_module()
    assert not module.anchor_language_problems([(1, None), (2, None)])
    assert module.anchor_language_problems([(1, None), (2, "Hit")]) == [
        "anchor sign 2 carries lang='Hit'"
    ]
