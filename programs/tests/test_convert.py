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
    # the anchor is marked so it can be excluded from counts
    anchors = [s for s in api.F.otype.s("sign") if api.F.type.v(s) == "empty"]
    assert len(anchors) == 1


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


def test_raw_kept_only_when_the_parse_failed(tmp_path):
    """Every analysis in this document parses, so `raw` should not occur at all --
    TF omits a feature with no values, which is the intended outcome."""
    api = build(tmp_path)
    assert all(api.F.parse_ok.v(a) == 1 for a in api.F.otype.s("analysis"))
    assert "raw" not in set(api.Fall())


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
