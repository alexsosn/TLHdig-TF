#!/usr/bin/env python
"""Inventory repaired-source <lb> elements without a usable lnr for issue #15.

Research-only helper. It deliberately follows the converter's repair + strict XML parse
path so malformed raw tags are not misclassified as missing metadata.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

import lxml.etree as LE

PROGRAMS = Path(__file__).resolve().parent
ROOT = PROGRAMS.parent
sys.path.insert(0, str(PROGRAMS))

from tlhdig import lineref, repair
from tlhdig.paths import PATCHES, corpus_files, rel


def _public_attrs(element) -> dict[str, str]:
    out = {k: v for k, v in element.attrib.items() if k != "cu"}
    cu = element.get("cu")
    if cu is not None:
        out["cu_length"] = len(cu)
    return out


def main() -> int:
    manifest = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    parser = LE.XMLParser(recover=False, resolve_entities=False)
    candidates = []
    total_lb = 0
    affected_files = 0
    repaired_files = 0
    unparseable_files = 0

    for path in corpus_files():
        data = path.read_bytes()
        entry = manifest.get(rel(path))
        if entry:
            data = repair.apply(data, entry[1], expect_sha=entry[0])
            repaired_files += 1
        try:
            root = LE.fromstring(data, parser)
        except Exception:
            unparseable_files += 1
            continue

        rows = [dict(lb.attrib) for lb in root.iter("lb")]
        total_lb += len(rows)
        bad_indices = [i for i, row in enumerate(rows) if not row.get("lnr", "").strip()]
        if not bad_indices:
            continue
        affected_files += 1

        # Classify contiguous missing runs only when the surrounding scholarly labels
        # prove one unique numeric sequence in the same section. Anything weaker stays
        # unresolved; sequence position alone is not promoted to a source line number.
        run_for = {}
        bad_set = set(bad_indices)
        start = None
        for i in range(len(rows) + 1):
            bad = i < len(rows) and i in bad_set
            if bad and start is None:
                start = i
            if start is not None and not bad:
                stop = i
                count = stop - start
                prev_i = start - 1 if start else None
                next_i = stop if stop < len(rows) else None
                prev_ref = lineref.parse(rows[prev_i].get("lnr")) if prev_i is not None else None
                next_ref = lineref.parse(rows[next_i].get("lnr")) if next_i is not None else None
                inferred = []
                if (
                    prev_ref is not None
                    and next_ref is not None
                    and prev_ref.ln is not None
                    and next_ref.ln is not None
                    and prev_ref.collabel == next_ref.collabel
                    and prev_ref.prime == next_ref.prime
                    and not prev_ref.tail
                    and not next_ref.tail
                    and next_ref.ln - prev_ref.ln == count + 1
                ):
                    inferred = [f"{prev_ref.ln + offset}{prev_ref.prime}" for offset in range(1, count + 1)]
                for offset, j in enumerate(range(start, stop)):
                    run_for[j] = {
                        "run_length": count,
                        "inferred_lnno": inferred[offset] if inferred else None,
                        "neighbor_collabel": prev_ref.collabel if inferred else None,
                    }
                start = None

        lbs = list(root.iter("lb"))
        for i in bad_indices:
            row = rows[i]
            prev = rows[i - 1] if i else {}
            nxt = rows[i + 1] if i + 1 < len(rows) else {}
            info = run_for[i]
            candidates.append(
                {
                    "path": rel(path),
                    "lb_index": i + 1,
                    "txtid": row.get("txtid", ""),
                    "lnr_state": "absent" if "lnr" not in row else "empty",
                    "attrs": _public_attrs(lbs[i]),
                    "previous_lnr": prev.get("lnr"),
                    "next_lnr": nxt.get("lnr"),
                    "run_length": info["run_length"],
                    "local_class": (
                        "deterministically inferable"
                        if info["inferred_lnno"]
                        else "needs external evidence or synthetic address"
                    ),
                    "inferred_lnno": info["inferred_lnno"],
                    "neighbor_collabel": info["neighbor_collabel"],
                }
            )

    state_counts = Counter(c["lnr_state"] for c in candidates)
    class_counts = Counter(c["local_class"] for c in candidates)
    result = {
        "total_lb": total_lb,
        "repaired_files": repaired_files,
        "unparseable_files": unparseable_files,
        "affected_lines": len(candidates),
        "affected_files": affected_files,
        "lnr_state_counts": dict(state_counts),
        "local_class_counts": dict(class_counts),
        "candidates": candidates,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    expected_states = Counter({"absent": 25, "empty": 14})
    if len(candidates) != 39 or state_counts != expected_states or affected_files != 35:
        print("RESEARCH CENSUS MISMATCH", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
