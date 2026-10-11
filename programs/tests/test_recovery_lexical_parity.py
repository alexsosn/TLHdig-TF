"""RED #150: independently source-authenticated lexical content and morphology.

A correct source opening offset is insufficient when a different lxml node
supplies @trans/@mrp* or a different Expat span supplies the sign body.
Use the ORIGINAL reviewed source plus mechanical-only lexical repairs as the
authority, not the historically repaired full XML tree.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from tlhdig import convert, morph, prepared_source, recovery, repair
from tlhdig.paths import CORPUS, PATCHES

SOURCES = (
    ("CTH 209_XML_TLH/KBo 12.55.xml", 14),
    ("CTH 448_XML_BESRIT/KBo 10.36.xml", 160),
    ("CTH 820_XML_TLH/KUB 48.15.xml", 37),
    ("CTH 832_XML_TLH/UBT 70.xml", 5),
)


@pytest.mark.parametrize("rel,count", SOURCES)
def test_real_tf_words_match_source_lexical_attributes_morphology_and_body(
    tmp_path, rel, count,
):
    prepared = prepared_source.prepare(rel)
    witnesses = recovery.lexical_word_witnesses(prepared)
    assert len(witnesses) == count
    assert len({w.opening_offset for w in witnesses}) == count
    assert sum(w.end_is_implicit for w in witnesses) == 1
    assert sum(not w.end_is_implicit for w in witnesses) == count - 1
    assert all(
        prepared.original_bytes[w.opening_offset:w.opening_offset + 2] == b"<w"
        for w in witnesses
    )
    recovered, = [w for w in witnesses if w.end_is_implicit]
    assert recovered.opening_offset == (
        recovery.reviewed_word_payload(prepared).opening_offset
    )
    if rel.endswith("UBT 70.xml"):
        assert recovered.body_bytes == b'<del_fin/>x-mu<gap c="RASUR"/> \n'
        assert witnesses[-1].body_bytes == b"<del_fin/>x"
        assert witnesses[-1].end_is_implicit is False

    api = convert.build(
        CORPUS, tmp_path / "tf", files=[CORPUS / rel],
        patches=repair.read_manifest(PATCHES),
        terminal_recovery_paths=(rel,),
    )
    assert api is not None
    F, L, E = api.F, api.L, api.E
    graph = {
        F.source_word_open.v(n): (n, F.otype.v(n))
        for n in (*F.otype.s("word"), *F.otype.s("layout"))
        if F.source_word_open.v(n) is not None
    }
    assert len(graph) == count
    for expected in witnesses:
        node, kind = graph[expected.opening_offset]
        attrs = expected.attributes
        if kind == "word":
            assert F.trans.v(node) == attrs.get("trans")
            assert F.mrpsel.v(node) == morph.parse_selection(
                attrs.get("mrp0sel")
            ).raw.strip()
            analyses = morph.analyses(attrs)
            assert F.nanalyses.v(node) == len(analyses)
            assert len(E.analyses.f(node)) == len(analyses)
            # Sign/token source bytes must belong to THIS lexical opening,
            # not merely to some other word with the same output node count.
            raw_sign_body = b"".join(
                ((F.srcxml.v(sign) or "") + (F.after.v(sign) or "")).encode("utf8")
                for sign in L.d(node, otype="sign")
            )
            assert raw_sign_body == expected.body_bytes
            if expected.end_is_implicit:
                assert F.src_span.v(node) is None
            else:
                start, stop = map(int, F.src_span.v(node).split("-"))
                assert start == expected.opening_offset
                assert prepared.original_bytes[start:stop].endswith(b"</w>")
        else:
            assert kind == "layout"
            # The source lexical word is contentless. Its identity must
            # survive as layout without inventing linguistic sign slots.
            assert not any(
                F.source_word_open.v(w) == expected.opening_offset
                for w in F.otype.s("word")
            )


def test_lexical_witness_audit_rejects_swapped_attrs_and_sign_bytes():
    prepared = prepared_source.prepare("CTH 832_XML_TLH/UBT 70.xml")
    words = recovery.lexical_word_witnesses(prepared)
    assert len(words) == 5
    first, second = words[0], words[1]
    assert first.body_bytes != second.body_bytes
    recovery.verify_lexical_pairing(
        prepared, first.opening_offset, first.attributes, first.body_bytes,
    )
    with pytest.raises(recovery.SignatureDrift, match="attribute|trans|mrp"):
        recovery.verify_lexical_pairing(
            prepared, first.opening_offset, second.attributes, first.body_bytes,
        )
    with pytest.raises(recovery.SignatureDrift, match="body|source"):
        recovery.verify_lexical_pairing(
            prepared, first.opening_offset, first.attributes, second.body_bytes,
        )
    with pytest.raises(recovery.SignatureDrift, match="source|opening"):
        recovery.verify_lexical_pairing(
            prepared, first.opening_offset + 1, first.attributes, first.body_bytes,
        )


def test_lexical_witnesses_fail_closed_on_unsigned_or_unreviewed_content():
    prepared = prepared_source.prepare("CTH 832_XML_TLH/UBT 70.xml")
    forged = replace(
        prepared, mechanical_bytes=prepared.mechanical_bytes.replace(
            b"<del_fin/>x-mu", b"<del_fin/>x-mm", 1,
        ),
    )
    with pytest.raises(recovery.SignatureDrift):
        recovery.lexical_word_witnesses(forged)
    with pytest.raises((recovery.NotWordResynchronization, recovery.SignatureDrift)):
        recovery.lexical_word_witnesses(
            prepared_source.prepare("CTH 394_XML_BESRIT/Bo 3353.xml")
        )
