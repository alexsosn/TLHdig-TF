#!/usr/bin/env python
"""Contract A gate: byte spans must reconstruct every source file exactly.

Reconstructs each document purely from recorded spans -- root outer slice, plus a
containment check on every element -- and additionally verifies that each <w>'s inner
span can be sliced back out. Writes reports/contract_a.tsv.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import source
from tlhdig.paths import REPORTS, corpus_files, rel


def main() -> int:
    files = corpus_files()
    stats = Counter()
    rows = []
    for f in files:
        data = f.read_bytes()
        try:
            spans = source.scan(data)
        except Exception as e:
            stats["unparseable"] += 1
            rows.append((rel(f), "unparseable", type(e).__name__, str(e)[:120]))
            continue

        problems = source.verify_reconstruction(data, spans)
        if problems:
            stats["span_problem"] += 1
            rows.append((rel(f), "span_problem", str(len(problems)), problems[0][:120]))
            continue

        # anything outside the root must be prolog/epilog only (PI, comment, doctype)
        root = spans[0]
        if not source.outside_root_ok(data, root):
            stats["content_outside_root"] += 1
            head = data[: root.outer_start]
            rows.append(
                (rel(f), "content_outside_root", head[:60].decode("utf8", "replace"), "")
            )
            continue
        if data[: root.outer_start].strip():
            stats["has_prolog_pi"] += 1

        nw = sum(1 for s in spans if s.tag == "w")
        stats["ok"] += 1
        stats["words"] += nw
        stats["elements"] += len(spans)

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / "contract_a.tsv"
    with out.open("w", encoding="utf8") as fh:
        fh.write("file\tstatus\tdetail1\tdetail2\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")

    print(f"files          : {len(files):,}")
    print(f"  reconstructed: {stats['ok']:,}")
    print(f"  unparseable  : {stats['unparseable']:,}  (repair stage)")
    print(f"  span problems: {stats['span_problem']:,}")
    print(f"  stray content: {stats['content_outside_root']:,}")
    print(f"  (of which had a legitimate prolog PI: {stats['has_prolog_pi']:,})")
    print(f"elements spanned: {stats['elements']:,}")
    print(f"<w> spanned     : {stats['words']:,}")
    print(f"report -> {out}")
    return 0 if stats["span_problem"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
