"""TDD contract for the #12 observation-only recovery inventory (pinned source bytes)."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import repair
import source_recovery_inventory as inventory
from tlhdig.paths import ROOT

LEGACY_CORPUS = ROOT / 'corpus' / 'TLHdig-0.3'
LEGACY = ROOT / 'programs/tests/fixtures/beta03'


CROSSING = "crossing tags: inner element closed before its parent"


def _write_list(path: Path, *rows: str) -> None:
    path.write_text(
        "# test allowlist\n" + "".join(f"{row}\ttest reason\n" for row in rows),
        encoding="utf8",
    )


def test_crossing_delta_preserves_multiplicity_and_boundary() -> None:
    old = b"</text> following context"
    new = b"</w></w></AO:HitGLOS>" + old
    closures, boundary = inventory.crossing_delta(old, new)
    assert closures == ["w", "w", "AO:HitGLOS"]
    assert boundary == "text"


def test_inventory_maps_sequential_patch_offset_back_to_original(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    rel = "CTH 1_XML_TLH/Test.xml"
    src = corpus / rel
    src.parent.mkdir(parents=True)
    raw = b'<text a="x"><w>abc</text>'
    src.write_bytes(raw)

    # The first edit changes length before the structural defect. The crossing event's
    # intermediate-stream offset must still map back to the original source coordinate.
    patches = [
        repair.Patch(b'a="x"', b'a="longer"', "test lexical repair"),
        repair.Patch(
            b"</text>",
            b"</w></text>",
            CROSSING,
        ),
    ]
    manifest = tmp_path / "patches.yaml"
    repair.write_manifest(manifest, {rel: (sha256(raw).hexdigest(), patches)})

    known = tmp_path / "known_lossy.txt"
    contract = tmp_path / "contract_a_known.txt"
    _write_list(known, rel)
    _write_list(contract, rel)

    rows = inventory.build_inventory(
        corpus=corpus,
        manifest=manifest,
        known_lossy=known,
        contract_a_known=contract,
        context_bytes=12,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["path"] == rel
    assert row["patch_ordinal"] == 2
    assert row["inserted_closures"] == ["w"]
    assert row["inserted_close_count"] == 1
    assert row["boundary"] == "text"
    assert row["current_known_lossy"] is True
    assert row["current_contract_a_known"] is True
    assert row["intermediate_byte_start"] > row["original_byte_start"]
    assert row["original_byte_start"] == raw.index(b"</text>")
    assert row["original_offset_exact"] is True
    assert row["source_sha256"] == sha256(raw).hexdigest()
    assert "disposition" not in row
    assert "suggested_recovery_class" not in row


def test_reviewed_marker_only_close_before_source_line_is_inventory_event() -> None:
    """A word-close inserted before an attested <lb> is not an end-tag close."""
    from tlhdig import repair

    source_label = '<lb txtid="KBo 41.49+" lnr="{€2} 29′"'.encode("utf8")
    patch = repair.Patch(
        old=source_label, new=b"</w>" + source_label,
        reason=inventory.MARKER_LINE_REASON + "9/14; preserve source readings",
    )
    assert inventory.observed_crossing_delta(patch) == (["w"], "lb")
    try:
        inventory.observed_crossing_delta(
            repair.Patch(source_label, b"</w></w>" + source_label, patch.reason)
        )
    except inventory.InventoryError:
        pass
    else:
        raise AssertionError("extra speculative closure should fail closed")


def test_inventory_keeps_multi_close_event_as_one_event(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    rel = "CTH 2_XML_TLH/Deep.xml"
    src = corpus / rel
    src.parent.mkdir(parents=True)
    raw = b"<text><w><w><w>x</text>"
    src.write_bytes(raw)
    patch = repair.Patch(
        b"</text>",
        b"</w></w></w></text>",
        CROSSING,
    )
    manifest = tmp_path / "patches.yaml"
    repair.write_manifest(manifest, {rel: (sha256(raw).hexdigest(), [patch])})
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf8")

    (row,) = inventory.build_inventory(
        corpus=corpus,
        manifest=manifest,
        known_lossy=empty,
        contract_a_known=empty,
    )
    assert row["inserted_closures"] == ["w", "w", "w"]
    assert row["inserted_close_count"] == 3
    assert row["event_id"].endswith(":1")


def test_direct_original_target_beats_coarse_offset_map_edit_region(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    rel = "CTH 3_XML_TLH/Widened.xml"
    src = corpus / rel
    src.parent.mkdir(parents=True)
    raw = b"<text><w><sGr>x</sGr></d>tail</w></text>"
    src.write_bytes(raw)

    # The first manifest patch changes only the stray </sGr>, but its uniqueness
    # context includes the later </d> crossing target. OffsetMap therefore marks that
    # whole widened replacement as an edit even though the crossing target bytes are
    # literally unchanged in the original source.
    old1 = b"</sGr></d>tail</w>"
    new1 = b"</d>tail</w>"
    old2 = b"</d>tail</w>"
    new2 = b"</sGr></d>tail</w>"
    patches = [
        repair.Patch(old1, new1, "test widened-context repair"),
        repair.Patch(old2, new2, CROSSING),
    ]
    manifest = tmp_path / "patches.yaml"
    repair.write_manifest(manifest, {rel: (sha256(raw).hexdigest(), patches)})
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf8")

    (row,) = inventory.build_inventory(
        corpus=corpus,
        manifest=manifest,
        known_lossy=empty,
        contract_a_known=empty,
    )
    assert row["original_byte_start"] == raw.index(old2)
    assert row["original_offset_exact"] is True
    assert row["original_offset_method"] == "direct_unique_target"


def _repaired(rel: str) -> bytes:
    manifest = repair.read_manifest(LEGACY / 'patches.yaml')
    raw = (LEGACY_CORPUS / rel).read_bytes()
    sha, patches = manifest[rel]
    return repair.apply(raw, patches, expect_sha=sha)


def test_filtered_loss_measurement_distinguishes_lossy_and_clean_word_stack_files(monkeypatch) -> None:
    # Historical loss examples are now both recovered by the whitespace fix.
    clean = {"failing_words": 0, "lost_bytes": 0, "words": []}
    for rel in ("CTH 209_XML_TLH/KBo 12.55.xml",
                "CTH 294_XML_TLH/KBo 31.43.xml",
                "CTH 324_XML_MYTH/IBoT 3.141.xml"):
        assert inventory.measure_filtered_word_loss(_repaired(rel)) == clean, rel

    # Fault injection tests the detector without depending on a production bug.
    from tlhdig import signs
    from base64 import b64decode
    xml = b"<text><w>a<del_in/>-b</w><w>c</w></text>"
    original = signs.tokenise_word
    def lossy(inner):
        if inner == b"a<del_in/>-b":
            return [signs.Sign(sym="a", srcxml="a"),
                    signs.Sign(type="empty", srcxml="<del_in/>"),
                    signs.Sign(sym="b", srcxml="b", after="")]
        return original(inner)
    # Keep the separator on the preceding token, so the injected loss is
    # precisely the marker bytes rather than an accounting inconsistency.
    def injected(inner):
        tokens = lossy(inner)
        if inner == b"a<del_in/>-b":
            tokens[1].after = "-"
        return tokens
    monkeypatch.setattr(signs, "tokenise_word", injected)
    result = inventory.measure_filtered_word_loss(xml)
    assert result["failing_words"] == 1
    assert result["lost_bytes"] == len(b"<del_in/>-")
    row, = result["words"]
    assert row["outer_start"] == xml.index(b"<w>")
    assert [b64decode(x) for x in row["dropped_segments_base64"]] == [b"<del_in/>-"]

def test_checked_in_beta03_source_recovery_inventory_is_reproducible() -> None:
    """Historical observations stay exact; current tokenisation may improve loss."""
    rows = inventory.build_inventory(corpus=LEGACY_CORPUS, manifest=LEGACY / 'patches.yaml', known_lossy=LEGACY / 'known_lossy.txt', contract_a_known=LEGACY / 'contract_a_known.txt')
    effects = inventory.measure_crossing_file_effects(rows, corpus=LEGACY_CORPUS, manifest=LEGACY / 'patches.yaml')
    report = json.loads((inventory.REPORTS / "source-recovery-inventory.json").read_text(encoding="utf8"))
    # Event identity, source bytes, offsets, and manifest observations are frozen.
    assert rows == report["events"]
    historical = report["file_effects"]
    assert effects.keys() == historical.keys()
    for rel, current in effects.items():
        old = historical[rel]
        assert current["current_known_lossy"] == old["current_known_lossy"], rel
        assert current["failing_words"] <= old["failing_words"], rel
        assert current["lost_bytes"] <= old["lost_bytes"], rel
        # A newly lost word is a regression even if total loss went down.
        old_by_word = {w["outer_start"]: w for w in old["words"]}
        for word in current["words"]:
            prior = old_by_word[word["outer_start"]]
            assert word["outer_end"] == prior["outer_end"], rel
            assert word["lost_bytes"] <= prior["lost_bytes"], rel
    # Positive improvement control, independently pinned by the old report.
    rel = "CTH 209_XML_TLH/KBo 12.55.xml"
    assert historical[rel]["lost_bytes"] == 1
    assert effects[rel]["lost_bytes"] == 0


def test_reviewed_dispositions_cover_exact_inventory_and_are_source_bound() -> None:
    report = json.loads(
        (inventory.REPORTS / "source-recovery-inventory.json").read_text(encoding="utf8")
    )
    policy_path = inventory.PROGRAMS / "source_recovery_dispositions.json"
    policy = json.loads(policy_path.read_text(encoding="utf8"))

    observed = {row["event_id"]: row for row in report["events"]}
    reviewed = {row["event_id"]: row for row in policy["events"]}
    assert reviewed.keys() == observed.keys()
    # #159 replaces one speculative end-of-text close event with 14 distinct,
    # hash-pinned line-boundary closures over proven marker-only wrappers.
    assert len(reviewed) == 87
    kbo_159 = [
        row for event_id, row in reviewed.items()
        if event_id.startswith("CTH 479_XML_BESRIT/KBo 41.49+.xml:")
    ]
    assert len(kbo_159) == 14
    assert all(row["planned_action"] == "resynchronize_word_state"
               for row in kbo_159)

    statuses = {
        "mechanically_determined",
        "strongly_supported",
        "ambiguous",
        "source_unusable",
    }
    actions = {
        "resynchronize_word_state",
        "resynchronize_before_sibling_word",
        "omit_ambiguous_wrapper_extent",
        "repair_misnamespaced_close",
        "omit_stray_empty_manuscripts_open",
        "exclude_document",
    }
    for event_id, row in reviewed.items():
        source = observed[event_id]
        assert row["source_sha256"] == source["source_sha256"]
        # A source hash alone is insufficient: patches.yaml can change while the
        # immutable source file does not. Review must bind to the exact observed
        # crossing signature, so changing old/new bytes, boundary, offset, or inserted
        # closures invalidates the old disposition.
        assert row["observation_fingerprint"] == source["observation_fingerprint"]
        assert row["evidence_status"] in statuses
        assert row["planned_action"] in actions
        assert row["evidence"]
        assert all(isinstance(item, str) and item.strip() for item in row["evidence"])

    kbo71 = reviewed["CTH 832_XML_TLH/KBo 71.216.xml:2"]
    assert kbo71["evidence_status"] == "mechanically_determined"
    assert kbo71["planned_action"] == "repair_misnamespaced_close"

    kub19 = reviewed["CTH 72_XML_TLH/KUB 19.15+.xml:1"]
    assert kub19["evidence_status"] == "strongly_supported"
    assert kub19["planned_action"] == "omit_stray_empty_manuscripts_open"

    collapsed = [
        row for event_id, row in reviewed.items()
        if event_id.startswith("CTH 412_XML_TLH/KBo 38.169.xml:")
    ]
    assert len(collapsed) == 6
    assert {row["evidence_status"] for row in collapsed} == {"source_unusable"}
    assert {row["planned_action"] for row in collapsed} == {"exclude_document"}


def test_observation_fingerprint_changes_when_neighboring_manifest_patch_changes(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    rel = "CTH 4_XML_TLH/Coupled.xml"
    src = corpus / rel
    src.parent.mkdir(parents=True)
    raw = b"<text><w><AO:HitGLOS>x</w>y</AO:HitGLOS></text>"
    src.write_bytes(raw)
    sha = sha256(raw).hexdigest()

    crossing = repair.Patch(
        b"</w>y</AO:HitGLOS>",
        b"</AO:HitGLOS></w>y</AO:HitGLOS>",
        CROSSING,
    )
    late_a = repair.Patch(
        b"</AO:HitGLOS></text>",
        b"</text>",
        "stray close tag, nothing open",
    )
    late_b = repair.Patch(
        b"</AO:HitGLOS></text>",
        b" </text>",
        "stray close tag, nothing open",
    )
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf8")

    m1 = tmp_path / "one.yaml"
    m2 = tmp_path / "two.yaml"
    repair.write_manifest(m1, {rel: (sha, [crossing, late_a])})
    repair.write_manifest(m2, {rel: (sha, [crossing, late_b])})

    (a,) = inventory.build_inventory(
        corpus=corpus, manifest=m1, known_lossy=empty, contract_a_known=empty
    )
    (b,) = inventory.build_inventory(
        corpus=corpus, manifest=m2, known_lossy=empty, contract_a_known=empty
    )
    assert a["old_base64"] == b["old_base64"]
    assert a["new_base64"] == b["new_base64"]
    assert a["observation_fingerprint"] != b["observation_fingerprint"]
    for row in (a, b):
        assert len(row["manifest_context_fingerprint"]) == 64
        assert len(row["observation_fingerprint"]) == 64
        int(row["manifest_context_fingerprint"], 16)
        int(row["observation_fingerprint"], 16)
