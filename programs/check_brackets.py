#!/usr/bin/env python
"""Prototype 3 gate: bracket pairing statistics over the whole corpus."""
import sys
from collections import Counter
from pathlib import Path

import lxml.etree as LE

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import brackets as B
from tlhdig.paths import REPORTS, corpus_files

def main() -> int:
    agg = Counter()
    totals = Counter()
    parser = LE.XMLParser(recover=False, resolve_entities=False)

    for f in corpus_files():
        try:
            root = LE.parse(str(f), parser).getroot()
        except Exception:
            totals["file_unparseable"] += 1
            continue
        totals["file_ok"] += 1
        text = root.find("body/div1/text")
        if text is None:
            continue

        # First pass: for each line, which family does it *open* with a close for?
        per_line: list[list[str]] = []
        cur: list[str] | None = None
        for node in text.iter():
            tag = node.tag
            if not isinstance(tag, str):
                continue
            if tag == "lb":
                cur = []
                per_line.append(cur)
            elif cur is not None and (tag in B.OPEN or tag in B.CLOSE):
                cur.append(tag)
        leading_close = [
            frozenset({B.CLOSE[ln[0]]}) if ln and ln[0] in B.CLOSE else frozenset()
            for ln in per_line
        ]

        t = B.Tracker()
        line_no = 0
        sign_idx = 0
        for node in text.iter():
            tag = node.tag
            if not isinstance(tag, str):
                continue
            if tag == "lb":
                hint = leading_close[line_no] if line_no < len(leading_close) else frozenset()
                line_no += 1
                t.start_line(line_no, hint)
            elif tag == "w":
                sign_idx += 1
            elif tag in B.OPEN or tag in B.CLOSE:
                B.feed(t, tag, sign_idx)
                totals["markers"] += 1
        t.finish()

        for k, v in t.stats.items():
            agg[k] += v
        for c in t.clusters:
            totals["clusters"] += 1
            totals[f"orphan_{c.orphan}"] += 1
            if c.crossesline:
                totals["crossesline"] += 1
            if c.nested:
                totals["nested_flagged"] += 1

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / "brackets.tsv"
    with out.open("w", encoding="utf8") as fh:
        fh.write("stat\tcount\n")
        for k, v in sorted(agg.items()):
            fh.write(f"{k}\t{v}\n")
        for k, v in sorted(totals.items()):
            fh.write(f"{k}\t{v}\n")

    print(f"files parsed   : {totals['file_ok']:,}")
    print(f"markers fed    : {totals['markers']:,}")
    print(f"clusters built : {totals['clusters']:,}")
    print(f"  fully paired : {totals['orphan_none']:,}")
    print(f"  orphan open  : {totals['orphan_open']:,}")
    print(f"  orphan close : {totals['orphan_close']:,}")
    print(f"  cross a line : {totals['crossesline']:,}")
    print(f"  reopen-flagged: {totals['nested_flagged']:,}")
    print("\nper-family:")
    for fam in B.FAMILIES:
        row = {k.split(":")[1]: v for k, v in agg.items() if k.startswith(fam + ":")}
        if row:
            print(f"  {fam:<5} {row}")
    print(f"\nreport -> {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
