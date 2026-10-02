"""TDD contract for the #12 observation-only recovery inventory (pinned source bytes)."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import repair
import source_recovery_inventory as inventory


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
