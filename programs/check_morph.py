#!/usr/bin/env python
"""Prototype 2 gate: parse every mrpN in the corpus; nothing may be silently dropped."""
import sys
from collections import Counter
from pathlib import Path

import lxml.etree as LE

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import morph
from tlhdig.paths import REPORTS, corpus_files, rel

def main() -> int:
    stats = Counter()
    failures = []
    sel_kinds = Counter()
    f4 = Counter()
    seps = Counter()
    idx_min = Counter()

    parser = LE.XMLParser(recover=False, resolve_entities=False)
    for f in corpus_files():
        try:
            root = LE.parse(str(f), parser).getroot()
        except Exception:
            stats["file_unparseable"] += 1
            continue
        stats["file_ok"] += 1
        for w in root.iter("w"):
            got = morph.analyses(w.attrib)
            if got:
                stats["words_with_analyses"] += 1
                idx_min[got[0].index] += 1
            for a in got:
                stats["analyses"] += 1
                seps[a.sep.strip() or "(none)"] += 1
                f4[a.field4_kind] += 1
                if not a.ok:
                    stats["parse_failed"] += 1
                    if len(failures) < 20000:
                        failures.append((rel(f), a.index, a.note, a.raw[:120]))
            s = morph.parse_selection(w.get("mrp0sel"))
            sel_kinds[s.kind] += 1
            if s.kind == "analysis" and s.index is not None:
                if not any(a.index == s.index for a in got):
                    stats["selector_dangling"] += 1
                    if len(failures) < 20000:
                        failures.append(
                            (rel(f), s.index, "selector points at missing mrpN", s.raw)
                        )

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / "morph_parse.tsv"
    with out.open("w", encoding="utf8") as fh:
        fh.write("file\tindex\tproblem\tvalue\n")
        for r in failures:
            fh.write("\t".join(str(x) for x in r) + "\n")

    n = stats["analyses"]
    print(f"files parsed        : {stats['file_ok']:,}  (unparseable {stats['file_unparseable']:,})")
    print(f"words with analyses : {stats['words_with_analyses']:,}")
    print(f"analyses parsed     : {n:,}")
    print(f"  parse failures    : {stats['parse_failed']:,}  ({stats['parse_failed']/max(n,1)*100:.4f}%)")
    print(f"  dangling selectors: {stats['selector_dangling']:,}")
    print(f"\nseparator forms  : {dict(seps.most_common())}")
    print(f"field4 kinds     : {dict(f4.most_common())}")
    print(f"selection kinds  : {dict(sel_kinds.most_common())}")
    print(f"lowest index used: {dict(sorted(idx_min.items())[:4])}")
    print(f"\nreport -> {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
