"""TDD research contracts for #21/#23: no automatic correction from votes."""
from __future__ import annotations
import importlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def module():
    try:
        return importlib.import_module("research_cuneiform_quality")
    except ModuleNotFoundError:
        pytest.fail("research_cuneiform_quality missing (RED gate)")


def test_gap_reason_is_exhaustive_and_overlap_is_retained():
    classify = module().classify_gap
    assert classify("", ["a"], {})["primary"] == "no-cu"
    assert classify("𒀀", [], {})["primary"] == "no-sign-slots"
    row = classify("𒀀▒" + chr(0x100009), ["a", "MEŠ"], {"MEŠ": "𒈨𒌍"})
    assert "pua" in row["flags"] and "placeholder" in row["flags"]
    assert "compound" in row["flags"]
    assert row["primary"] != "unknown"
    assert classify("𒀀", ["a"], {})["primary"] == "unknown"


def test_unknown_cannot_be_coerced_into_false_resolution():
    classify = module().classify_gap
    a = classify("𒀀𒁹", ["a"], {})
    assert a["primary"] != "resolved"
    assert len(a["flags"]) >= 1


def test_reference_evidence_never_proposes_replacement():
    from tlhdig.signrefs import References
    r = References({"wa": {"osl": {"𒁀"}, "potnia": {"𒉿"}}})
    case = module().classify_disagreement("wa", "𒊀", r)
    assert case["status"] == "all-disagree"
    assert case["reference_conflict"]
    assert case["sourceCandidates"] == {"osl": ["𒁀"], "potnia": ["𒉿"]}
    assert "corrected" not in case and "replacement" not in case


def test_equivalent_sign_is_not_outvoted():
    from tlhdig.signrefs import References
    r = References({"ku": {"osl": {"𒆪"}}}, {"𒂉": {"𒂉", "𒆪"}})
    assert module().classify_disagreement("ku", "𒂉", r)["status"] == "supported"


def test_independent_traditions_not_raw_list_count():
    from tlhdig.signrefs import References, LINEAGE
    r = References({"a": {"enmerkar": {"𒁀"}, "osl": {"𒂊"}}})
    case = module().classify_disagreement("a", "𒀀", r)
    assert case["sources"] == 2
    assert case["traditions"] == len({LINEAGE.get(x,x) for x in ("enmerkar","osl")})
    assert case["status"] == "all-disagree"


def test_unknown_reference_reading_remains_explicit():
    from tlhdig.signrefs import References
    case = module().classify_disagreement("nonexistent", "𒀀", References({}))
    assert case["status"] == "unknown"
    assert case["sourceCandidates"] == {}


def test_line_source_identity_uses_document_extent_not_repeated_manuscript_siglum():
    lookup = module().source_for_line
    docs = [(1, 10, "A.xml", "Same siglum"), (11, 20, "B.xml", "Same siglum")]
    assert lookup([12, 13], docs)["src_file"] == "B.xml"
    assert lookup([9, 12], docs) is None  # fail closed on crossing
    assert lookup([], docs) is None
    assert lookup([21], docs) is None


def test_unaligned_case_document_source_is_immutable_record_identity():
    assert "src_file" in module().inventory.__code__.co_consts or (
        "src_file" in __import__("inspect").getsource(module().inventory)
    )


def test_external_reference_disagreement_collapses_known_sign_equivalences():
    from tlhdig.signrefs import References
    refs = References(
        {"ku": {"osl": {"𒆪"}, "potnia": {"𒂉"}}},
        {"𒂉": {"𒂉", "𒆪"}, "𒆪": {"𒂉", "𒆪"}},
    )
    result = module().classify_disagreement("ku", "𒂉", refs)
    assert result["reference_conflict"]  # raw glyphs differ
    assert not result["equivalenceAwareReferenceConflict"]  # same sign
    assert result["status"] == "supported"


def test_truly_distinct_reference_glyphs_remain_contested():
    from tlhdig.signrefs import References
    refs = References({"wa": {"osl": {"𒁀"}, "potnia": {"𒉿"}}})
    result = module().classify_disagreement("wa", "𒊀", refs)
    assert result["reference_conflict"]
    assert result["equivalenceAwareReferenceConflict"]


def test_derived_lists_do_not_count_as_two_independent_opposing_votes():
    from tlhdig.signrefs import References
    refs = References({"an": {"osl": {"𒁀"}, "enmerkar": {"𒁀"}}})
    case = module().classify_disagreement("an", "𒀭", refs)
    assert case["status"] == "all-disagree"
    assert case["traditions"] == 1
    assert case["opposingTraditions"] == 1
    assert case["independentConsensusAlternatives"] == []
    assert not case["independentConsensus"]


def test_two_unrelated_houses_support_one_consistent_alternative():
    from tlhdig.signrefs import References
    refs = References({
        "wa": {"osl": {"𒉿"}, "enmerkar": {"𒉿"}, "potnia": {"𒉿"}}
    })
    case = module().classify_disagreement("wa", "𒊀", refs)
    assert case["sources"] == 3
    assert case["opposingTraditions"] == 2
    assert case["independentConsensusAlternatives"] == ["𒉿"]
    assert case["independentConsensus"]


def test_unrelated_opposition_without_common_glyph_is_not_consensus():
    from tlhdig.signrefs import References
    refs = References({"wa": {"osl": {"𒉿"}, "potnia": {"𒁀"}}})
    case = module().classify_disagreement("wa", "𒊀", refs)
    assert case["opposingTraditions"] == 2
    assert not case["independentConsensus"]
    assert case["independentConsensusAlternatives"] == []


def test_transitive_equivalence_class_prevents_false_witness_conflict():
    from tlhdig.signrefs import References
    refs = References({"ku": {"osl": {"𒆪"}, "potnia": {"𒂉"}, "nuolenna": {"𒆨"}}},
                      {"𒆪": {"𒆪", "𒂉"}, "𒂉": {"𒂉", "𒆨"}})
    case = module().classify_disagreement("ku", "𒀭", refs)
    assert not case["equivalenceAwareReferenceConflict"]
    assert case["independentConsensus"]
    assert len(case["independentConsensusAlternatives"]) == 1


def test_lineage_with_support_cannot_be_treated_as_unanimously_opposed():
    from tlhdig.signrefs import References
    refs = References({"a": {"osl": {"𒀀"}, "enmerkar": {"𒁀"}, "potnia": {"𒁀"}}})
    case = module().classify_disagreement("a", "𒀀", refs)
    assert case["status"] == "split"
    assert case["opposingTraditions"] == 1
    assert not case["independentConsensus"]
