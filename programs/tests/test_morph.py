"""Prototype 2: the mrp grammar, including the two documented traps."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import morph


def test_simple_base_with_det():
    a = morph.parse(1, "murši-DINGIR-LIM-=i-@Muršili@PNm.NOM.SG.C@38.3@m")
    assert a.ok and a.clitic is None
    assert a.base.lemma == "murši-DINGIR-LIM-=i-"
    assert a.base.gloss == "Muršili"
    assert a.base.morph == "PNm.NOM.SG.C"
    assert a.base.stemclass == "38.3"
    assert a.base.det == "m"
    assert a.field4_kind == "stemclass"


def test_empty_det_field_survives():
    """The rstrip('@') trap: 794,637 values end in '@' with an empty det field."""
    a = morph.parse(1, "pai-/pā-@gehen@3SG.PST@I.11@")
    assert a.ok
    assert a.base.stemclass == "I.11"
    assert a.base.det == ""          # present and empty, not absent


def test_separator_space_form():
    a = morph.parse(1, "takk=@entsprechen@3SG.PRS@II.1 += (a)šta@OBPst@@ ")
    assert a.ok and a.clitic is not None
    assert a.base.stemclass == "II.1"
    assert a.clitic.lemma == "(a)šta"
    assert a.clitic.morph == "OBPst"


def test_separator_at_boundary_form():
    """'@+= ' -- the '@' terminates the base's last field, it is not an empty field."""
    a = morph.parse(1, "watarn=aḫḫ-@befehlen@2SG.IMP@II.9@+= ya=an@CNJadd=PPRO.3SG.C.ACC@")
    assert a.ok
    assert a.base.stemclass == "II.9"      # not "II.9@"
    assert a.clitic.lemma == "ya=an"
    assert a.clitic.morph == "CNJadd=PPRO.3SG.C.ACC"


def test_separator_bare_plus_forms():
    a = morph.parse(1, "ann=a/i-@Mutter@{ a → NOM.SG.C}@1.1.1 +@{ R → PPRO.2PL.DAT}@@ ")
    assert a.ok and a.clitic is not None
    assert a.base.stemclass == "1.1.1"
    b = morph.parse(1, "UTU-ŠI@'meine Sonne'@{ a → …:D/L.SG}@+@{ R → PPRO.2PL.DAT}@@ D")
    assert b.ok and b.clitic is not None


def test_alternative_sets_parsed():
    a = morph.parse(1, "nerik=@Nerik@{ a → GN.NOM.SG(UNM)} { b → GN.ACC.SG(UNM)}@39.1@URU/KUR")
    assert a.base.alts == {"a": "GN.NOM.SG(UNM)", "b": "GN.ACC.SG(UNM)"}


def test_field4_pos_without_leading_space():
    """The closed vocabulary decides, not whitespace: 65 values occur both ways."""
    for raw in ("katta@unten@@ ADV@", "katta@unten@@ADV@"):
        a = morph.parse(1, raw)
        assert a.field4_kind == "pos" and a.pos == "ADV", raw


def test_field4_logographic_morphology():
    a = morph.parse(1, "x@y@z@HITT.NOM.SG.C(ABBR)@")
    assert a.field4_kind == "morph" and a.pos == ""


def test_index_read_from_attribute_name():
    got = morph.analyses({"mrp0": "a@b@c@@", "mrp3": "d@e@f@@", "mrp0sel": " 0a "})
    assert [x.index for x in got] == [0, 3]     # mrp0 kept, gaps preserved


def test_selection_forms():
    s = morph.parse_selection(" 1a ")
    assert (s.kind, s.index, s.base_alt) == ("analysis", 1, "a")
    s = morph.parse_selection("2aR")
    assert (s.index, s.base_alt, s.clitic_alt) == (2, "a", "R")
    s = morph.parse_selection("1all")
    assert s.group == "all"
    s = morph.parse_selection("2pl")
    assert (s.index, s.group) == (2, "pl")
    assert morph.parse_selection("DEL").kind == "DEL"
    assert morph.parse_selection("???").kind == "unknown"
    assert morph.parse_selection("").kind == "none"
    assert morph.parse_selection(" 1a 1b ").multiple is True
    # a marker plus a fallback index: keep both, discard neither
    s = morph.parse_selection("??? 0a")
    assert (s.kind, s.index, s.base_alt) == ("unknown", 0, "a")
    s = morph.parse_selection("AKK")
    assert (s.kind, s.index) == ("AKK", None)


def test_plus_inside_lemma_is_not_a_separator():
    """The numeral lemma '+n' was split by an unanchored plus, losing the base."""
    a = morph.parse(1, "+n@+n@QUANcar@33.5 += at=mu@{ R → PPRO.3SG.N.NOM}@@ ")
    assert a.ok
    assert a.base.lemma == "+n"
    assert a.base.gloss == "+n"
    assert a.base.stemclass == "33.5"
    assert a.clitic.lemma == "at=mu"


def test_plus_inside_morph_tag_is_not_a_separator():
    a = morph.parse(1, "mukišn=@Herr der Anrufung@{ a → Anrufung:GEN.SG+Herr:NOM.SG}@30.1@")
    assert a.ok and a.clitic is None
    assert a.base.alts == {"a": "Anrufung:GEN.SG+Herr:NOM.SG"}


def test_clitic_only_analysis():
    """Some words are nothing but an enclitic; the value opens with the separator."""
    a = morph.parse(1, " += ma@CNJctr@@ m")
    assert a.ok and a.note == "clitic-only"
    assert a.base.lemma == ""
    assert a.clitic.lemma == "ma"
    assert a.clitic.morph == "CNJctr"


def test_every_selector_token_is_parsed():
    """`mrp0sel` can name several analyses. Reading only the first discarded the
    editor's other choices on 20,907 words (7,290 naming different analyses)."""
    s = morph.parse_selection(" 1 2a ")
    assert [(x.index, x.base_alt) for x in s.selectors] == [(1, ""), (2, "a")]
    assert s.index == 1 and s.base_alt == ""      # scalars stay "the first"
    assert s.multiple is True


def test_several_alternatives_of_one_analysis():
    s = morph.parse_selection(" 1bR 1bS ")
    assert [(x.index, x.base_alt, x.clitic_alt) for x in s.selectors] == [
        (1, "b", "R"), (1, "b", "S")
    ]


def test_marker_with_fallback_index_still_yields_one_selector():
    s = morph.parse_selection("??? 0a")
    assert s.kind == "unknown"
    assert [(x.index, x.base_alt) for x in s.selectors] == [(0, "a")]


def test_group_selector_is_not_read_as_alternatives():
    s = morph.parse_selection(" 3pl ")
    (one,) = s.selectors
    assert (one.index, one.group, one.base_alt) == (3, "pl", "")


def test_padded_fields_are_stripped():
    """The source pads fields: `mrp1="pai-/pā-@ gehen@3SG.PST@I.11@"`.

    Carried verbatim, ' gehen' and 'gehen' were different values. On `lemma` that split
    3,018 of 28,180 distinct lemmas into duplicates -- 10.7% of the lexicon -- and would
    have keyed thousands of spurious `lex` nodes on a leading space.
    """
    (a,) = morph.analyses({"mrp1": "pai-/pā-@ gehen @3SG.PST@I.11@"})
    assert a.base.lemma == "pai-/pā-"
    assert a.base.gloss == "gehen"
    assert a.normalised is True


def test_unpadded_analysis_is_not_marked_normalised():
    (a,) = morph.analyses({"mrp1": "katta@unten@@ADV@"})
    assert a.base.gloss == "unten"
    assert a.normalised is False


def test_stripping_preserves_the_field_count():
    """Fields are stripped, never the whole value: the empty trailing det field is
    meaningful, so `@` counts must not change."""
    (a,) = morph.analyses({"mrp1": "nu=z@@ CONNn=REFL@@ "})
    assert a.raw == "nu=z@@ CONNn=REFL@@ "
    assert a.base.lemma == "nu=z"


def test_normalisation_runs_before_derived_fields():
    """`alts` and the field-4 classification are derived from morph/stemclass, so they
    must see stripped input or they classify padded values."""
    (a,) = morph.analyses({"mrp1": "x@y@ 3SG.PRS @ ADV @"})
    assert a.base.morph == "3SG.PRS"
    assert a.field4_kind == "pos"
    assert a.pos == "ADV"


def test_clitic_fields_are_stripped_too():
    (a,) = morph.analyses({"mrp1": "ar=@stehen@1SG.PRS.MP@III.1@ += ma@ CNJctr @@ "})
    assert a.clitic is not None
    assert a.clitic.morph == "CNJctr"
    assert a.normalised is True
