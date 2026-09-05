#!/usr/bin/env python
"""Inventory source <lb> elements without a usable lnr for issue #15.

Research-only helper. It does not modify source data or TF artifacts.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys

PROGRAMS = Path(__file__).resolve().parent
ROOT = PROGRAMS.parent
CORPUS = ROOT / "corpus" / "TLHdig-0.3"
sys.path.insert(0, str(PROGRAMS))

from tlhdig import lineref

LB_RE = re.compile(r"<lb\b(?P<attrs>[^>]*)/?>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", re.S)


def attrs(raw: str) -> dict[str, str]:
    return {m.group(1): m.group(3) for m in ATTR_RE.finditer(raw)}


def compact_tag(raw: str) -> str:
    # Cuneiform strings can be long and are irrelevant to the addressing defect.
    return re.sub(r"\s+cu\s*=\s*([\"']).*?\1", " cu=<omitted>", raw, flags=re.S)


def main() -> int:
    candidates = []
    total_lb = 0
    files = 0

    for path in sorted(CORPUS.rglob("*.xml"), key=lambda p: str(p).lower()):
        text = path.read_text(encoding="utf8", errors="replace")
        rows = []
        for m in LB_RE.finditer(text):
            a = attrs(m.group("attrs"))
            rows.append({"attrs": a, "raw": m.group(0)})
        if not rows:
            continue
        total_lb += len(rows)
        bad_indices = [i for i, row in enumerate(rows) if not row["attrs"].get("lnr", "").strip()]
        if not bad_indices:
            continue
        files += 1

        # Classify contiguous missing runs from the nearest source-provided neighbours.
        run_for = {}
        start = None
        for i in range(len(rows) + 1):
            bad = i < len(rows) and i in bad_indices
            if bad and start is None:
                start = i
            if start is not None and not bad:
                stop = i
                prev_i = start - 1 if start > 0 else None
                next_i = stop if stop < len(rows) else None
                prev_ref = lineref.parse(rows[prev_i]["attrs"].get("lnr")) if prev_i is not None else None
                next_ref = lineref.parse(rows[next_i]["attrs"].get("lnr")) if next_i is not None else None
                count = stop - start
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
                        "run_start": start,
                        "run_length": count,
                        "inferred_lnno": inferred[offset] if inferred else None,
                        "neighbor_collabel": prev_ref.collabel if inferred else None,
                    }
                start = None

        for i in bad_indices:
            a = rows[i]["attrs"]
            prev = rows[i - 1]["attrs"] if i else {}
            nxt = rows[i + 1]["attrs"] if i + 1 < len(rows) else {}
            info = run_for[i]
            kind = "absent" if "lnr" not in a else "empty"
            local_class = "deterministically inferable" if info["inferred_lnno"] else "truly unnumbered locally"
            candidates.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "lb_index": i + 1,
                    "txtid": a.get("txtid", ""),
                    "lnr_state": kind,
                    "raw_tag": compact_tag(rows[i]["raw"]),
                    "previous_lnr": prev.get("lnr"),
                    "next_lnr": nxt.get("lnr"),
                    "run_length": info["run_length"],
                    "local_class": local_class,
                    "inferred_lnno": info["inferred_lnno"],
                    "neighbor_collabel": info["neighbor_collabel"],
                }
            )

    state_counts = Counter(c["lnr_state"] for c in candidates)
    class_counts = Counter(c["local_class"] for c in candidates)
    result = {
        "total_lb": total_lb,
        "affected_lines": len(candidates),
        "affected_files": files,
        "lnr_state_counts": dict(state_counts),
        "local_class_counts": dict(class_counts),
        "candidates": candidates,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # This research helper asserts the currently documented defect census so source
    # changes cannot silently invalidate the analysis before a plan is written.
    if len(candidates) != 39 or state_counts != Counter({"absent": 25, "empty": 14}) or files != 35:
        print("RESEARCH CENSUS MISMATCH", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
