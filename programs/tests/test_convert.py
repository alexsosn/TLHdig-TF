"""The CV director (plan §7.7).

Builds a tiny TF dataset from synthetic AOxml and checks the graph shape: node types,
section addressing, analyses as nodes rather than edges, and the empty-token policy.
"""
import sys
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
            if api.F.type.v(cl) == "del":
                in_cluster.update(api.L.d(cl, otype="sign"))
        flagged = {s for s in api.F.otype.s("sign") if api.F.missing.v(s)}
        assert flagged == in_cluster, (name, flagged ^ in_cluster)


def test_marker_at_sign_start_marks_that_sign(tmp_path):
    """`pa-<del_in/>it<del_fin/>` -- every character of 'it' is inside the range.

    Stamping the flag from the state *before* the sign's own markers left it unmarked.
    """
    api = _build_doc(tmp_path, DOC_WHOLE_SIGN, "whole")
    by = {api.F.sym.v(s): s for s in api.F.otype.s("sign")}
    assert api.F.missing.v(by["it"]) == 1
    assert api.F.missing.v(by["pa"]) is None
