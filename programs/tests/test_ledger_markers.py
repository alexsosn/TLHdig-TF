"""The damage-marker ledger.

Four builds in a row reported healthy totals while losing markers, so the ledger is
the component that has to be trustworthy on its own.  These tests pin the two claims
the build gate rests on: every count it compares is *shown*, and a per-document
divergence is named rather than folded into a corpus-wide total.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert


def test_report_shows_the_source_column():
    """The gate compares src to fed; a report that hides src cannot be checked."""
    L = convert.Ledger()
    L.note_markers("a.xml", {"del/open": 3}, {"del/open": 3}, {"del/open": 3})
    out = L.marker_report()
    assert "src" in out and "fed" in out and "emitted" in out
    assert out.count("3") >= 3


def test_conserved_document_is_not_listed_as_divergent():
    L = convert.Ledger()
    L.note_markers("a.xml", {"del/open": 2}, {"del/open": 2}, {"del/open": 2})
    assert L.marker_lost == []
    assert "LOST" not in L.marker_report()


def test_loss_between_source_and_fed_is_named_per_document():
    """The regression that cost four build cycles: markers dropped before emission."""
    L = convert.Ledger()
    L.note_markers("kept.xml", {"del/open": 5}, {"del/open": 5}, {"del/open": 5})
    L.note_markers("lossy.xml", {"del/open": 9}, {"del/open": 4}, {"del/open": 4})
    assert [r for r, *_ in L.marker_lost] == ["lossy.xml"]
    assert L.marker_src["del/open"] == 14
    assert L.marker_fed["del/open"] == 9
    report = L.marker_report()
    assert "LOST 5" in report
    assert "lossy.xml" in report


def test_loss_between_fed_and_emitted_is_flagged():
    L = convert.Ledger()
    L.note_markers("a.xml", {"ras/open": 7}, {"ras/open": 7}, {"ras/open": 6})
    assert L.marker_lost
    assert "LOST 1" in L.marker_report()


def test_gate_condition_matches_the_report():
    """build.py fails when src != fed or fed != out -- the report must agree."""
    for src, fed, out, bad in (
        ({"a": 1}, {"a": 1}, {"a": 1}, False),
        ({"a": 2}, {"a": 1}, {"a": 1}, True),
        ({"a": 1}, {"a": 1}, {"a": 0}, True),
    ):
        L = convert.Ledger()
        L.note_markers("f.xml", src, fed, out)
        gate = L.marker_src != L.marker_fed or L.marker_fed != L.marker_out
        assert gate is bad
        assert ("LOST" in L.marker_report()) is bad
