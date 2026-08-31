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


# ------------------------------------------------------------ phase 3: numerals
#
# The compound table learned `2` -> 𒁹𒁹 and `12` -> 𒌋𒁹𒁹 by frequency, but a table only
# knows the numbers this release happens to contain. TLHdig is a living corpus: a future
# version will hold numbers the table has never seen, and they would silently fail to
# align. Arithmetic generalises; a table does not.
#
# The primitives are what the corpus attests (signmap.tsv): 1 and 3-9 have dedicated
# signs, 2 is written 𒁹𒁹, 10 is 𒌋, 20 is 𒌋𒌋, 30 is 𒌍. Above 39 nothing is reliably
# attested, so the rule refuses rather than inventing.


def test_a_single_digit_uses_its_own_sign():
    assert C.numeral("7") == "\U0001230C"
    assert C.numeral("1") == "\U00012079"


def test_two_is_written_with_two_units():
    """2 has no dedicated sign in this corpus: 7,409 observations of 𒁹𒁹."""
    assert C.numeral("2") == "\U00012079\U00012079"


def test_a_teen_is_the_tens_sign_then_the_units():
    assert C.numeral("12") == "\U0001230B\U00012079\U00012079"
    assert C.numeral("13") == "\U0001230B" + C.numeral("3")


def test_the_tens_have_their_attested_forms():
    assert C.numeral("10") == "\U0001230B"
    assert C.numeral("20") == "\U0001230B\U0001230B"
    assert C.numeral("30") == "\U0001230D"


def test_a_number_beyond_what_is_attested_is_refused():
    """40 and above: the corpus does not render them consistently -- some lines leave
    ASCII digits in `cu`. Refusing keeps the line unaligned instead of inventing."""
    assert C.numeral("40") is None
    assert C.numeral("137") is None


def test_a_non_numeral_is_refused():
    assert C.numeral("LUGAL") is None
    assert C.numeral("") is None
    assert C.numeral("2a") is None


def test_numerals_align_without_being_in_the_table():
    """The point of the rule: a number absent from the learned table still aligns."""
    how, got = C.align(A + C.numeral("12"), ["a", "12"], multi={})
    assert how == 4
    assert got == [A, C.numeral("12")]


def test_a_subscript_digit_is_not_a_numeral():
    """`str.isdigit()` is true for `₄` but `int('₄')` raises ValueError, and the corpus
    is full of subscripts: NA₄, SIG₅, EZEN₄. This crashed a full build."""
    for reading in ("₄", "₅", "⁴", "NA₄", "2₄"):
        assert C.numeral(reading) is None, reading


def test_align_survives_subscript_readings():
    assert C.align(A + BA, ["NA₄", "₄"], multi={}) == (1, [A, BA])


# ------------------------------------------------- residue: editorial marks in cu
#
# 4,721 of the codepoints that no sign could claim are `?`, `|` and `°` -- editorial
# annotation that the source put inside the cuneiform string. They are not signs and
# there is no sign for them to belong to. Dropping them from the alignment view loses
# nothing: `cu` still carries the line verbatim.


def test_editorial_marks_in_cu_are_not_points():
    assert C.split_points(A + "?" + BA) == [A, BA]
    assert C.split_points(A + "|" + BA) == [A, BA]
    assert C.split_points(A + "°" + BA) == [A, BA]


def test_a_line_with_editorial_marks_still_aligns():
    assert C.align(A + "?" + BA, ["a", "ba"]) == (1, [A, BA])


def test_the_placeholder_is_still_a_point():
    """▒ stands for a lost sign and must keep counting, unlike the marks above."""
    assert C.split_points(A + C.PLACEHOLDER + BA) == [A, C.PLACEHOLDER, BA]
