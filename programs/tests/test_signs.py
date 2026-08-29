"""Sign tokenisation (plan §3.1, §4.1).

A sign is a maximal run of transliteration characters between '-' or '.' separators,
within one wrapper context.  Markers that interrupt a sign stay inside it at their
exact offset, because TLH brackets cut signs mid-way (research §8.1).

The governing invariant, tested last and hardest: concatenating srcxml + after over the
signs of a word must reproduce the word's exact source bytes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import signs


def toks(xml: str):
    """Tokenise a <w> given as source text; returns the list of Sign objects."""
    return signs.tokenise_word(xml.encode("utf8"))


# ----------------------------------------------------------------- basic splitting

def test_plain_word_splits_on_hyphen():
    got = toks("pa-it")
    assert [s.sym for s in got] == ["pa", "it"]
    assert [s.after for s in got] == ["-", ""]


def test_splits_on_full_stop_too():
    got = toks("DUMU.DUMU")
    assert [s.sym for s in got] == ["DUMU", "DUMU"]
    assert [s.after for s in got] == [".", ""]


def test_single_sign_word():
    got = toks("nu")
    assert len(got) == 1 and got[0].sym == "nu" and got[0].after == ""


# ------------------------------------------------------------------- sign typing

def test_wrappers_set_flags_not_type():
    """'Sumerogram' is orthogonal to 'is an identifiable reading' (plan §4.1)."""
    got = toks("<sGr>DINGIR</sGr>")
    assert got[0].sgr == 1 and got[0].type == "reading"
    got = toks("<aGr>A-NA</aGr>")
    assert all(s.agr == 1 for s in got)
    got = toks("<d>URU</d>")
    assert got[0].det == 1
    got = toks("<num>3</num>")
    assert got[0].num == 1 and got[0].type == "numeral"


def test_signname_type():
    got = toks('<c type="sign">UD</c>')
    assert got[0].type == "signname" and got[0].sym == "UD"


def test_unknown_and_ellipsis_types():
    assert toks("x")[0].type == "unknown"
    assert toks("…")[0].type == "ellipsis"


def test_mixed_wrappers_in_one_word():
    got = toks("<d>GIŠ</d><sGr>KIRI₆</sGr><d>ḪI.A</d>-ia")
    assert [s.sym for s in got] == ["GIŠ", "KIRI₆", "ḪI", "A", "ia"]
    assert [(s.det, s.sgr) for s in got] == [(1, 0), (0, 1), (1, 0), (1, 0), (0, 0)]


# ------------------------------------------------- markers at their exact offsets

def test_marker_between_signs_is_a_boundary():
    got = toks("ur-<laes_in/>ši")
    assert [s.sym for s in got] == ["ur", "ši"]
    assert got[1].markers[0][0] == "laes_in"
    assert got[1].markers[0][1] == 0          # offset 0: before the first character


def test_marker_inside_a_sign_keeps_its_offset():
    """55% of del_fin and 89% of laes_fin sit mid-sign (research §8.1)."""
    got = toks("ḫar<del_fin/>ga")
    assert len(got) == 1 and got[0].sym == "ḫarga"
    tag, off = got[0].markers[0]
    assert tag == "del_fin" and off == 3       # after 'ḫar'


def test_point_markers_recorded():
    got = toks("nu<corr c='?'/>")
    assert got[0].corr == "?"
    got = toks("wi<subscr c='i'/>")
    assert got[0].subscr == "i"


def test_space_becomes_a_count_not_a_sign():
    got = toks('<space c="12"/>a')
    assert len(got) == 1
    assert got[0].sym == "a" and got[0].space_count == 12


# ------------------------------------------------------- the governing invariant

def test_roundtrip_simple():
    src = "<d>M</d>m<del_fin/>ur-<laes_in/>ši-<sGr>DINGIR</sGr><aGr>-LIM</aGr>"
    got = toks(src)
    assert "".join(s.srcxml + s.after for s in got) == src


def test_roundtrip_with_escaped_attribute():
    src = 'a-b<note n="1" c="see &lt;X&gt; here"/>-c'
    got = toks(src)
    assert "".join(s.srcxml + s.after for s in got) == src


def test_roundtrip_empty_word():
    assert toks("") == []


def test_roundtrip_marker_only_word():
    src = "<del_in/>"
    got = toks(src)
    assert "".join(s.srcxml + s.after for s in got) == src


# ------------------------------------------------ no spurious slots (TDD: red first)

def test_wrapper_opening_before_separator_makes_no_empty_sign():
    """`<aGr>-LIM</aGr>`: the '-' joins LIM to the previous sign; the open tag
    belongs to LIM, and must not strand an empty sign carrying only '<aGr>'."""
    src = "<sGr>DINGIR</sGr><aGr>-LIM</aGr>"
    got = toks(src)
    assert [s.sym for s in got] == ["DINGIR", "LIM"]
    assert [s.type for s in got] == ["reading", "reading"]   # no stranded empty
    assert got[0].sgr == 1 and got[1].agr == 1
    # The '-' lives *inside* <aGr> in the source, so it stays in srcxml rather than
    # moving to the previous sign's `after`; hoisting it out would break round-trip.
    assert got[1].srcxml == "<aGr>-LIM</aGr>"
    assert "".join(s.srcxml + s.after for s in got) == src


def test_word_initial_separator_makes_no_empty_sign():
    """A word may open with '-' when it continues the previous one."""
    src = "-z<del_fin/>i"
    got = toks(src)
    assert [s.sym for s in got] == ["zi"]
    assert "".join(s.srcxml + s.after for s in got) == src


def test_no_empty_signs_in_common_shapes():
    for src in (
        "<d>D</d><sGr>UTU</sGr><aGr>-ŠI</aGr>",
        "<num>1</num><aGr>-ŠU</aGr>",
        "<sGr>SÌR</sGr><aGr>-RU</aGr>",
    ):
        got = toks(src)
        assert all(s.type != "empty" for s in got), (src, [s.srcxml for s in got])
        assert "".join(s.srcxml + s.after for s in got) == src


def test_marker_only_word_still_yields_one_sign():
    """Carrying forward must not delete a word that is nothing but a marker."""
    for src in ("<del_in/>", "<space c='4'/>", "<del_fin/><del_in/>"):
        got = toks(src)
        assert got, src
        assert "".join(s.srcxml + s.after for s in got) == src


def test_wrapper_containing_only_a_separator():
    """`pé<sGr>.</sGr>-an`: a wrapper holding nothing but '.' is carried forward, so a
    later separator must join the carry rather than attach to the previous sign --
    otherwise the '-' migrates in front of the wrapper."""
    for src in (
        "pé<sGr>.</sGr>-an",
        "da<sGr>.</sGr>-an",
        "kat-ta<sGr>..</sGr><del_in/></sGr>".replace("</sGr><del_in/></sGr>", "<del_in/></sGr>"),
        "<d>KUR</d>i-šu-wa<sGr>..</sGr>",
    ):
        got = toks(src)
        assert "".join(s.srcxml + s.after for s in got) == src, src
