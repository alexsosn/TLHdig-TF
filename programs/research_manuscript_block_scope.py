#!/usr/bin/env python
"""Research the source scope of repeated/moved AO:Manuscripts blocks for issue #18.

The production converter walks one primary body/div1/text, but repaired strict XML has
Manuscripts blocks both directly under div1 and repeated under text.  This pass measures
where those blocks occur relative to lines and whether a deterministic source-order block
can own line->fragment witness resolution without dropping the other source statements.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import lineref, manuscripts, repair
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, rel

AO = "{http://hethiter.net/ns/AO/1.0}"


def lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else "?"


def parse_source(path, r, patches):
    if r == ENCRYPTED:
        return None
    data = path.read_bytes()
    entry = patches.get(r)
    if entry:
        try:
            data = repair.apply(data, entry[1], expect_sha=entry[0])
        except repair.PatchError:
            return None
    try:
        return ET.fromstring(data)
    except ET.XMLSyntaxError:
        return None


def line_frags(text) -> tuple[str, ...]:
    result = []
    if text is None:
        return ()
    for lb in text.iter("lb"):
        ref = lineref.parse(lb.get("lnr"))
        for frag in ref.frags or ((ref.frag,) if ref.frag else ()):
            if frag and frag not in result:
                result.append(frag)
    return tuple(result)


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    counts = Counter()
    block_count_dist = Counter()
    witness_choice_dist = Counter()
    duplicate_text_dist = Counter()
    mismatch_examples = []
    multi_examples = []

    for path in sorted(CORPUS.rglob("*.xml")):
        r = rel(path)
        root = parse_source(path, r, patches)
        if root is None:
            continue
        div1 = root.find("body/div1")
        if div1 is None:
            continue
        primary_text = div1.find("text")
        primary_frags = line_frags(primary_text)

        # All strict/repaired blocks are measured independently in reachability research
        # as either div1/Manuscripts or text/Manuscripts. Keep source document order here.
        blocks = [n for n in div1.iter() if lname(n) == "Manuscripts"]
        block_count_dist[len(blocks)] += 1
        if not blocks:
            continue
        counts["documents_with_blocks"] += 1
        counts["blocks"] += len(blocks)
        if len(blocks) > 1:
            counts["documents_with_multiple_blocks"] += 1

        seen_lb = False
        before_first_line = []
        for node in div1.iter():
            if lname(node) == "lb":
                seen_lb = True
            elif lname(node) == "Manuscripts":
                counts["blocks_after_first_line" if seen_lb else "blocks_before_first_line"] += 1
                if not seen_lb:
                    before_first_line.append(node)

        parsed = [manuscripts.parse(b) for b in blocks]
        statement_counts = [len(a.statements) for a in parsed]
        entry_counts = [len(a.entries) for a in parsed]
        counts["statements"] += sum(statement_counts)
        counts["entries"] += sum(entry_counts)

        # Exact normalized duplicate apparatus bodies are useful evidence: repeated
        # serialization should keep separate source statement ledger rows, but it should
        # not automatically turn a line into an ambiguous witness.
        body_keys = []
        for app in parsed:
            body_keys.append(
                (
                    tuple((e.kind, e.label, e.siglum) for e in app.entries),
                    tuple((s.kind, s.encoding, s.raw, s.left, s.right, s.resolved) for s in app.statements),
                )
            )
        repeated = len(body_keys) - len(set(body_keys))
        duplicate_text_dist[repeated] += 1
        if repeated:
            counts["documents_with_exact_duplicate_blocks"] += 1
            counts["duplicate_block_occurrences_beyond_first"] += repeated

        if primary_frags:
            counts["documents_with_line_fragment_refs"] += 1
            block_sigla = [set(e.siglum for e in app.entries if e.siglum) for app in parsed]
            coverage = [sum(1 for frag in primary_frags if frag in sigla) for sigla in block_sigla]
            best = max(coverage, default=0)
            best_indexes = tuple(i + 1 for i, n in enumerate(coverage) if n == best and n > 0)
            counts["line_fragment_keys"] += len(primary_frags)
            counts["line_fragment_keys_best_covered"] += best
            if best == len(primary_frags):
                counts["documents_fully_covered_by_a_block"] += 1
            else:
                counts["documents_not_fully_covered_by_any_block"] += 1
                if len(mismatch_examples) < 40:
                    mismatch_examples.append((r, primary_frags, coverage, [sorted(x) for x in block_sigla]))

            # Candidate source-order policy: the last apparatus before the first line.
            last_before = blocks.index(before_first_line[-1]) + 1 if before_first_line else None
            best_last = best_indexes[-1] if best_indexes else None
            witness_choice_dist[(last_before, best_last, len(blocks))] += 1
            if last_before == best_last and best_last is not None:
                counts["last_before_line_is_best_last"] += 1
            elif best_last is not None:
                counts["last_before_line_differs_from_best_last"] += 1
                if len(mismatch_examples) < 40:
                    mismatch_examples.append((r, primary_frags, coverage, f"last_before={last_before}, best={best_indexes}"))

        if len(blocks) > 1 and len(multi_examples) < 35:
            multi_examples.append(
                (
                    r,
                    len(blocks),
                    primary_frags,
                    [
                        {
                            "path": "/".join(lname(x) for x in (list(b.iterancestors())[::-1] + [b])),
                            "entries": [(e.kind, e.label, e.siglum) for e in app.entries],
                            "statements": [(s.kind, s.encoding, s.raw, s.left, s.right, s.resolved) for s in app.statements],
                        }
                        for b, app in zip(blocks, parsed)
                    ],
                )
            )

    for key in (
        "documents_with_blocks", "blocks", "entries", "statements",
        "documents_with_multiple_blocks", "documents_with_exact_duplicate_blocks",
        "duplicate_block_occurrences_beyond_first", "blocks_before_first_line",
        "blocks_after_first_line", "documents_with_line_fragment_refs", "line_fragment_keys",
        "line_fragment_keys_best_covered", "documents_fully_covered_by_a_block",
        "documents_not_fully_covered_by_any_block", "last_before_line_is_best_last",
        "last_before_line_differs_from_best_last",
    ):
        print(f"{key}: {counts[key]:,}")
    print("block count distribution:")
    for nblocks, ndocs in sorted(block_count_dist.items()):
        if nblocks:
            print(f"  {nblocks} blocks: {ndocs:,} documents")
    print("duplicate-block occurrences beyond first distribution:")
    for repeated, ndocs in sorted(duplicate_text_dist.items()):
        if repeated:
            print(f"  {repeated}: {ndocs:,} documents")
    print("witness choice (last-before-line, best-last, block-count):")
    for shape, n in witness_choice_dist.most_common(20):
        print(f"  {shape}: {n:,}")
    if mismatch_examples:
        print("first coverage/policy mismatches:")
        for row in mismatch_examples:
            print(f"  {row}")
    if multi_examples:
        print("first multi-block documents:")
        for r, nblocks, frags, apps in multi_examples:
            print(f"  {r}: blocks={nblocks}, line_frags={frags}")
            for i, app in enumerate(apps, 1):
                print(f"    block {i}: {app}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
