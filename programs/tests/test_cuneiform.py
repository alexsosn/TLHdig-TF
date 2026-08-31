"""Laying cuneiform out per sign.

The mechanisms are measured in docs/research-cuneiform-alignment.md; these pin the
behaviour, including the cases that must NOT align. A line nothing explains stays
unaligned: absence of an assignment means unknown, never "no sign".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import cuneiform as C

A, BA, ME, ESH, U, DISH = "\U00012000", "\U00012040", "\U00012228", "\U0001230D", "\U0001230B", "\U00012079"
MULTI = {"MEŠ": ME + ESH, "SAGI": "\U000120E1\U000120D7\U00012083"}


def test_equal_counts_zip_one_to_one():
    assert C.align(A + BA, ["a", "ba"]) == (1, [A, BA])


def test_spacing_and_combining_marks_are_not_points():
    assert C.align(A + " " + BA, ["a", "ba"]) == (1, [A, BA])


def test_a_compound_logogram_takes_several_codepoints():
    """`MEŠ` is written 𒈨𒌍 -- one reading, two signs, 21,818 observations."""
    how, got = C.align(A + ME + ESH, ["a", "MEŠ"], multi=MULTI)
    assert how == 3
    assert got == [A, ME + ESH]


def test_a_three_sign_logogram_works_too():
    how, got = C.align(A + MULTI["SAGI"], ["a", "SAGI"], multi=MULTI)
    assert how == 3 and got[1] == MULTI["SAGI"]


def test_a_lacuna_absorbs_its_placeholders():
    how, got = C.align(A + C.PLACEHOLDER + C.PLACEHOLDER + BA, ["a", "ba"], damaged=True)
    assert how == 2
    assert got == [A, BA]


def test_placeholders_are_not_absorbed_without_recorded_damage():
    """A surplus placeholder where nothing is marked damaged is unexplained."""
    assert C.align(A + C.PLACEHOLDER + BA, ["a", "ba"], damaged=False) is None


def test_absorbing_more_or_fewer_than_the_surplus_is_refused():
    """Two placeholders but three surplus codepoints: the extra one is not a placeholder,
    so the line is not explained and must not be forced."""
    assert C.align(A + C.PLACEHOLDER + C.PLACEHOLDER + ME + BA, ["a", "ba"],
                   damaged=True) is None


def test_damage_and_a_compound_can_occur_on_one_line():
    how, got = C.align(A + C.PLACEHOLDER + ME + ESH, ["a", "MEŠ"], damaged=True, multi=MULTI)
    assert how == 3
    assert got == [A, ME + ESH]


def test_the_strongest_explanation_wins():
    """A line whose counts already match is level 1, even if a compound would also fit."""
    how, _ = C.align(ME + ESH, ["MEŠ", "x"], multi=MULTI)
    assert how == 1


def test_an_unknown_reading_does_not_consume_two_codepoints():
    """Only readings in the measured table may take more than one sign."""
    assert C.align(A + ME + ESH, ["a", "NOTINTABLE"], multi=MULTI) is None


def test_nothing_to_align_returns_none():
    assert C.align("", ["a"]) is None
    assert C.align(A, []) is None


def test_load_multi_ignores_single_codepoint_rows(tmp_path):
    """`signmap.tsv` holds one-to-one readings; only sequences belong here."""
    f = tmp_path / "m.tsv"
    f.write_text(f"# c\nMEŠ\t{ME+ESH}\t0.99\t10\t10\n a\t{A}\t0.99\t10\t10\n",
                 encoding="utf8")
    got = C.load_multi(f)
    assert got == {"MEŠ": ME + ESH}
