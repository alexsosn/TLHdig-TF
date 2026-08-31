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


# --------------------------------------- markers must survive the empty-token filter

def _kept(src: str):
    """Round-trip using only the tokens the converter keeps as slots."""
    got = toks(src)
    return "".join(s.srcxml + s.after for s in got if s.type != "empty")


def test_leading_marker_attaches_to_the_following_sign():
    """`<laes_in/><d>m</d>` -- the marker must not become a droppable empty token."""
    src = "<laes_in/><d>m</d><laes_fin/>I-ni"
    assert _kept(src) == src
    got = [s for s in toks(src) if s.type != "empty"]
    assert got[0].sym == "m"
    assert ("laes_in", 0) in got[0].markers


def test_trailing_marker_attaches_to_the_previous_sign():
    src = "<sGr>GAŠAN</sGr><laes_fin/>"
    assert _kept(src) == src


def test_marker_between_wrappers_survives():
    src = "<del_in/><d>D</d><del_fin/><sGr>NIN.GAL</sGr>"
    assert _kept(src) == src


def test_point_marker_after_a_wrapper_survives():
    src = '<sGr>UZU</sGr><corr c="?"/>'
    assert _kept(src) == src
    got = [s for s in toks(src) if s.type != "empty"]
    assert got[-1].corr == "?"


def test_whole_word_of_markers_still_yields_a_token():
    """With nothing to attach to, the markers stay as one empty token, which the
    converter turns into a layout node rather than dropping."""
    for src in ("<del_in/>", "<del_fin/><del_in/>", '<space c="7"/>'):
        got = toks(src)
        assert got and all(s.type == "empty" for s in got)
        assert "".join(s.srcxml + s.after for s in got) == src


def test_space_between_wrappers_is_a_separator():
    """`<aGr>A-NA</aGr> <sGr>LÚ</sGr>` -- the space joins an Akkadogram to what
    follows.  Treated as content it becomes a droppable empty token."""
    src = "<aGr>A-NA</aGr> <sGr>LÚ</sGr><d>MEŠ</d>"
    assert _kept(src) == src
    got = [s for s in toks(src) if s.type != "empty"]
    assert [s.sym for s in got] == ["A", "NA", "LÚ", "MEŠ"]
    assert got[1].after == " "


def test_trailing_space_token_is_not_dropped():
    src = 'a-b<space c="3"/>'
    assert _kept(src) == src


def test_leading_space_still_becomes_space_count():
    got = [s for s in toks('<space c="12"/>a-b') if s.type != "empty"]
    assert got[0].space_count == 12 and got[0].sym == "a"


def test_known_lossy_list_is_parseable_and_nfc():
    """The gate tolerates exactly the listed files; the list must be readable and its
    paths must match what a Linux checkout has (NFC, see test_paths)."""
    import sys
    import unicodedata
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import check_signs

    known = check_signs.known_lossy()
    assert known, "expected at least the KBo 70.109+ entry"
    for path, reason in known.items():
        assert unicodedata.is_normalized("NFC", path), path
        assert reason, path


# --------------------------------------------------- punctuation is not a sign
#
# The corpus writes `ta(-)la` for an uncertain word division, and `〈 〉` for an
# editorial insertion. Those marks were becoming sign slots: 1,500 slots whose `sym`
# is `˽`, 369 `(`, 200 `(_)`, 122 `)`, 111 `〈`. They inflate every sign count and they
# break cuneiform alignment before it starts, because the cuneiform has no codepoint
# for a bracket. See docs/plan-cuneiform-alignment.md phase 0.


def _syms(xml: bytes):
    return [s.sym for s in signs.tokenise_word(xml)]


def test_uncertain_word_division_is_not_a_sign():
    """`ta(-)la` is two signs with a mark between them, not three."""
    got = [s for s in _syms(b"ta(-)la") if s.strip()]
    assert got == ["ta", "la"], got


def test_editorial_insertion_brackets_are_not_signs():
    got = [s for s in _syms("〈ka〉".encode()) if s.strip()]
    assert got == ["ka"], got


def test_no_slot_is_punctuation_only():
    for xml in (b"ta(-)la", "〈ka〉".encode(), b"a-(b)-c", b"nu(-)za"):
        for s in signs.tokenise_word(xml):
            if s.type == "empty":
                continue
            assert s.sym.strip(" ()〈〉˽_"), (
                f"{xml!r} produced a punctuation-only sign {s.sym!r}"
            )


def test_the_bytes_still_round_trip():
    """Whatever happens to the marks, `srcxml + after` must still rebuild the source --
    nothing may be silently deleted."""
    for xml in (b"ta(-)la", "〈ka〉".encode(), b"a-(b)-c"):
        rebuilt = "".join(s.srcxml + s.after for s in signs.tokenise_word(xml))
        assert rebuilt.encode("utf8") == xml, (rebuilt, xml)
