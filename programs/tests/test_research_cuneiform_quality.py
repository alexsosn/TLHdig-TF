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
