#!/usr/bin/env python
"""Inventory repaired-source and shipped-TF lines without a usable section address (#15).

Research-only helper. It deliberately follows the converter's repair + strict XML parse
path, then independently inventories the committed TF feature files and reconciles both
by ``(src_file, srcln)``. Source coverage and shipped-graph coverage are different facts.
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

from tlhdig import TF_VERSION, appcheck, compact, lineref, repair
from tlhdig.paths import PATCHES, corpus_files, rel


def _public_attrs(element) -> dict[str, str]:
    out = {k: v for k, v in element.attrib.items() if k != "cu"}
    cu = element.get("cu")
    if cu is not None:
        out["cu_length"] = len(cu)
    return out


def _source_candidates():
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

    return candidates, {
        "total_lb": total_lb,
        "repaired_files": repaired_files,
        "unparseable_files": unparseable_files,
        "affected_lines": len(candidates),
        "affected_files": affected_files,
        "lnr_state_counts": dict(Counter(c["lnr_state"] for c in candidates)),
        "local_class_counts": dict(Counter(c["local_class"] for c in candidates)),
    }


def _feature(tf_dir: Path, name: str) -> dict[int, str]:
    path = appcheck.feature_path(tf_dir, name)
    if path is None:
        raise RuntimeError(f"missing feature {name}.tf")
    return compact.read_values(path)


def _spans(tf_dir: Path, wanted: dict[str, tuple[int, int]]):
    """Read oslots once and retain only spans for the requested structural types."""
    ranges = list(wanted.items())
    result = {name: {} for name in wanted}
    _, body = compact._split(tf_dir / "oslots.tf")
    for nodes, value in compact._parse(body):
        slots = compact._nodes_of(value)
        if not slots:
            continue
        span = (min(slots), max(slots))
        for node in nodes:
            for name, (lo, hi) in ranges:
                if lo <= node <= hi:
                    result[name][node] = span
                    break
    return result


def _container(span: tuple[int, int], structures: dict[int, tuple[int, int]]) -> list[int]:
    lo, hi = span
    return [node for node, (a, b) in structures.items() if a <= lo and hi <= b]


def _tf_candidates():
    tf_dir = ROOT / "tf" / TF_VERSION
    ranges = appcheck.node_ranges(tf_dir)
    needed = {name: ranges[name] for name in ("line", "column", "document")}
    spans = _spans(tf_dir, needed)

    lnno = _feature(tf_dir, "lnno")
    srcln = _feature(tf_dir, "srcln")
    lnr = _feature(tf_dir, "lnr")
    txtid = _feature(tf_dir, "txtid")
    src_file = _feature(tf_dir, "src_file")
    collabel = _feature(tf_dir, "collabel")

    line_lo, line_hi = ranges["line"]
    rows = []
    for line in range(line_lo, line_hi + 1):
        if (lnno.get(line) or "").strip():
            continue
        span = spans["line"].get(line)
        if span is None:
            rows.append({"node": line, "problem": "line has no oslots span"})
            continue
        docs = _container(span, spans["document"])
        columns = _container(span, spans["column"])
        if len(docs) != 1 or len(columns) != 1:
            rows.append(
                {
                    "node": line,
                    "problem": f"containers documents={docs} columns={columns}",
                }
            )
            continue
        doc, column = docs[0], columns[0]
        rows.append(
            {
                "node": line,
                "path": src_file.get(doc, ""),
                "srcln": int(srcln[line]) if line in srcln and srcln[line] else None,
                "txtid": txtid.get(line, ""),
                "lnr": lnr.get(line),
                "lnno": lnno.get(line),
                "collabel": collabel.get(column),
                "column_node": column,
            }
        )
    return rows


def main() -> int:
    source_rows, source_summary = _source_candidates()
    tf_rows = _tf_candidates()

    source_by_key = {(row["path"], row["lb_index"]): row for row in source_rows}
    tf_by_key = {(row.get("path"), row.get("srcln")): row for row in tf_rows if "problem" not in row}
    source_only = [source_by_key[k] for k in sorted(source_by_key.keys() - tf_by_key.keys())]
    tf_only = [tf_by_key[k] for k in sorted(tf_by_key.keys() - source_by_key.keys())]
    matched = [
        {"source": source_by_key[k], "tf": tf_by_key[k]}
        for k in sorted(source_by_key.keys() & tf_by_key.keys())
    ]

    result = {
        "source": source_summary,
        "shipped_tf": {
            "version": TF_VERSION,
            "unaddressed_lines": len(tf_rows),
            "problem_rows": [row for row in tf_rows if "problem" in row],
        },
        "matched": len(matched),
        "source_only": source_only,
        "tf_only": tf_only,
        "candidates": matched,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    bad = False
    if len(tf_rows) != 39:
        print(f"TF RESEARCH CENSUS MISMATCH: expected 39, got {len(tf_rows)}", file=sys.stderr)
        bad = True
    if tf_only:
        print(f"TF lines without a matching repaired-source candidate: {len(tf_only)}", file=sys.stderr)
        bad = True
    if [row for row in tf_rows if "problem" in row]:
        print("TF unaddressed lines with ambiguous/missing structure containment", file=sys.stderr)
        bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
