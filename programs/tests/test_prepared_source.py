"""Phase-1 TDD contract for shared prepared-source recovery (#12)."""
from __future__ import annotations

from hashlib import sha256
import json

from tlhdig import prepared_source, repair
from tlhdig.paths import CORPUS, PATCHES, PROGRAMS, REPORTS


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


def test_independent_stray_word_close_remains_mechanical() -> None:
    rel = "CTH 570_XML_HDivT/KUB 50.123.xml"
    raw = _raw(rel)
    expected_sha, patches = _manifest_entry(rel)
    prepared = prepared_source.prepare(rel)

    # Patch 1 removes a genuinely unmatched </w> immediately after a self-closing
    # <del_in/>. The later end-of-text open-word defect is independent and is patch 2.
    assert prepared.mechanical_patch_ordinals == (1,)
    assert prepared.recovery_patch_ordinals == (2,)
    assert prepared.mechanical_bytes == repair.apply(
        raw, [patches[0]], expect_sha=expected_sha
    )
    assert b"<del_in/></w> <w><space c=\"14\"/>" not in prepared.mechanical_bytes
    assert repair.parses(prepared.mechanical_bytes) is False


def test_patch_policy_is_bound_to_reviewed_inventory_and_dispositions() -> None:
    policy = json.loads(prepared_source.PATCH_POLICY.read_text(encoding="utf8"))["files"]
    report = json.loads(
        (PROGRAMS / "source_recovery_dispositions.json").read_text(
            encoding="utf8"
        )
    )
    inventory = json.loads(
        (REPORTS / "source-recovery-inventory.json").read_text(
            encoding="utf8"
        )
    )

    dispositions_by_path: dict[str, list[str]] = {}
    for row in report["events"]:
        rel = row["event_id"].rsplit(":", 1)[0]
        dispositions_by_path.setdefault(rel, []).append(row["event_id"])

    observations_by_path: dict[str, list[dict]] = {}
    for row in inventory["events"]:
        observations_by_path.setdefault(row["path"], []).append(row)

    assert policy.keys() == dispositions_by_path.keys() == observations_by_path.keys()
    for rel, entry in policy.items():
        observed = observations_by_path[rel]
        assert entry["source_sha256"] == observed[0]["source_sha256"]
        assert (
            entry["manifest_context_fingerprint"]
            == observed[0]["manifest_context_fingerprint"]
        )
        assert sorted(entry["recovery_event_ids"]) == sorted(dispositions_by_path[rel])
        event_ordinals = {row["patch_ordinal"] for row in observed}
        assert event_ordinals <= set(entry["recovery_patch_ordinals"])


def test_policy_rejects_patch_ordinals_out_of_manifest_order(tmp_path) -> None:
    rel = "CTH 0_XML_TLH/Synthetic.xml"
    corpus = tmp_path / "corpus"
    source_path = corpus / rel
    source_path.parent.mkdir(parents=True)
    raw = b"<root>a b c</root>"
    source_path.write_bytes(raw)

    patches = [
        repair.Patch(b"a", b"A", "mechanical a"),
        repair.Patch(b"b", b"B", "mechanical b"),
        repair.Patch(b"</root>", b"</x></root>", "structural synthetic"),
    ]
    manifest = tmp_path / "patches.yaml"
    source_sha = sha256(raw).hexdigest()
    repair.write_manifest(manifest, {rel: (source_sha, patches)})

    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "schema": 1,
                "files": {
                    rel: {
                        "source_sha256": source_sha,
                        "manifest_context_fingerprint":
                            prepared_source.manifest_context_fingerprint(patches),
                        "mechanical_patch_ordinals": [2, 1],
                        "recovery_patch_ordinals": [3],
                        "recovery_event_ids": [f"{rel}:3"],
                    }
                },
            }
        ),
        encoding="utf8",
    )

    try:
        prepared_source.prepare(
            rel, corpus=corpus, manifest=manifest, policy_path=policy_path
        )
    except prepared_source.PolicyDrift:
        pass
    else:
        raise AssertionError("out-of-order patch policy did not fail closed")


def test_reviewed_partition_preserves_21_coupled_stray_closes() -> None:
    policy = json.loads(prepared_source.PATCH_POLICY.read_text(encoding="utf8"))["files"]
    coupled = []
    mechanical_strays = []

    for rel, entry in policy.items():
        _sha, patches = _manifest_entry(rel)
        event_ordinals = {
            int(event_id.rsplit(":", 1)[1])
            for event_id in entry["recovery_event_ids"]
        }
        for ordinal in entry["recovery_patch_ordinals"]:
            if ordinal not in event_ordinals:
                coupled.append((rel, ordinal, patches[ordinal - 1].reason))
        for ordinal in entry["mechanical_patch_ordinals"]:
            reason = patches[ordinal - 1].reason
            assert "crossing tags:" not in reason, (rel, ordinal, reason)
            if reason == "stray close tag, nothing open":
                mechanical_strays.append((rel, ordinal))

    assert len(coupled) == 21
    assert {reason for _rel, _ordinal, reason in coupled} == {
        "stray close tag, nothing open"
    }
    assert mechanical_strays == [("CTH 570_XML_HDivT/KUB 50.123.xml", 1)]


def test_mechanical_offset_map_targets_immutable_source_bytes() -> None:
    rel = "CTH 209_XML_TLH/KBo 12.55.xml"
    prepared = prepared_source.prepare(rel)
    repaired_offset = prepared.mechanical_bytes.index(b"</text>")
    original_offset = prepared.original_bytes.index(b"</text>")

    omap = prepared.mechanical_offset_map
    assert omap.is_exact(repaired_offset)
    assert omap.to_original(repaired_offset) == original_offset
