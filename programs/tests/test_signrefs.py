"""Reading external sign lists, so they can judge our alignment.

Five lists, four transliteration conventions between them. The normalisation is the
whole difficulty: `SZE3` and `ŠÈ` are the same reading written by different houses, and
a comparison that misses that reports a disagreement where there is agreement.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import signrefs as R


# --------------------------------------------------------------- index marks
#
# A sign value's homophone index is written three ways depending on its size, and every
# list picks one: 1 unmarked, 2 an acute, 3 a grave, 4 and up a subscript digit. ATF
# writes them all as ASCII digits, so `sze3` and `ŠÈ` are the same reading.

def test_the_second_homophone_takes_an_acute():
    assert R.normalise("sza2") == "šá"
    assert R.normalise("SZA2") == "ŠÁ"


def test_the_third_takes_a_grave():
    assert R.normalise("sze3") == "šè"
    assert R.normalise("SZE3") == "ŠÈ"


def test_the_fourth_and_beyond_take_a_subscript():
    assert R.normalise("sig7") == "sig₇"
    assert R.normalise("na4") == "na₄"


def test_the_first_is_unmarked():
    assert R.normalise("sza") == "ša"


def test_the_mark_lands_on_the_last_vowel():
    """`ezen2` is `ezén`, not `ézen`: the accent marks the value, not the first vowel."""
    assert R.normalise("ezen2") == "ezén"
    assert R.normalise("kaskal3") == "kaskàl"


# ------------------------------------------------------------------ digraphs

def test_atf_digraphs_become_their_letters():
    assert R.normalise("sza") == "ša"
    assert R.normalise("s,a") == "ṣa"
    assert R.normalise("t,a") == "ṭa"


def test_h_is_the_hittite_h_in_atf():
    """ATF has no plain `h`; every `h` in these lists is ḫ."""
    assert R.normalise("hu", atf=True) == "ḫu"
    assert R.normalise("HAL", atf=True) == "ḪAL"


def test_h_is_left_alone_when_the_list_already_writes_it():
    assert R.normalise("ḫu") == "ḫu"


# ------------------------------------------------------------------- numbers

def test_a_bare_number_is_not_an_index():
    """`2` is the numeral two, not a homophone index on nothing."""
    for n in ("1", "2", "30", "100"):
        assert R.normalise(n) == n


def test_a_reading_already_normalised_survives_unchanged():
    for r in ("ša", "ḫu", "NA₄", "MEŠ", "ŠÈ", "an", "x"):
        assert R.normalise(r) == r


# --------------------------------------------------------------------- votes

def test_a_reading_carries_the_sources_that_attest_it():
    refs = R.References({
        "an": {"potnia": {"𒀭"}, "nuolenna": {"𒀭"}, "hzl": {"𒀭"}},
        "ku": {"potnia": {"𒆪"}, "nuolenna": {"𒆪"}},
    })
    assert refs.sources("an") == {"potnia", "nuolenna", "hzl"}
    v = refs.verdict("an", "𒀭")
    assert v.support == 3 and v.against == 0


def test_a_glyph_no_source_attests_is_outvoted():
    refs = R.References({"ku": {"potnia": {"𒆪"}, "nuolenna": {"𒆪"}, "hzl": {"𒆪"}}})
    v = refs.verdict("ku", "𒂉")
    assert v.support == 0 and v.against == 3


def test_a_reading_nobody_lists_is_not_a_disagreement():
    refs = R.References({})
    v = refs.verdict("qqq", "𒀭")
    assert v.support == 0 and v.against == 0 and v.unknown


def test_the_lists_may_disagree_with_each_other():
    """`bar` really is written two ways by two houses. That is a fact about the sign,
    not an error, and the verdict has to be able to say so."""
    refs = R.References({"bar": {"nuolenna": {"𒁇"}, "potnia": {"𒈦"}}})
    assert refs.verdict("bar", "𒁇").support == 1
    assert refs.verdict("bar", "𒁇").against == 1
    assert refs.contested("bar")
