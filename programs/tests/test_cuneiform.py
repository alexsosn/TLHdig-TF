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
    assert C.align(A + BA, ["a", "ba"]) == C.Alignment(1, [A, BA], ("zip",))


def test_spacing_and_combining_marks_are_not_points():
    assert C.align(A + " " + BA, ["a", "ba"]).values == [A, BA]


def test_a_compound_logogram_takes_several_codepoints():
    """`MEŠ` is written 𒈨𒌍 -- one reading, two signs, 21,818 observations."""
    got = C.align(A + ME + ESH, ["a", "MEŠ"], multi=MULTI)
    assert got.level == 3
    assert got.values == [A, ME + ESH]


def test_a_three_sign_logogram_works_too():
    got = C.align(A + MULTI["SAGI"], ["a", "SAGI"], multi=MULTI)
    assert got.level == 3 and got.values[1] == MULTI["SAGI"]


def test_a_lacuna_absorbs_its_placeholders():
    got = C.align(A + C.PLACEHOLDER + C.PLACEHOLDER + BA, ["a", "ba"], damaged=True)
    assert got.level == 2
    assert got.values == [A, BA]


def test_placeholders_are_not_absorbed_without_recorded_damage():
    """A surplus placeholder where nothing is marked damaged is unexplained."""
    assert C.align(A + C.PLACEHOLDER + BA, ["a", "ba"], damaged=False) is None


def test_absorbing_more_or_fewer_than_the_surplus_is_refused():
    """Two placeholders but three surplus codepoints: the extra one is not a placeholder,
    so the line is not explained and must not be forced."""
    assert C.align(A + C.PLACEHOLDER + C.PLACEHOLDER + ME + BA, ["a", "ba"],
                   damaged=True) is None


def test_damage_and_a_compound_can_occur_on_one_line():
    got = C.align(A + C.PLACEHOLDER + ME + ESH, ["a", "MEŠ"], damaged=True, multi=MULTI)
    assert got.level == 3
    assert got.values == [A, ME + ESH]


def test_the_strongest_explanation_wins():
    """A line whose counts match and whose readings are all ordinary is level 1.

    This used to say "even if a compound would also fit", and asserted level 1 for
    `MEŠ ba` written 𒈨𒌍. That is the compensating case, not a stronger explanation:
    `MEŠ` takes both codepoints and `ba` is left with none. It is now refused."""
    assert C.align(A + BA, ["a", "ba"], multi=MULTI).level == 1
    assert C.align(ME + ESH, ["MEŠ", "ba"], multi=MULTI) is None


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
    got = C.align(A + C.numeral("12"), ["a", "12"], multi={})
    assert got.level == 4
    assert got.values == [A, C.numeral("12")]


def test_a_subscript_digit_is_not_a_numeral():
    """`str.isdigit()` is true for `₄` but `int('₄')` raises ValueError, and the corpus
    is full of subscripts: NA₄, SIG₅, EZEN₄. This crashed a full build."""
    for reading in ("₄", "₅", "⁴", "NA₄", "2₄"):
        assert C.numeral(reading) is None, reading


def test_align_survives_subscript_readings():
    assert C.align(A + BA, ["NA₄", "₄"], multi={}).values == [A, BA]


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
    assert C.align(A + "?" + BA, ["a", "ba"]).values == [A, BA]


def test_the_placeholder_is_still_a_point():
    """▒ stands for a lost sign and must keep counting, unlike the marks above."""
    assert C.split_points(A + C.PLACEHOLDER + BA) == [A, C.PLACEHOLDER, BA]


# --------------------------------------------------------------- structural constraints
#
# Measured on the shipped build (audit in docs/research-cuneiform-alignment.md §7):
# absorbing "the first N placeholders, wherever they fall" put a legible sign on a shade
# and a shade on a legible sign in 14.1% of the level-2 assignments that the learned
# table can check.  The signature is a swapped pair: `x` gets 𒀭 and `an` gets ▒.
#
# The constraint is structural, never a sign lookup: `▒` and `x` are the same statement
# in two scripts.  Level-1 lines, where the zip is forced and so cannot be argued with,
# measure it both ways -- 98.76% of their placeholders sit on an `x`, and 24 of
# 1,511,993 legible points do.  Being inside a lacuna is NOT used: a restored sign is
# restored in the cuneiform too, so it takes a placeholder only 0.15% of the time.

def test_an_illegible_sign_keeps_its_own_placeholder():
    """The defect this constraint exists for: `x` must not be handed a legible sign."""
    got = C.align(
        C.PLACEHOLDER + A + C.PLACEHOLDER + C.PLACEHOLDER + BA,
        ["x", "a", "ba"], damaged=True,
    )
    assert got.values == [C.PLACEHOLDER, A, BA]


def test_a_legible_sign_is_never_put_on_a_placeholder():
    """`a` is read, so it was there to read; it cannot be the shade.

    An earlier version kept the line and withheld only that position, on the reasoning
    that equal counts force the correspondence. They do not force it, they only make it
    possible, and the corpus says which: on the 996 level-1 lines where a placeholder
    lands on a legible reading, the *other* positions are wrong 14.72% of the time,
    against 0.04% on lines with no such violation. One bad position is evidence about
    the line, not about the position."""
    assert C.align(C.PLACEHOLDER + BA, ["a", "ba"]) is None


def test_an_undecidable_position_is_left_undecided():
    """Two placements are equally valid here, so neither is asserted."""
    got = C.align(
        A + C.PLACEHOLDER + C.PLACEHOLDER + BA, ["a", "x", "ba"], damaged=True,
    )
    assert got.values == [A, C.PLACEHOLDER, BA]      # the shades are interchangeable

    got = C.align(
        A + C.PLACEHOLDER + ME + BA, ["a", "x", "ba"], damaged=True,
    )
    assert got is None            # ME is legible and unclaimed: nothing explains it


def test_a_compound_does_not_certify_the_signs_around_it():
    """A match at the end of the line said nothing about the start, and the start was
    a placeholder handed to a legible reading."""
    assert C.align(C.PLACEHOLDER + ME + ESH, ["a", "MEŠ"], multi=MULTI) is None


def test_damage_is_never_part_of_a_compound_spelling(tmp_path):
    """`a+na -> 𒀀▒𒀀` was learned at 0.986 over 146 observations. It is an artefact
    recurring consistently, not a spelling: the shade is a hole in the tablet."""
    p = tmp_path / "m.tsv"
    p.write_text(f"MEŠ\t{ME + ESH}\t0.99\t100\t101\t2 signs\n"
                 f"a+na\t{A + C.PLACEHOLDER + A}\t0.986\t144\t146\t3 signs\n", encoding="utf8")
    assert C.load_multi(p) == {"MEŠ": ME + ESH}


def test_a_value_that_is_not_a_sign_is_not_assigned():
    """`cu` sometimes carries the Latin digits unrendered. The counts still match, so
    the rest of the zip stands; the digit is simply not a sign anyone can query."""
    got = C.align(A + "5" + BA, ["a", "50", "ba"])
    assert got.level == 1
    assert got.values == [A, None, BA]


def test_the_mechanisms_are_reported_separately():
    """`cu_aligned` alone cannot say whether a level-3 line also absorbed damage; 9,326
    of the 39,689 shipped level-3 lines did."""
    got = C.align(C.PLACEHOLDER + C.PLACEHOLDER + A + ME + ESH, ["x", "a", "MEŠ"],
                  damaged=True, multi=MULTI)
    assert got.level == 3
    assert got.methods == ("damage", "compound")


# ------------------------------------------------------- equal counts are not evidence
#
# The counts can balance by accident: a reading written with two signs is one codepoint
# too many, a reading written with none is one too few, and together they cancel.  The
# zip then runs happily and everything between the two is off by one.
#
# It is not hypothetical.  333 level-1 lines in the previous build carried a reading the
# compound table says takes several codepoints, and 209 of them had been handed the
# compound's *first* codepoint -- `MEŠ` -> 𒈨 rather than 𒈨𒌍, 112 times.  Nothing could
# see it: the one-to-one table cannot judge a reading that is not in it, and a compound
# reading is by construction not in it.
#
#     ŠA DINGIR MEŠ :za am mu ra at ti Ù ŠA KUR URU Ḫat ti      15 readings
#     𒊭 𒀭 𒈨𒌍 ·  𒄠 𒈬 𒊏 𒀜 𒋾 𒅇 𒊭 𒆳 𒌷 𒉺 𒋾              15 codepoints
#
# `MEŠ` needs two and `:za` -- a Glossenkeil, which the cuneiform does not render -- has
# none.  The zip gave 𒈨 to `MEŠ` and 𒌍 to `:za`, splitting one sign across two readings.

def test_equal_counts_are_not_evidence_when_a_compound_is_present():
    """Four readings, four codepoints, and still no valid alignment: `MEŠ` takes two of
    them, which leaves the last reading with nothing."""
    assert C.align(A + ME + ESH + BA, ["a", "MEŠ", "ni", "ba"], multi=MULTI) is None


def test_a_compound_that_does_not_appear_refuses_the_line_anyway():
    """It is tempting to say the table is a measurement, not a law -- `MEŠ` is 𒈨𒌍 99%
    of the time, not always -- and to zip the line where the compound does not appear.

    The corpus refuses that reasoning. On the 130 lines where the expansion succeeded
    with one codepoint per reading, the assignments are wrong 30.64% of the time, against
    0.04% on lines carrying no compound at all. The counts balanced because something
    else on the line was missing a codepoint, not because `MEŠ` shrank."""
    assert C.align(A + ME + BA, ["a", "MEŠ", "ba"], multi=MULTI) is None


def test_a_compound_that_does_appear_is_expanded_not_zipped():
    got = C.align(A + ME + ESH, ["a", "MEŠ"], multi=MULTI)
    assert got.level == 3
    assert got.values == [A, ME + ESH]
