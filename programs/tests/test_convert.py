"""The CV director (plan §7.7).

Builds a tiny TF dataset from synthetic AOxml and checks the graph shape: node types,
section addressing, analyses as nodes rather than edges, and the empty-token policy.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert

DOC = """<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>KUB 21.8</docID><meta>
  <creation-date date="2024-12-30T23:01:04"/>
  <kor2 editor="BK" date="2025-01-31T22:33:48"/>
</meta></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<AO:Manuscripts><AO:TxtPubl>KUB 21.8</AO:TxtPubl></AO:Manuscripts>
<lb txtid="KUB 21.8" lnr="Vs. II 1&#8242;" lg="Hit" cu="&#x12079;&#x1212F;"/>
<w><space c="7"/></w>
<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">pa-it</w>
<w trans="nuza" mrp0sel=" 1 " mrp1="nu=z@@ CONNn=REFL@@ ">nu-za</w>
<parsep/>
<lb txtid="KUB 21.8" lnr="Vs. II 2&#8242;" lg="Hit" cu="&#x12000;"/>
<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>
</text></div1></body></AOxml>
"""


def build(tmp_path, **kw):
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(DOC, encoding="utf8")
    out = tmp_path / "tf"
    api = convert.build(src.parent, out, **kw)
    assert api is not None, "conversion failed"
    return api


def test_node_types_present(tmp_path):
    api = build(tmp_path)
    types = set(api.F.otype.all)
    for t in ("sign", "word", "analysis", "line", "column", "surface", "document"):
        assert t in types, t
    assert api.F.otype.slotType == "sign"


def test_words_and_signs(tmp_path):
    api = build(tmp_path)
    words = [api.F.trans.v(w) for w in api.F.otype.s("word")]
    assert "pait" in words and "nuza" in words
    n = api.L.d(api.F.otype.s("word")[0], otype="sign")
    assert len(n) >= 1


def test_analyses_are_nodes_not_edges(tmp_path):
    """A word with two candidate lemmas must keep both (plan §3.4)."""
    api = build(tmp_path)
    kat = next(w for w in api.F.otype.s("word") if api.F.trans.v(w) == "kat")
    got = api.E.analyses.f(kat)
    assert len(got) == 2
    lemmas = sorted(api.F.lemma.v(a) for a in got)
    assert lemmas == ["katta", "katta"]
    assert sorted(api.F.pos.v(a) for a in got) == ["ADV", "POSP"]


def test_analysis_index_is_the_attribute_number(tmp_path):
    api = build(tmp_path)
    kat = next(w for w in api.F.otype.s("word") if api.F.trans.v(w) == "kat")
    assert sorted(api.F.index.v(a) for a in api.E.analyses.f(kat)) == [1, 2]


def test_section_addressing(tmp_path):
    api = build(tmp_path)
    n = api.T.nodeFromSection(("KUB 21.8", "Vs. II", "1′"))
    assert n is not None
    assert api.T.sectionFromNode(n)[0] == "KUB 21.8"


def test_cuneiform_format_actually_renders(tmp_path):
    """The feature being present is not the same as the format working.

    `fmt:line#text-cuneiform={cu}` looked right and shipped for weeks: TF splits the
    *template* on "#", not the format name, so the descend type stayed `sign`, {cu} was
    evaluated on signs that have none, and every line rendered as a run of spaces.
    test_line_carries_cuneiform passed throughout, because the feature was fine.
    """
    api = build(tmp_path)
    T, F = api.T, api.F
    assert "text-cuneiform" in T.formats
    assert T.formats["text-cuneiform"] == "line", "must descend to line, not to the slot type"
    for ln in F.otype.s("line"):
        cu = F.cu.v(ln)
        if cu:
            rendered = T.text(ln, fmt="text-cuneiform")
            assert cu in rendered, f"line {ln}: {rendered!r} does not contain {cu!r}"
            assert rendered.strip(), "rendered as whitespace only"
            break
    else:
        raise AssertionError("fixture has no line with cuneiform")


def test_no_text_format_references_a_provenance_feature(tmp_path):
    """The main dataset must load without the provenance module.

    A format naming an absent feature is not a warning: `loadAll` raises
    `KeyError: 'srcxml'` from tf/core/fabric.py:416. `text-orig-full` is TF's required
    default, so if it referenced `srcxml` the dataset would be unloadable on its own and
    the split would achieve nothing.

    This replaces an earlier test that required an orig/trans pair for Context-Fabric's
    format samples. That pair existed only because `srcxml` and `sym` differed; with
    `srcxml` in the module there is one slot-level string left, and a declared pair
    would show the same value twice.
    """
    from tlhdig import PROVENANCE_FEATURES

    api = build(tmp_path)
    for name, template in convert.OTEXT.items():
        if not name.startswith("fmt:"):
            continue
        for feat in PROVENANCE_FEATURES:
            assert f"{{{feat}}}" not in template, (
                f"format {name} references {feat}, which lives in the provenance module"
            )
    assert "text-orig-full" in api.T.formats, "TF requires this default format"


def test_line_carries_cuneiform(tmp_path):
    api = build(tmp_path)
    lines = api.F.otype.s("line")
    assert any(api.F.cu.v(ln) for ln in lines)


def test_document_features(tmp_path):
    api = build(tmp_path)
    d = api.F.otype.s("document")[0]
    assert api.F.docid.v(d) == "KUB 21.8"
    assert api.F.cth.v(d) == "101"
    assert api.F.subcorpus.v(d) == "TLH"
    assert api.F.lang.v(d) == "Hit"


def test_edit_events_become_nodes(tmp_path):
    api = build(tmp_path)
    edits = api.F.otype.s("edit")
    kinds = {api.F.kind.v(e) for e in edits}
    assert "kor2" in kinds
    e = next(x for x in edits if api.F.kind.v(x) == "kor2")
    assert api.F.editor.v(e) == "BK"


def test_empty_tokens_excluded_by_default(tmp_path):
    """Default policy: contentless tokens are not slots (plan §2.2)."""
    api = build(tmp_path)
    assert all(api.F.type.v(s) != "empty" for s in api.F.otype.s("sign"))


def test_empty_tokens_included_when_asked(tmp_path):
    api = build(tmp_path, keep_empty=True)
    assert any(api.F.type.v(s) == "empty" for s in api.F.otype.s("sign"))


DOC_LAYOUT = DOC.replace(
    '<w><space c="7"/></w>',
    '<w><space c="7"/></w>\n<w><del_in/></w>',
)


def build_layout(tmp_path, **kw):
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(DOC_LAYOUT, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf", **kw)
    assert api is not None
    return api


def test_contentless_words_become_layout_nodes(tmp_path):
    """Excluding empty tokens must not delete the <w> itself (plan §2.2).

    A contentless <w> carries layout and damage markers; dropping it would break
    Contract B while claiming nothing is lost.
    """
    api = build_layout(tmp_path)
    layouts = api.F.otype.s("layout")
    assert len(layouts) == 2
    assert any(api.F.space_count.v(n) == 7 for n in layouts)


def test_layout_nodes_are_not_signs(tmp_path):
    api = build_layout(tmp_path)
    assert all(api.F.type.v(s) != "empty" for s in api.F.otype.s("sign"))
    assert "layout" in set(api.F.otype.all)


DOC_EMPTY = DOC.replace(
    '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">pa-it</w>',
    '<w><del_in/></w>',
).replace(
    '<w trans="nuza" mrp0sel=" 1 " mrp1="nu=z@@ CONNn=REFL@@ ">nu-za</w>', ""
).replace(
    '<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>',
    "",
)


def test_document_with_no_readable_signs_survives(tmp_path):
    """249 corpus documents have no non-empty token at all -- entirely broken tablets.

    Without an anchor slot TF deletes them as unlinked and they vanish from the
    dataset, so a document count would silently be wrong.
    """
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(DOC_EMPTY, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    assert len(api.F.otype.s("document")) == 1
    d = api.F.otype.s("document")[0]
    assert api.F.docid.v(d) == "KUB 21.8"
    # Both <lb> elements survive.  The anchor used to be emitted once per *document*,
    # into the first line only, so every later contentless line was still deleted as
    # unlinked -- 15,434 lines corpus-wide.  It is now once per contentless structure.
    assert len(api.F.otype.s("line")) == 2
    anchors = [s for s in api.F.otype.s("sign") if api.F.type.v(s) == "empty"]
    assert len(anchors) == 2
    assert all(api.F.anchor.v(s) == 1 for s in anchors)


def test_words_carry_a_source_span(tmp_path):
    """Contract A: a word must point back into the bytes it came from, so the full
    mrpN strings stay recoverable without storing them twice."""
    api = build(tmp_path)
    w = next(x for x in api.F.otype.s("word") if api.F.trans.v(x) == "pait")
    span = api.F.src_span.v(w)
    assert span and "-" in span
    d = api.L.u(w, otype="document")[0]
    src = (tmp_path / "corpus" / api.F.src_file.v(d)).read_bytes()
    a, b = (int(x) for x in span.split("-"))
    assert b"pa-it" in src[a:b]


def test_raw_is_kept_exactly_when_the_fields_do_not_reconstruct_the_source(tmp_path):
    """`raw` is the guarantee that normalisation loses nothing.

    It used to be stored only for a failed parse, on the grounds that the verbatim
    string stays recoverable through the word's src_span. That reasoning no longer
    holds: fields are now whitespace-stripped, and src_span is provenance that a
    caller may not have loaded. So `raw` is kept whenever the parsed fields do not
    reconstruct the source -- a failed parse, or a padded field.
    """
    api = build(tmp_path)
    F = api.F
    assert all(F.parse_ok.v(a) == 1 for a in F.otype.s("analysis"))
    # the fixture has `mrp1="nu=z@@ CONNn=REFL@@ "` -- a padded clitic morph field
    withraw = [a for a in F.otype.s("analysis") if F.raw.v(a)]
    assert withraw, "a padded analysis must keep its raw string"
    for a in withraw:
        assert " " in F.raw.v(a), "raw is kept because the source had padding"
    # and the stripped value is what the graph carries
    for a in withraw:
        for feat in ("lemma", "gloss", "morph"):
            v = getattr(F, feat).v(a)
            if v:
                assert v == v.strip(), f"{feat} still padded: {v!r}"


def test_no_raw_for_a_clean_analysis(tmp_path):
    """An unpadded, well-formed analysis reconstructs from its fields, so it costs
    nothing to store -- 1.4M of 1.6M analyses are in this class."""
    doc = DOC.replace(
        '<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>',
        '<w trans="kat" mrp0sel=" 1 " mrp1="katta@unten@ADV@I.1@">ka-at</w>',
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    F = api.F
    kat = [a for a in F.otype.s("analysis") if F.lemma.v(a) == "katta"]
    assert kat and all(not F.raw.v(a) for a in kat)


# ------------------------------------------------------------ src_span after repair

def test_src_span_indexes_the_original_file_after_a_repair(tmp_path):
    """166 repaired files change length; a span must still slice src_file correctly."""
    from tlhdig import repair

    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    broken = DOC.replace("<w><space c=\"7\"/></w>", "<w <w><space c=\"7\"/></w>")
    f = src / "KUB 21.8.xml"
    f.write_bytes(broken.encode("utf8"))
    data = f.read_bytes()
    patches = repair.propose_iteratively(data)
    assert patches, "expected the stray <w to be repairable"
    man = {"CTH 101_XML_TLH/KUB 21.8.xml": (repair.sha256(data), patches)}

    api = convert.build(src.parent, tmp_path / "tf", patches=man)
    assert api is not None
    original = f.read_bytes()
    for w in api.F.otype.s("word"):
        span = api.F.src_span.v(w)
        trans = api.F.trans.v(w)
        if not span or not trans:
            continue
        a, b = (int(x) for x in span.split("-"))
        assert original[a:b].startswith(b"<w"), (trans, original[a:b][:40])


# --------------------------------------------------------------- damage / clusters

DOC_DAMAGE = DOC.replace(
    '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">pa-it</w>',
    '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">'
    'pa<del_in/>-it<del_fin/></w>',
)


def build_damage(tmp_path):
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(DOC_DAMAGE, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    return api


def test_cluster_nodes_are_emitted(tmp_path):
    api = build_damage(tmp_path)
    assert "cluster" in set(api.F.otype.all)
    cl = api.F.otype.s("cluster")
    assert cl and any(api.F.type.v(c) == "del" for c in cl)


def test_cluster_records_intra_sign_offsets(tmp_path):
    """The tokeniser knows a del_in sits after character 2 of 'pa'; the converter
    previously threw that offset away."""
    api = build_damage(tmp_path)
    c = next(x for x in api.F.otype.s("cluster") if api.F.type.v(x) == "del")
    assert api.F.start_offset.v(c) == 2


def test_sign_damage_flag_reflects_state_at_the_sign(tmp_path):
    """A del_in at the *end* of 'pa' must not mark 'pa' itself as missing."""
    api = build_damage(tmp_path)
    signs_by_sym = {api.F.sym.v(s): s for s in api.F.otype.s("sign")}
    assert api.F.missing.v(signs_by_sym["pa"]) is None
    assert api.F.missing.v(signs_by_sym["it"]) == 1


# ------------------------------------------------------------ document accounting

def test_every_source_file_is_accounted_for(tmp_path):
    """sources == converted + explicitly excluded. A silent `continue` used to drop
    52 documents while the build still reported success."""
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "good.xml").write_text(DOC, encoding="utf8")
    (src / "broken.xml").write_text("<AOxml><unclosed>", encoding="utf8")

    ledger = convert.Ledger()
    api = convert.build(src.parent, tmp_path / "tf", ledger=ledger)
    assert api is not None
    assert ledger.total == 2
    assert ledger.converted == 1
    assert ledger.excluded_reasons["unparseable"] == 1
    assert ledger.balances()


def test_ledger_rejects_an_exclusion_not_on_the_allowlist(tmp_path):
    """Arithmetic balance is not a gate: a regression that broke 500 more documents
    would still 'balance'.  The exclusion set for an immutable release is known, so
    the build must check membership, not just the sum."""
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "good.xml").write_text(DOC, encoding="utf8")
    (src / "broken.xml").write_text("<AOxml><unclosed>", encoding="utf8")

    ledger = convert.Ledger(allow={"CTH 101_XML_TLH/other.xml"})
    convert.build(src.parent, tmp_path / "tf", ledger=ledger)
    assert ledger.balances()                       # the sum still adds up
    assert not ledger.allowed()                    # but the file is not on the list
    assert "CTH 101_XML_TLH/broken.xml" in ledger.unexpected()


def test_ledger_accepts_a_listed_exclusion(tmp_path):
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "good.xml").write_text(DOC, encoding="utf8")
    (src / "broken.xml").write_text("<AOxml><unclosed>", encoding="utf8")
    ledger = convert.Ledger(allow={"CTH 101_XML_TLH/broken.xml"})
    convert.build(src.parent, tmp_path / "tf", ledger=ledger)
    assert ledger.allowed() and not ledger.unexpected()


def test_patch_failure_is_never_acceptable(tmp_path):
    """A stale patch hash means the manifest and the corpus disagree; that is a build
    error, not an exclusion."""
    ledger = convert.Ledger(allow={"x.xml"})
    ledger.total = 1
    ledger.exclude("x.xml", "patch_failed")
    assert not ledger.allowed()


def test_clusters_emit_in_a_multi_document_corpus(tmp_path):
    """The tracker was fed a per-document sign counter while cluster slots were
    looked up among global TF slot numbers.  With one document the two coincide, so
    a single-document test cannot catch it; with two they diverge and every cluster
    after the first document is silently dropped.
    """
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    for i in range(3):
        (src / f"doc{i}.xml").write_text(
            DOC_DAMAGE.replace("KUB 21.8", f"KUB 21.{i}"), encoding="utf8"
        )
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    assert len(api.F.otype.s("document")) == 3
    # one del range per document
    dels = [c for c in api.F.otype.s("cluster") if api.F.type.v(c) == "del"]
    assert len(dels) == 3, f"expected one per document, got {len(dels)}"
    assert all(api.F.start_offset.v(c) == 2 for c in dels)


# ------------------------------------------------- cluster extents and damage flags

DOC_ORPHAN = DOC.replace(
    '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">pa-it</w>',
    '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">'
    'pa<del_in/>-it</w>',
)
DOC_WHOLE_SIGN = DOC.replace(
    '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">pa-it</w>',
    '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">'
    'pa-<del_in/>it<del_fin/></w>',
)


def _flagged(api, feat="missing"):
    """Signs carrying a damage flag.  TF omits a feature with no values entirely, so
    `api.F.missing` may not exist -- which is the correct outcome when nothing is
    damaged, not an error."""
    if feat not in set(api.Fall()):
        return set()
    f = getattr(api.F, feat)
    return {s for s in api.F.otype.s("sign") if f.v(s)}


def _build_doc(tmp_path, body, name="d"):
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True, exist_ok=True)
    (src / f"{name}.xml").write_text(body, encoding="utf8")
    api = convert.build(src.parent, tmp_path / f"tf{name}")
    assert api is not None
    return api


def test_orphan_open_cluster_runs_to_the_line_end(tmp_path):
    """An unclosed del_in must cover the rest of its line, not just its own sign.

    All 113,717 orphan-open clusters previously collapsed to one sign, contradicting
    the induced sign flags, which did continue to line end.
    """
    api = _build_doc(tmp_path, DOC_ORPHAN, "orphan")
    c = next(x for x in api.F.otype.s("cluster") if api.F.type.v(x) == "del")
    assert api.F.orphan.v(c) == "open"
    covered = {api.F.sym.v(s) for s in api.L.d(c, otype="sign")}
    assert "it" in covered, covered          # the rest of the line, not just 'pa'
    assert len(api.L.d(c, otype="sign")) > 1


def test_damage_flags_agree_with_cluster_membership(tmp_path):
    """The authoritative span and the convenience flag must never disagree."""
    for body, name in ((DOC_ORPHAN, "a"), (DOC_WHOLE_SIGN, "b"), (DOC_DAMAGE, "c")):
        api = _build_doc(tmp_path, body, name)
        in_cluster = set()
        for cl in api.F.otype.s("cluster"):
            if api.F.type.v(cl) == "del" and api.F.width.v(cl):
                in_cluster.update(api.L.d(cl, otype="sign"))
        assert _flagged(api) == in_cluster, name


def test_marker_at_sign_start_marks_that_sign(tmp_path):
    """`pa-<del_in/>it<del_fin/>` -- every character of 'it' is inside the range.

    Stamping the flag from the state *before* the sign's own markers left it unmarked.
    """
    api = _build_doc(tmp_path, DOC_WHOLE_SIGN, "whole")
    by = {api.F.sym.v(s): s for s in api.F.otype.s("sign")}
    assert api.F.missing.v(by["it"]) == 1
    assert api.F.missing.v(by["pa"]) is None


DOC_ZERO = DOC.replace(
    '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">pa-it</w>',
    '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">'
    'pa-<del_in/><del_fin/>it</w>',
)


def test_zero_width_range_is_kept_as_a_point(tmp_path):
    """`<del_in/><del_fin/>` between two signs encloses nothing, but it is still an
    editorial statement: a break of unknown extent sits here.  Discarding it lost 30%
    of all ranges."""
    api = _build_doc(tmp_path, DOC_ZERO, "zero")
    zeros = [c for c in api.F.otype.s("cluster") if api.F.width.v(c) == 0]
    assert len(zeros) == 1
    assert api.F.type.v(zeros[0]) == "del"


def test_zero_width_ranges_do_not_mark_signs_damaged(tmp_path):
    """A point break encloses no sign, so no sign may be flagged by it -- otherwise
    the flag/cluster invariant breaks again."""
    api = _build_doc(tmp_path, DOC_ZERO, "zero2")
    assert not _flagged(api)


def test_flags_match_positive_width_clusters_only(tmp_path):
    for body, name in ((DOC_ZERO, "z1"), (DOC_ORPHAN, "z2"), (DOC_WHOLE_SIGN, "z3")):
        api = _build_doc(tmp_path, body, name)
        spanned = set()
        for c in api.F.otype.s("cluster"):
            if api.F.type.v(c) == "del" and api.F.width.v(c):
                spanned.update(api.L.d(c, otype="sign"))
        assert _flagged(api) == spanned, name


def test_zero_width_point_does_not_make_a_neighbour_look_damaged(tmp_path):
    """A width=0 cluster is anchored to a sign so TF will not delete it, which means
    a query for `cluster type=del` matches that sign structurally. Anything advertised
    to users must filter width>0, and this test is the regression guard for the
    published query."""
    api = _build_doc(tmp_path, DOC_ZERO, "pt")
    points = [c for c in api.F.otype.s("cluster") if not api.F.width.v(c)]
    assert points, "expected a point break"
    # the naive query -- what the README used to show -- does match
    naive = set()
    for c in api.F.otype.s("cluster"):
        if api.F.type.v(c) == "del":
            naive.update(api.L.d(c, otype="sign"))
    assert naive, "naive query matches the anchor sign"
    # the correct query does not
    correct = set()
    for c in api.F.otype.s("cluster"):
        if api.F.type.v(c) == "del" and api.F.width.v(c):
            correct.update(api.L.d(c, otype="sign"))
    assert not correct
    assert _flagged(api) == correct


def test_boundary_signs_are_reachable_as_edges(tmp_path):
    """start_offset is meaningless without knowing which sign it counts into, and the
    boundary sign is often excluded from oslots by design."""
    api = _build_doc(tmp_path, DOC_DAMAGE, "bnd")
    c = next(x for x in api.F.otype.s("cluster") if api.F.type.v(x) == "del")
    starts = api.E.startsAt.f(c)
    ends = api.E.endsAt.f(c)
    assert starts and ends
    assert api.F.otype.v(starts[0]) == "sign"
    assert api.F.sym.v(starts[0]) == "pa"       # excluded from oslots, still reachable


def test_same_family_reopen_retires_the_previous_range_with_an_extent(tmp_path):
    """A second del_in before the first closes retires the first. It must keep a known
    end, or it collapses to one coordinate exactly like the orphan bug did."""
    from tlhdig import brackets as B

    t = B.Tracker()
    t.start_line(1)
    B.feed(t, "del_in", 10, 0)
    B.feed(t, "del_in", 14, 0)          # reopen: retires the first
    B.feed(t, "del_fin", 20, 1)
    t.finish(30, 2)
    first = [c for c in t.clusters if c.start_sign == 10]
    assert len(first) == 1
    assert first[0].end_sign is not None, "retired range lost its extent"
    assert first[0].end_sign <= 14


def test_ledger_checks_the_reason_not_just_the_path(tmp_path):
    """A file listed as `unparseable` that starts failing for a different reason is a
    change in behaviour, not a known exclusion."""
    led = convert.Ledger(allow={"a.xml": "unparseable"})
    led.total = 1
    led.exclude("a.xml", "no_text_element")
    assert led.unexpected() == ["a.xml"]
    led2 = convert.Ledger(allow={"a.xml": "unparseable"})
    led2.total = 1
    led2.exclude("a.xml", "unparseable")
    assert led2.unexpected() == []


# ------------------------------------------------------------------- Contract B

DOC_B = """<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>KBo 1.1</docID><meta>
  <creation-date date="2024-01-01T00:00:00"/>
  <annotation><annot editor="BK" date="2025-01-01"/><annot editor="CS" date="2025-02-02"/></annotation>
  <neu><kor2 editor="JD" date="2025-03-03"/></neu>
</meta></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<AO:Manuscripts><AO:TxtPubl nr="&#8364;1">KBo 1.1</AO:TxtPubl><AO:TxtPubl nr="&#8364;2">KBo 1.2</AO:TxtPubl>
<AO:InvNr>Bo 1234</AO:InvNr><AO:DirectJoin>KBo 1.3</AO:DirectJoin></AO:Manuscripts>
<lb txtid="KBo 1.1" lnr=" {&#8364;1} Vs. I 1" lg="Hit" cu="&#x12000;"/>
<w trans="nu" mrp0sel=" 1 " mrp1="nu=@und@@ CNJ@">nu<note n="1" c="a remark"/></w>
<lb txtid="KBo 1.2" lnr=" {&#8364;2} Vs. I 2" lg="Hit" cu="&#x12001;"/>
<w trans="za" mrp0sel=" 1 " mrp1="za=@x@@ CNJ@">za</w>
</text></div1></body></AOxml>
"""


def test_notes_become_nodes_anchored_to_a_sign(tmp_path):
    api = _build_doc(tmp_path, DOC_B, "note")
    notes = api.F.otype.s("note")
    assert len(notes) == 1
    assert api.F.n.v(notes[0]) == "1"
    assert "a remark" in api.F.c.v(notes[0])
    target = api.E.noteref.f(notes[0])
    assert target and api.F.otype.v(target[0]) == "sign"


def test_fragments_from_the_manuscript_block(tmp_path):
    api = _build_doc(tmp_path, DOC_B, "frag")
    frags = api.F.otype.s("fragment")
    sigla = {api.F.frag.v(f) for f in frags}
    assert sigla == {"€1", "€2"}
    pub = {api.F.txtpubl.v(f) for f in frags}
    assert pub == {"KBo 1.1", "KBo 1.2"}


def test_lines_link_to_their_witness(tmp_path):
    """lnr carries the siglum, so a line in a composite tablet knows its witness."""
    api = _build_doc(tmp_path, DOC_B, "wit")
    for ln in api.F.otype.s("line"):
        w = api.E.witness.f(ln)
        assert w, api.F.lnr.v(ln)
        assert api.F.otype.v(w[0]) == "fragment"


def test_joins_are_recorded(tmp_path):
    api = _build_doc(tmp_path, DOC_B, "join")
    d = api.F.otype.s("document")[0]
    assert "KBo 1.3" in (api.F.directjoin.v(d) or "")


def test_nested_editorial_events_are_captured(tmp_path):
    """`<annotation>` wraps the annot events and `<neu>` wraps others; iterating only
    the direct children of <meta> missed a third of all events."""
    api = _build_doc(tmp_path, DOC_B, "edit")
    kinds = Counter(api.F.kind.v(e) for e in api.F.otype.s("edit"))
    assert kinds["annot"] == 2
    assert kinds["kor2"] == 1
    editors = {api.F.editor.v(e) for e in api.F.otype.s("edit")}
    assert {"BK", "CS", "JD"} <= editors


def test_docgroup_links_records_of_the_same_manuscript(tmp_path):
    """docid is manuscript identity, not record identity: a Sammeltafel is edited
    under several CTH numbers."""
    src = tmp_path / "corpus"
    for cth in ("CTH 1_XML_HAnn", "CTH 18_XML_HAnn"):
        d = src / cth
        d.mkdir(parents=True)
        (d / "KUB 26.71.xml").write_text(DOC_B.replace("KBo 1.1", "KUB 26.71"), encoding="utf8")
    api = convert.build(src, tmp_path / "tfdg")
    assert api is not None
    groups = api.F.otype.s("docgroup")
    assert len(groups) == 1
    assert api.F.nrecords.v(groups[0]) == 2
    docs = api.F.otype.s("document")
    assert len(docs) == 2
    for d in docs:
        assert api.E.edition.f(d)


def test_edges_are_never_attached_to_a_slotless_node(tmp_path):
    """A node with no slots and an edge crashes TF 13.1.0 in _removeUnlinked
    (walker.py:1425 — see handoff/TF-WALKER-BUG-HANDOFF.md). Empty lines are common
    in damaged documents, so witness edges must skip them."""
    body = DOC_B.replace(
        '<w trans="za" mrp0sel=" 1 " mrp1="za=@x@@ CNJ@">za</w>', ""
    )  # second line now has no words at all
    api = _build_doc(tmp_path, body, "slotless")
    assert api is not None, "build crashed on a slotless node carrying an edge"
    for ln in api.F.otype.s("line"):
        if api.E.witness.f(ln):
            assert api.L.d(ln, otype="sign"), "witness edge on a line with no slots"


DOC_STRAY_W = DOC.replace(
    '<body><div1 type="transliteration">',
    '<body><div1 type="transliteration"><w trans="STRAY">zz</w>',
)


def test_word_spans_pair_with_the_right_elements(tmp_path):
    """427 spans in 30 files sit outside <text>, under <div1>. Pairing the nth element
    under <text> with the nth span in the whole file shifted every later pairing, so
    words were tokenised from another word's bytes."""
    api = _build_doc(tmp_path, DOC_STRAY_W, "stray")
    for w in api.F.otype.s("word"):
        trans = api.F.trans.v(w)
        syms = "".join(api.F.sym.v(s) for s in api.L.d(w, otype="sign"))
        if trans == "pait":
            assert "pa" in syms and "it" in syms, syms
        if trans == "nuza":
            assert "nu" in syms, syms


def test_nested_words_are_not_tokenised_twice(tmp_path):
    """235 <w> sit inside another <w>; the outer word's bytes already contain them, so
    feeding both double-counted 108 open and 107 close markers."""
    body = DOC.replace(
        '<w trans="nuza" mrp0sel=" 1 " mrp1="nu=z@@ CONNn=REFL@@ ">nu-za</w>',
        '<w trans="nuza" mrp0sel=" 1 " mrp1="nu=z@@ CONNn=REFL@@ ">nu<w><del_in/>za</w></w>',
    )
    api = _build_doc(tmp_path, body, "nested")
    dels = [c for c in api.F.otype.s("cluster") if api.F.type.v(c) == "del"]
    assert len(dels) == 1, f"expected one del range, got {len(dels)}"


def test_markers_outside_a_word_still_reach_the_tracker(tmp_path):
    """647+ markers sit directly under <text>, not inside any <w>. The converter only
    fed markers found while tokenising words, so those were dropped entirely."""
    body = DOC.replace(
        '<w trans="nuza" mrp0sel=" 1 " mrp1="nu=z@@ CONNn=REFL@@ ">nu-za</w>',
        '<del_in/><w trans="nuza" mrp0sel=" 1 " mrp1="nu=z@@ CONNn=REFL@@ ">nu-za</w><del_fin/>',
    )
    api = _build_doc(tmp_path, body, "outside")
    dels = [c for c in api.F.otype.s("cluster") if api.F.type.v(c) == "del"]
    assert dels, "marker outside <w> produced no cluster"


DOC_EARLY = DOC.replace(
    '<w><space c="7"/></w>',
    '<w><del_in/></w><w><space c="7"/></w>',
)


def test_marker_before_the_first_slot_is_not_dropped(tmp_path):
    """9,060 markers are fed before their document has any slot -- a line that opens
    with a break, before any readable sign. The resulting cluster had start_sign=None
    and emission discarded it, losing the marker entirely."""
    api = _build_doc(tmp_path, DOC_EARLY, "early")
    dels = [c for c in api.F.otype.s("cluster") if api.F.type.v(c) == "del"]
    assert dels, "cluster dropped for a marker preceding the first slot"
    c = dels[0]
    assert api.F.from_open_marker.v(c) == 1
    assert api.L.d(c, otype="sign"), "cluster covers no slots"


def test_damage_in_a_document_with_no_readable_signs_survives(tmp_path):
    """A wholly broken tablet gets one artificial anchor slot. That slot was never
    registered in slot_len, so the boundary rule (offset >= len) discarded any cluster
    touching it and the zero-width fallback then rejected it as 'not a real sign' --
    losing every marker in such documents."""
    body = DOC.replace(
        '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">pa-it</w>',
        "<w><del_in/></w>",
    ).replace(
        '<w trans="nuza" mrp0sel=" 1 " mrp1="nu=z@@ CONNn=REFL@@ ">nu-za</w>', ""
    ).replace(
        '<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>',
        "<w><del_fin/></w>",
    )
    api = _build_doc(tmp_path, body, "anchoronly")
    assert len(api.F.otype.s("document")) == 1
    dels = [c for c in api.F.otype.s("cluster") if api.F.type.v(c) == "del"]
    assert dels, "all damage lost in a document with no readable signs"


def test_markers_in_a_word_before_the_first_line_are_kept(tmp_path):
    """A word can precede the first <lb>. The converter skipped such words -- and
    returned before feeding their markers, so the damage they carried vanished."""
    body = DOC.replace(
        "<lb txtid=\"KUB 21.8\" lnr=\"Vs. II 1&#8242;\" lg=\"Hit\" cu=\"&#x12079;&#x1212F;\"/>",
        '<w trans="pre" mrp0sel=" 1 " mrp1="x@y@z@@ ">a<del_in/>b</w>'
        "<lb txtid=\"KUB 21.8\" lnr=\"Vs. II 1&#8242;\" lg=\"Hit\" cu=\"&#x12079;&#x1212F;\"/>",
    )
    api = _build_doc(tmp_path, body, "preline")
    dels = [c for c in api.F.otype.s("cluster") if api.F.type.v(c) == "del"]
    assert dels, "marker in a pre-line word was never fed to the tracker"


def test_markers_on_empty_tokens_inside_a_real_word_are_fed(tmp_path):
    """A word can hold both readable signs and marker-only tokens. The converter fed
    markers only from the tokens it keeps as slots, so those on empty tokens vanished
    -- the last source of marker loss, and the one that survives in heavily nested
    documents such as KUB 12.24."""
    body = DOC.replace(
        '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">pa-it</w>',
        '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">'
        'pa-it<w><del_in/></w><w><del_fin/></w></w>',
    )
    api = _build_doc(tmp_path, body, "emptytok")
    dels = [c for c in api.F.otype.s("cluster") if api.F.type.v(c) == "del"]
    assert dels, "markers on an empty token inside a real word were dropped"


def test_build_can_skip_the_post_walk_load(tmp_path):
    """build.py compacts right after the walk, which invalidates any cache TF
    compiles here; on the full corpus that load costs ~35 minutes of discarded work."""
    src = tmp_path / "c" / "doc.xml"
    src.parent.mkdir(parents=True)
    src.write_text(DOC, encoding="utf8")
    out = tmp_path / "tf"
    assert convert.build(src.parent, out, load=False) is True
    assert (out / "otype.tf").exists()
    assert (out / "oslots.tf").exists()
    assert not (out / ".tf").exists()


def test_contentless_line_inside_a_readable_document_survives(tmp_path):
    """The narrower case the document-level anchor never covered.

    A tablet that reads fine except for one wholly broken line used to lose that line
    entirely: it got no slots, so TF deleted it as unlinked. The line still exists in
    the source and its absence silently shifts every line count for that document.
    """
    doc = DOC.replace(
        '<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>',
        "<w><del_in/></w>",
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    F, L = api.F, api.L
    assert len(F.otype.s("line")) == 2, "the broken line must survive"
    # the readable line keeps real signs; the broken one is held open by one anchor
    per_line = {ln: L.d(ln, otype="sign") for ln in F.otype.s("line")}
    assert sorted(len(v) for v in per_line.values())[0] == 1
    anchors = [s for s in F.otype.s("sign") if F.anchor.v(s) == 1]
    assert len(anchors) == 1


def test_note_on_a_contentless_word_survives(tmp_path):
    """3,848 notes -- 31.7% of the corpus's -- were lost this way.

    Notes were materialised only inside the loop over tokens that become slots, so a
    <note> attached to a wholly broken word went out with the discarded token. Exactly
    the marker-loss defect, one field over.
    """
    doc = DOC.replace(
        '<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>',
        '<w><del_in/><note n="7" c="broken here"/></w>',
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    notes = api.F.otype.s("note")
    assert len(notes) == 1, "the note on the contentless word must survive"
    assert api.F.n.v(notes[0]) == "7"


def test_note_before_any_slot_is_not_dropped(tmp_path):
    """A note on the first, contentless word has no preceding slot to attach to."""
    doc = DOC.replace(
        '<w><space c="7"/></w>',
        '<w><note n="1" c="opening remark"/></w>',
    ).replace(
        '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">pa-it</w>',
        '<w trans="pait" mrp0sel=" 1 " mrp1="pai-/p&#257;-@gehen@3SG.PST@I.11@">pa-it</w>',
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    assert len(api.F.otype.s("note")) == 1


def test_fragment_covers_its_own_lines_not_the_document_start(tmp_path):
    """Every fragment used to get `{slots[0]}` -- the document's first sign -- while the
    code comment claimed it covered the lines that cite it. Slot-based containment
    queries therefore returned the same wrong answer for every witness."""
    api = _build_doc(tmp_path, DOC_B, "fragext")
    F, L = api.F, api.L
    covered = {F.frag.v(f): set(L.d(f, otype="sign")) for f in F.otype.s("fragment")}
    assert set(covered) == {"\u20ac1", "\u20ac2"}
    a, b = covered["\u20ac1"], covered["\u20ac2"]
    assert a and b, "each fragment must cover the signs of its own lines"
    assert not (a & b), "these witnesses cite disjoint lines and must not overlap"
    # and the coverage must match the line each witness actually cites
    for ln in F.otype.s("line"):
        (fn,) = api.E.witness.f(ln)
        assert set(L.d(ln, otype="sign")) <= covered[F.frag.v(fn)]


def test_note_outside_any_word_is_collected(tmp_path):
    """419 notes sit outside <w> -- 398 directly under <text>. Only tokenised words fed
    the note collector, so the walk never saw them."""
    doc = DOC.replace("<parsep/>", '<note n="42" c="editorial aside"/><parsep/>')
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    ns = {api.F.n.v(n) for n in api.F.otype.s("note")}
    assert "42" in ns


def test_contentless_colon_survives(tmp_path):
    """start_colon terminated the previous colon directly, bypassing the anchor in
    _close(), so a <clb> with no readable sign was deleted as unlinked."""
    doc = DOC.replace(
        "<parsep/>",
        '<clb id="1" nr="1"/><w><del_in/></w><clb id="2" nr="2"/>',
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    assert len(api.F.otype.s("colon")) == 2


def _sel_doc(sel: str) -> str:
    return DOC.replace(
        '<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>',
        f'<w trans="kat" mrp0sel="{sel}" mrp1="katta@unten@@ ADV@" '
        f'mrp2="katta@unter@@ POSP@" mrp3="katta@bei@@ POSP@">ka-at</w>',
    )


def test_two_selected_analyses_both_get_an_edge(tmp_path):
    """`mrp0sel="1 2a"` selects two analyses. Only the first used to get a `selected`
    edge, so the graph asserted a single reading the editor never claimed."""
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(_sel_doc("1 2a"), encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    F, E = api.F, api.E
    w = [n for n in F.otype.s("word") if F.trans.v(n) == "kat"][0]
    picked = {F.index.v(t): v for t, v in E.selected.f(w)}
    assert picked == {1: "1", 2: "2a"}
    assert F.nselected.v(w) == 2


def test_two_alternatives_of_one_analysis_are_both_kept(tmp_path):
    """`1bR 1bS` picks two alternatives of analysis 1. TF stores one value per
    (word, analysis) pair, so they are joined rather than one overwriting the other."""
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(_sel_doc("1bR 1bS"), encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    F, E = api.F, api.E
    w = [n for n in F.otype.s("word") if F.trans.v(n) == "kat"][0]
    picked = {F.index.v(t): v for t, v in E.selected.f(w)}
    assert picked == {1: "1bR 1bS"}
    assert F.nselected.v(w) == 1


def test_single_selector_is_unchanged(tmp_path):
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(_sel_doc("2a"), encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    F, E = api.F, api.E
    w = [n for n in F.otype.s("word") if F.trans.v(n) == "kat"][0]
    assert {F.index.v(t): v for t, v in E.selected.f(w)} == {2: "2a"}


def test_no_selected_edge_carries_an_empty_value(tmp_path):
    """A None among real values in a valued edge feature corrupts the file.

    TF writes a valued edge line as `from<TAB>to<TAB>value`, but also allows an implicit
    `from`, so a two-field line is ambiguous. A None-valued edge wrote `24<TAB>7`, which
    the reader took as (implicit from, to=24, value="7") -- and adding one valued
    selector silently deleted every other word's `selected` edge. Hence: every selected
    edge carries the selector token that produced it, and none is ever empty.
    """
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(_sel_doc("2a"), encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    F, E = api.F, api.E
    seen = 0
    for w in F.otype.s("word"):
        for target, value in E.selected.f(w) or ():
            seen += 1
            assert value, f"word {w} -> {target} has an empty selected value"
    # all three words carry a selector, and every one survived
    assert seen == 3, "a valued edge on one word must not delete the others"


def test_an_empty_word_element_still_becomes_a_node(tmp_path):
    """`<w></w>` occurs 297 times. It tokenises to nothing, and the converter returned
    without emitting either a `word` or a `layout`, so the element left no trace at all
    -- it did not even appear in a count."""
    doc = DOC.replace(
        '<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>',
        "<w></w>",
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    F = api.F
    # three <w>: the indent, "pa-it"/"nu-za" words, and the empty one
    spans = [F.src_span.v(n) for n in F.otype.s("layout")]
    assert any(s for s in spans), "the empty word must carry its source span"
    assert len(F.otype.s("word")) + len(F.otype.s("layout")) == 4


def test_lex_nodes_group_occurrences_by_lemma_and_sense(tmp_path):
    """A `lex` node is one (lemma, gloss) pair -- one sense of one lemma.

    The gloss is part of the key because 2,670 lemmas are genuinely polysemous:
    LUGAL is König, König werden, Königtum and königlicher Status, and collapsing
    those onto one node would assert an identity the source does not.
    """
    doc = DOC.replace(
        '<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>',
        '<w trans="kat" mrp0sel=" 1 " mrp1="katta@unten@ADV@I.1@">ka-at</w>'
        '<w trans="kat2" mrp0sel=" 1 " mrp1="katta@unter@POSP@I.1@">ka-at</w>',
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    F, E = api.F, api.E
    lex = F.otype.s("lex")
    senses = {(F.lemma.v(x), F.gloss.v(x)) for x in lex}
    assert ("katta", "unten") in senses
    assert ("katta", "unter") in senses, "two senses of one lemma are two lex nodes"
    # every analysis with a lemma reaches exactly one lex node
    for a in F.otype.s("analysis"):
        if F.lemma.v(a):
            target = E.lexeme.f(a)
            assert len(target) == 1
            assert F.otype.v(target[0]) == "lex"
            assert F.lemma.v(target[0]) == F.lemma.v(a)


def test_lex_occurrence_count_is_recorded(tmp_path):
    api = build(tmp_path)
    F = api.F
    for x in F.otype.s("lex"):
        assert F.noccs.v(x) >= 1


def test_lex_slots_are_an_anchor_not_an_extent(tmp_path):
    """Documented explicitly because the `fragment` node made the opposite mistake:
    its comment claimed an extent while the code gave every fragment the document's
    first sign. A lexeme's attestations are scattered, so oslots here is deliberately
    one anchor slot and containment must be read through the `lexeme` edge."""
    api = build(tmp_path)
    F, L = api.F, api.L
    for x in F.otype.s("lex"):
        assert len(L.d(x, otype="sign")) == 1


def test_unmodelled_inline_tags_are_named_on_the_sign(tmp_path):
    """`othertags` is what makes the provenance split lossless.

    149 signs contain an inline element with no dedicated feature -- `ras_X`,
    `AkkGLOS`, `PARSER_ERROR`, the mistyped `del_iin`, leaked ODF styling. Their text
    reaches `sym`, but the tag identity lived only in `srcxml`, so moving `srcxml` to
    the provenance module would have destroyed it.
    """
    doc = DOC.replace(
        '<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>',
        '<w trans="kat" mrp0sel=" 1 " mrp1="katta@unten@ADV@I.1@">ka<ras_X/>-at</w>',
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    F = api.F
    tagged = [s for s in F.otype.s("sign") if F.othertags.v(s)]
    assert tagged, "the ras_X must be recorded on its sign"
    assert "ras_X" in F.othertags.v(tagged[0])


def test_modelled_tags_do_not_appear_in_othertags(tmp_path):
    """A wrapper or damage marker has a feature of its own; naming it again would make
    `othertags` a duplicate rather than a record of what is otherwise unrecorded."""
    doc = DOC.replace(
        '<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>',
        '<w trans="kat" mrp0sel=" 1 " mrp1="katta@unten@ADV@I.1@">'
        '<sGr>ka</sGr><ras_X/><del_in/>-at</w>',
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    F = api.F
    tagged = [s for s in F.otype.s("sign") if F.othertags.v(s)]
    assert tagged, "the fixture must produce at least one othertags value"
    for s in tagged:
        for tag in F.othertags.v(s).split():
            assert tag.split(":")[-1] not in ("sGr", "aGr", "d", "num", "del_in",
                                              "laes_in", "corr", "w"), F.othertags.v(s)


def test_cuneiform_is_laid_out_per_sign_when_counts_match(tmp_path):
    """`cu` is one string for a whole line, so the corpus could not be queried by
    grapheme. Where the codepoint count equals the sign count they are zipped."""
    doc = DOC.replace(
        '<lb txtid="KUB 21.8" lnr="Vs. II 1&#8242;" lg="Hit" cu="&#x12079;&#x1212F;"/>',
        '<lb txtid="KUB 21.8" lnr="Vs. II 1&#8242;" lg="Hit" cu="&#x12000;&#x12001;&#x12002;&#x12003;"/>',
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    F, L = api.F, api.L
    aligned = [ln for ln in F.otype.s("line") if F.cu_aligned.v(ln) == 1]
    assert aligned, "the four-codepoint line has four signs and must align"
    ln = aligned[0]
    anch = F.anchor if "anchor" in set(api.Fall()) else None
    signs = [s for s in L.d(ln, otype="sign") if not (anch and anch.v(s) == 1)]
    got = [F.cu_sign.v(s) for s in signs]
    assert all(got), "every sign on an aligned line carries one codepoint"
    assert "".join(got) == "\U00012000\U00012001\U00012002\U00012003"


def test_a_line_whose_counts_differ_gets_no_cu_sign(tmp_path):
    """Absence must mean unknown, not 'no sign'. A line that does not align is marked,
    so a query can never silently mix aligned and unaligned material."""
    doc = DOC.replace(
        '<lb txtid="KUB 21.8" lnr="Vs. II 1&#8242;" lg="Hit" cu="&#x12079;&#x1212F;"/>',
        '<lb txtid="KUB 21.8" lnr="Vs. II 1&#8242;" lg="Hit" cu="&#x12000;"/>',
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    F, L = api.F, api.L
    bad = [ln for ln in F.otype.s("line") if F.cu_aligned.v(ln) == 0]
    assert bad, "the one-codepoint line has more signs and must not align"
    has_cs = "cu_sign" in set(api.Fall())
    for ln in bad:
        for s in L.d(ln, otype="sign"):
            assert not (has_cs and F.cu_sign.v(s))


def test_anchor_slots_are_excluded_from_alignment(tmp_path):
    """An anchor is a slot we invented to keep a contentless line alive; it corresponds
    to no cuneiform, so counting it would shift every sign after it."""
    doc = DOC.replace(
        '<w trans="kat" mrp0sel=" " mrp1="katta@unten@@ ADV@" mrp2="katta@unter@@ POSP@">ka-at</w>',
        "<w><del_in/></w>",
    )
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 21.8.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    F = api.F
    assert "anchor" in set(api.Fall()), "the fixture must produce an anchor"
    for s in F.otype.s("sign"):
        if F.anchor.v(s) == 1:
            cs = F.cu_sign.v(s) if "cu_sign" in set(api.Fall()) else None
            assert not cs, "an anchor must never receive a codepoint"


# ------------------------------------------------ phase 1: damage placeholders
#
# 39.2% of the gaps between anchors are a codepoint with no sign, and 82% of those are
# U+2592 MEDIUM SHADE. Cuneiform writes one placeholder per lost sign; transliteration
# writes one bracketed lacuna for the whole gap. Two conventions for the same fact.
# See docs/plan-cuneiform-alignment.md phase 1.

DOC_LACUNA = """<?xml version="1.0" encoding="UTF-8"?>
<AOxml xmlns:AO="http://hethiter.net/ns/AO/1.0">
<AOHeader><docID>KUB 1.1</docID><meta>
  <creation-date date="2024-01-01T00:00:00"/>
</meta></AOHeader>
<body><div1 type="transliteration"><text xml:lang="Hit">
<lb txtid="KUB 1.1" lnr="Vs. I 1" lg="Hit" cu="&#x12000;&#x2592;&#x2592;&#x12040;"/>
<w trans="a" mrp0sel=" 1 " mrp1="a@x@@ ADV@">a</w>
<w><del_in/><del_fin/></w>
<w trans="ba" mrp0sel=" 1 " mrp1="ba@y@@ ADV@">ba</w>
</text></div1></body></AOxml>
"""


def test_a_lacuna_absorbs_its_placeholders(tmp_path):
    """`a ... ba` with two lost signs between: cuneiform has 𒀀▒▒𒁀, four codepoints
    against two signs. The line must align, the two signs taking 𒀀 and 𒁀 and the
    placeholders being attributed to the damage rather than blocking the line."""
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 1.1.xml").write_text(DOC_LACUNA, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    assert api is not None
    F, L = api.F, api.L
    (ln,) = F.otype.s("line")
    assert F.cu_aligned.v(ln) == 2, "aligned by resolving damage placeholders"
    got = {F.sym.v(s): F.cu_sign.v(s) for s in L.d(ln, otype="sign") if F.sym.v(s)}
    assert got == {"a": "\U00012000", "ba": "\U00012040"}


def test_a_placeholder_outside_damage_does_not_align(tmp_path):
    """A surplus placeholder where nothing is marked damaged is unexplained, and an
    unexplained line stays unaligned rather than being forced."""
    doc = DOC_LACUNA.replace("<w><del_in/><del_fin/></w>", "")
    src = tmp_path / "corpus" / "CTH 101_XML_TLH"
    src.mkdir(parents=True)
    (src / "KUB 1.1.xml").write_text(doc, encoding="utf8")
    api = convert.build(src.parent, tmp_path / "tf")
    (ln,) = api.F.otype.s("line")
    assert api.F.cu_aligned.v(ln) == 0
