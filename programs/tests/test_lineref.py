"""Line references (plan §4.5, research §5).

    [ "{" fragment "}" ] [ surface ] [ column ] number [ prime ] [ tail ]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import lineref


def p(s):
    return lineref.parse(s)


def test_plain_number():
    r = p("5")
    assert (r.ln, r.prime, r.surface, r.column) == (5, "", "", "")
    assert r.is_line


def test_prime_marks_relative_numbering():
    r = p("5′")
    assert r.ln == 5 and r.prime == "′"


def test_surface_and_roman_column():
    r = p("Vs. II 5′")
    assert (r.surface, r.column, r.ln, r.prime) == ("Vs.", "II", 5, "′")


def test_reverse_and_lowercase_column():
    r = p("rev. iv 12")
    assert (r.surface, r.column, r.ln) == ("rev.", "iv", 12)


def test_named_columns():
    assert p("lk. Kol. 3′").column == "lk. Kol."
    assert p("r. Kol. 3′").column == "r. Kol."
    assert p("l. col. 3′").column == "l. col."


def test_edges_are_surfaces_not_columns():
    assert p("u. Rd. 2").surface == "u. Rd."
    assert p("lk. Rd. 2").surface == "lk. Rd."


def test_fragment_siglum():
    r = p(" {€1} Vs. I 4′")
    assert r.frag == "€1" and r.surface == "Vs." and r.column == "I" and r.ln == 4


def test_composite_fragment_siglum():
    """`€1+2` -- a line concerning several witnesses at once."""
    r = p(" {€1+2} Rs. IV 4")
    assert r.frag == "€1+2"
    assert r.frags == ("€1", "€2")


def test_uncertainty_markers_kept_on_the_surface():
    assert p("Vs.? II 3′").surface == "Vs.?"
    assert p("Rs. III? 1′").column == "III?"


def test_tail_forms():
    assert p("5′a").tail == "a"
    assert p("4/1′").tail == "/1′"
    assert p("5″").prime == "″"


def test_surface_header_without_a_number():
    r = p("Rs.")
    assert not r.is_line and r.surface == "Rs." and r.ln is None


def test_label_is_unique_within_a_document():
    """Level-2 section label must distinguish fragment and column (plan §3.3)."""
    a = p(" {€1} Vs. II 5′")
    b = p(" {€2} Vs. II 5′")
    c = p(" {€1} Vs. III 5′")
    assert a.collabel == "€1 Vs. II"
    assert len({a.collabel, b.collabel, c.collabel}) == 3


def test_lnno_is_the_citation_form():
    assert p(" {€1} Vs. II 5′").lnno == "5′"
    assert p("4/1′").lnno == "4/1′"


def test_raw_is_preserved():
    for s in (" {€1+2} Rs. IV 4", "Vs.? II 3′", "Rs."):
        assert p(s).raw == s


def test_parenthesised_column():
    """`Vs. (II) 5′` -- the column is inferred by the editor, hence the brackets."""
    r = p("Vs. (II) 5′")
    assert r.surface == "Vs." and r.column == "(II)" and r.ln == 5
    assert p("Rs.? (III) 1′").surface == "Rs.?"


def test_lettered_sides():
    for s, want in (("Seite A 1′", "Seite A"), ("side B 2′", "side B"), ("a. 1", "a.")):
        assert p(s).surface == want, s


def test_capitalised_side_variants():
    assert p("Obv. 3′").surface == "Obv."
    assert p("Rev.? 4′").surface == "Rev.?"


def test_kol_prefixed_column():
    r = p("Kol. I 7")
    assert r.column == "Kol. I" and r.ln == 7


def test_column_with_parenthesised_uncertainty():
    assert p("obv. II(?) 5′").column == "II(?)"


def test_capitalised_named_column():
    assert p("R. col. 3′").column == "R. col."
    assert p("re. Kol. 3′").column == "re. Kol."
