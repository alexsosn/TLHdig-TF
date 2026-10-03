"""Phase-1 TDD contract for shared prepared-source recovery (#12)."""
from __future__ import annotations

from hashlib import sha256

from tlhdig import prepared_source, repair
from tlhdig.paths import CORPUS, PATCHES


def _manifest_entry(rel: str):
    return repair.read_manifest(PATCHES)[rel]


def _raw(rel: str) -> bytes:
    return (CORPUS / rel).read_bytes()


def test_wrapper_crossing_keeps_delayed_original_close_for_recovery() -> None:
    rel = "CTH 144_XML_SVH/KUB 26.29+.xml"
    raw = _raw(rel)
    prepared = prepared_source.prepare(rel)

    # Current patch 1 inserts an early synthetic </AO:Akkgram>; patch 2 then deletes
    # the original delayed close as "stray". Both decisions are one structural defect.
    assert prepared.original_bytes == raw
    assert prepared.mechanical_bytes == raw
    assert prepared.mechanical_patch_ordinals == ()
    assert prepared.recovery_patch_ordinals == (1, 2)
    assert prepared.recovery_event_ids == (f"{rel}:1",)
    assert b"</AO:Akkgram></w> <w><AO:Sumgram>KUR" in prepared.mechanical_bytes
    assert repair.parses(prepared.mechanical_bytes) is False


def test_word_stack_keeps_proven_byte_local_repairs_but_skips_crossing_close() -> None:
    rel = "CTH 209_XML_TLH/KBo 12.55.xml"
    raw = _raw(rel)
    expected_sha, patches = _manifest_entry(rel)
    prepared = prepared_source.prepare(rel)

    expected_mechanical = repair.apply(raw, patches[:2], expect_sha=expected_sha)
    assert prepared.source_sha256 == sha256(raw).hexdigest()
    assert prepared.original_bytes == raw
    assert prepared.mechanical_bytes == expected_mechanical
    assert prepared.mechanical_patch_ordinals == (1, 2)
    assert prepared.recovery_patch_ordinals == (3,)
    assert prepared.recovery_event_ids == (f"{rel}:3",)
    assert prepared.mechanical_bytes.endswith(b"</text></div1></body></AOxml> ")
    assert repair.parses(prepared.mechanical_bytes) is False


def test_misnamespaced_close_keeps_original_close_and_groups_preceding_patch() -> None:
    rel = "CTH 832_XML_TLH/KBo 71.216.xml"
    raw = _raw(rel)
    prepared = prepared_source.prepare(rel)

    # Patch 1 deletes the original </TxtPubl>; patch 2 only becomes necessary because
    # the old loop then inserts </AO:TxtPubl>. The reviewed disposition owns the pair.
    assert prepared.original_bytes == raw
    assert prepared.mechanical_bytes == raw
    assert prepared.mechanical_patch_ordinals == ()
    assert prepared.recovery_patch_ordinals == (1, 2)
    assert prepared.recovery_event_ids == (f"{rel}:2",)
    assert b"</TxtPubl> </AO:Manuscripts>" in prepared.mechanical_bytes
    assert repair.parses(prepared.mechanical_bytes) is False


def test_every_patch_is_partitioned_once_for_all_reviewed_crossing_files() -> None:
    for rel in prepared_source.reviewed_paths():
        prepared = prepared_source.prepare(rel)
        _sha, patches = _manifest_entry(rel)
        mechanical = set(prepared.mechanical_patch_ordinals)
        recovery = set(prepared.recovery_patch_ordinals)
        assert mechanical.isdisjoint(recovery), rel
        assert mechanical | recovery == set(range(1, len(patches) + 1)), rel
        assert prepared.recovery_event_ids, rel


def test_unreviewed_path_cannot_enter_structural_recovery() -> None:
    # A normal corpus file has no #12 disposition and therefore no structural lane.
    rel = "CTH 1_XML_TLH/KBo 22.1.xml"
    try:
        prepared_source.prepare(rel)
    except prepared_source.NotReviewed:
        pass
    else:
        raise AssertionError("unreviewed source unexpectedly entered #12 recovery")
