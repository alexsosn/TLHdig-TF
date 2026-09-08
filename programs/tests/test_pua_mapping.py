"""#20 RED contract for reproducible mapped/unresolved PUA classification."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert


ROOT = Path(__file__).resolve().parents[2]
PROGRAMS = ROOT / "programs"

MAPPED = chr(0x100000)
UNRESOLVED = chr(0x100009)
FUTURE = chr(0x10000B)
ORDINARY = "𒀀"
BMP_PUA = chr(0xE000)
SUPPLEMENTARY_A = chr(0xF0000)


def _pua():
    """Load only inside tests so RED is test failures, not collection failure."""
    try:
        return importlib.import_module("tlhdig.pua")
    except ModuleNotFoundError:
        pytest.fail("#20 requires tlhdig.pua production classifier")


def _build(tmp_path: Path, cu: str):
    corpus = tmp_path / "corpus" / "CTH 999_XML_TLH"
    corpus.mkdir(parents=True)
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>PUA 1</docID><meta/></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<AO:Manuscripts><AO:TxtPubl>PUA 1</AO:TxtPubl></AO:Manuscripts>
<lb txtid="PUA 1" lnr="Vs. I 1" lg="Hit" cu="{cu}"/>
<w trans="a">a</w>
</text></div1></body></AOxml>'''
    (corpus / "PUA.xml").write_text(xml, encoding="utf8")
    api = convert.build(corpus.parent, tmp_path / "tf")
    assert api is not None
    return api


def test_all_three_unicode_private_use_ranges_are_recognised():
    pua = _pua()
    assert pua.is_pua_char(BMP_PUA)
    assert pua.is_pua_char(SUPPLEMENTARY_A)
    assert pua.is_pua_char(MAPPED)
    assert not pua.is_pua_char(ORDINARY)


def test_directly_mapped_value_is_not_unresolved():
    pua = _pua()
    assert pua.classify_codepoint(ord(MAPPED)) == "mapped-deliberate-pua"
    assert pua.count_pua(MAPPED) == (1, 0)


def test_ambiguous_legacy_value_remains_unresolved():
    pua = _pua()
    assert pua.classify_codepoint(ord(UNRESOLVED)) == "ambiguous-legacy-pua"
    assert pua.count_pua(UNRESOLVED) == (1, 1)


def test_mixed_string_counts_total_and_unresolved_occurrences_independently():
    pua = _pua()
    # Count occurrences, not distinct values. Ordinary Unicode cuneiform is irrelevant.
    text = MAPPED + ORDINARY + UNRESOLVED + MAPPED + UNRESOLVED
    assert pua.count_pua(text) == (4, 2)


def test_non_pua_cuneiform_has_zero_counts():
    assert _pua().count_pua(ORDINARY + "𒀭") == (0, 0)


def test_future_undeclared_pua_is_unresolved_never_mapped():
    pua = _pua()
    assert pua.classify_codepoint(ord(FUTURE)) == "unknown-pua"
    assert pua.count_pua(FUTURE) == (1, 1)


def test_committed_status_table_has_frozen_research_population_and_valid_schema():
    pua = _pua()
    table = pua.load_status_table()
    assert table["schema"] == 1
    assert set(table["codepoints"]) == {
        "U+100000", "U+100001", "U+100003", "U+100005", "U+100006", "U+100009"
    }
    assert table["codepoints"]["U+100000"]["status"] == "mapped-deliberate-pua"
    assert all(
        table["codepoints"][cp]["status"] == "ambiguous-legacy-pua"
        for cp in ("U+100001", "U+100003", "U+100005", "U+100006", "U+100009")
    )


def test_table_validator_rejects_invalid_status_and_codepoint(tmp_path):
    pua = _pua()
    bad_status = tmp_path / "bad-status.json"
    bad_status.write_text(json.dumps({
        "schema": 1,
        "codepoints": {"U+100000": {"status": "mapped-because-we-say-so"}},
    }), encoding="utf8")
    with pytest.raises(ValueError):
        pua.load_status_table(bad_status)

    bad_cp = tmp_path / "bad-cp.json"
    bad_cp.write_text(json.dumps({
        "schema": 1,
        "codepoints": {"not-a-codepoint": {"status": "ambiguous-legacy-pua"}},
    }), encoding="utf8")
    with pytest.raises(ValueError):
        pua.load_status_table(bad_cp)


def test_converter_emits_line_level_unresolved_count_without_rewriting_cu(tmp_path):
    api = _build(tmp_path, MAPPED + UNRESOLVED + ORDINARY)
    line = next(iter(api.F.otype.s("line")))
    assert api.F.cu.v(line) == MAPPED + UNRESOLVED + ORDINARY
    assert api.F.cu_pua.v(line) == 2
    assert api.F.cu_pua_unmapped.v(line) == 1


def test_line_level_classification_does_not_depend_on_sign_alignment(tmp_path):
    # One transliterated sign against two cuneiform code points makes this fixture
    # intentionally unsuitable for a complete sign-level zip. The PUA count is still a
    # property of verbatim line-level cu and must be available regardless of alignment.
    api = _build(tmp_path, MAPPED + UNRESOLVED)
    line = next(iter(api.F.otype.s("line")))
    assert api.F.cu_aligned.v(line) in (None, 0)
    assert api.F.cu_pua.v(line) == 2
    assert api.F.cu_pua_unmapped.v(line) == 1


def test_independent_corpus_checker_exists_and_freezes_measured_totals():
    checker = PROGRAMS / "check_pua_mapping.py"
    assert checker.is_file(), "#20 requires a permanent independent source→TF PUA checker"
    text = checker.read_text(encoding="utf8")
    # The checker must freeze the hosted research population and not quietly learn a
    # new trust set from the generated graph.
    assert "3_643" in text
    assert "924" in text
    assert "2_719" in text
    assert "signmap" not in text.lower()
