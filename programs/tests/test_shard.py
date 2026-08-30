"""Adversarial integration shard.

Every serious defect in this project has been an integration bug: components correct in
isolation, wrong where their output meets the graph. Unit tests passed throughout the
marker losses, the structural losses and the compaction corruption. This builds a real
Text-Fabric dataset from 91 documents chosen for the constructs that have actually
broken, and compares a source census with a graph census -- the check that would have
caught every one of them.

`programs/shard.txt` is checked in so CI does not re-scan 23,937 files to find them.
"""
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import convert, repair, structure
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, PROGRAMS, rel


def shard_files() -> list[Path]:
    out = []
    for line in (PROGRAMS / "shard.txt").read_text(encoding="utf8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        out.append(CORPUS / line.partition("\t")[0])
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    files = shard_files()
    missing = [f for f in files if not f.is_file()]
    assert not missing, f"shard names files that do not exist: {missing[:3]}"
    out = tmp_path_factory.mktemp("shard") / "tf"
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    ledger = convert.Ledger()
    ok = convert.build(
        CORPUS, out, files=files, patches=patches, ledger=ledger, load=False
    )
    assert ok, "the shard did not convert"
    return out, files, patches, ledger


def test_the_shard_covers_the_constructs_that_have_broken():
    kinds = Counter(
        line.partition("\t")[2].strip()
        for line in (PROGRAMS / "shard.txt").read_text(encoding="utf8").splitlines()
        if line.strip() and not line.startswith("#")
    )
    for required in (
        "repaired", "nested-w", "empty-w", "multi-mrp0sel", "no-readable-sign",
        "note-outside-w", "composite-witness", "duplicate-docid", "colon",
    ):
        assert kinds[required] >= 1, f"shard no longer covers {required}"


def test_every_source_structure_survives_in_the_shard(built):
    """The gate that would have caught the line/colon/note losses on every push."""
    out, files, patches, _ = built
    src, docs = structure.count_corpus(files, patches, ENCRYPTED, rel)
    graph = structure.graph_counts(out)
    assert docs > 50, "the shard should convert most of its documents"
    for ntype in ("line", "colon", "note"):
        assert src[ntype] == graph.get(ntype, 0), (
            f"{ntype}: source {src[ntype]:,} != graph {graph.get(ntype, 0):,}"
        )


def test_marker_conservation_holds_on_the_shard(built):
    """src -> fed -> emitted, the three counts the full build gate compares."""
    _, _, _, ledger = built
    assert ledger.marker_src, "no markers were counted"
    assert ledger.marker_src == ledger.marker_fed == ledger.marker_out
    assert ledger.marker_lost == []


def test_compaction_preserves_the_shard_byte_for_byte(built):
    """Compaction silently rewrote values onto the wrong nodes for months.

    Reading every feature before and after is cheap at shard scale and impossible to
    fool: the corruption only showed up in features containing empty values.
    """
    from tlhdig import compact

    out, _, _, _ = built
    before = {
        p.name: compact.read_values(p)
        for p in sorted(out.glob("*.tf"))
        if p.read_text(encoding="utf8").lstrip().startswith("@node")
    }
    compact.compact_dir(out)
    for name, values in before.items():
        after = compact.read_values(out / name)
        assert after == values, f"{name}: compaction changed {len(set(values.items()) ^ set(after.items()))} values"
