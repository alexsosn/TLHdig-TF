#!/usr/bin/env python
"""Prototype 2 gate: parse every mrpN in the corpus; nothing may be silently dropped."""
import sys
from collections import Counter
from pathlib import Path

import lxml.etree as LE

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import morph, repair
from tlhdig.paths import PATCHES, REPORTS, corpus_files, rel

# Beta 0.4, pinned source inventory. Independently counted using the archive's
# raw XML (1,071 incomplete records: 974 two-field, 95 six-field, 2 one-field).
# 73 source-attested doubled-separator wātar2 records are now normalized.
# Preserve raw for remaining failures; new shapes must fail independently of
# the total. The previous 0.3 scalar limits do not describe this source.
SOURCE_FAILURE_LIMITS = {
    "base has 2 field(s)": 974,
    "base has 6 fields": 22,
    "base has 1 field(s)": 2,
}


def gate_problems(stats, failure_reasons):
    problems = []
    for key, expected in (("file_ok", 24128), ("file_unparseable", 3),
                          ("analyses", 1640230)):
        if stats[key] != expected:
            problems.append(f"{key} {stats[key]} != source census {expected}")
    if stats["patch_failed"]:
        problems.append(f"patch failures {stats['patch_failed']}")
    if sum(failure_reasons.values()) != stats["parse_failed"]:
        problems.append("parse failure reason ledger does not balance")
    for reason, count in sorted(failure_reasons.items()):
        limit = SOURCE_FAILURE_LIMITS.get(reason, 0)
        if count > limit:
            problems.append(f"{reason}: {count} > source limit {limit}")
    if stats["unknown_control"]:
        problems.append(f"unknown analysis-control prefixes {stats['unknown_control']}")
    if stats["selector_dangling"] > 47:
        problems.append(f"dangling first analysis selectors {stats['selector_dangling']} > 47")
    return problems


def main() -> int:
    stats = Counter()
    failures = []
    failure_reasons = Counter()
    sel_kinds = Counter()
    f4 = Counter()
    seps = Counter()
    idx_min = Counter()

    parser = LE.XMLParser(recover=False, resolve_entities=False)
    # Parse the repaired stream, as the converter does. 173 files convert only after
    # programs/patches.yaml is applied, and reading the raw file skipped every one of
    # them -- so a morphology defect confined to repaired content was never gated.
    man = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    for f in corpus_files():
        data = f.read_bytes()
        entry = man.get(rel(f))
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
                stats["file_repaired"] += 1
            except repair.PatchError:
                stats["patch_failed"] += 1
                continue
        try:
            root = LE.fromstring(data, parser)
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
                    failure_reasons[a.note] += 1
                    if "unknown analysis-control prefix" in a.note:
                        stats["unknown_control"] += 1
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
    print(f"  unknown controls  : {stats['unknown_control']:,}")
    print(f"  dangling selectors: {stats['selector_dangling']:,}")
    print(f"\nseparator forms  : {dict(seps.most_common())}")
    print(f"field4 kinds     : {dict(f4.most_common())}")
    print(f"selection kinds  : {dict(sel_kinds.most_common())}")
    print(f"lowest index used: {dict(sorted(idx_min.items())[:4])}")
    print(f"\nreport -> {out}")
    print(f"failure reasons: {dict(failure_reasons.most_common())}")
    problems = gate_problems(stats, failure_reasons)
    for problem in problems:
        print("GATE FAIL:", problem)
    return 1 if problems else 0

if __name__ == "__main__":
    raise SystemExit(main())
