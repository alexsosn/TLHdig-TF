#!/usr/bin/env python
"""Independent #20 gate: conservation of source/TF cu and exact PUA status.

This intentionally does not import the converter's PUA counting/classification helper.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import TF_VERSION, appcheck, compact, repair
from tlhdig.paths import ENCRYPTED, PATCHES, ROOT, corpus_files, rel

FROZEN_TOTAL = 3_643
FROZEN_MAPPED = 924
FROZEN_UNRESOLVED = 2_719
TABLE = ROOT / "programs" / "pua-status.json"


def is_private(c: str) -> bool:
    n = ord(c)
    return (0xE000 <= n <= 0xF8FF or 0xF0000 <= n <= 0xFFFFD
            or 0x100000 <= n <= 0x10FFFD)


def undeclared_codepoints(observed, declared) -> list[str]:
    return sorted(set(observed) - set(declared))


def counts(cu: str, mapped: set[str]) -> tuple[int, int, Counter]:
    points = [f"U+{ord(c):04X}" for c in cu if is_private(c)]
    return (len(points), sum(cp not in mapped for cp in points), Counter(points))


def source_cu():
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}
    for path in corpus_files():
        key = rel(path)
        if key == ENCRYPTED:
            continue
        data = path.read_bytes()
        if key in patches:
            data = repair.apply(data, patches[key][1], expect_sha=patches[key][0])
        try:
            root = ET.fromstring(data)
        except ET.XMLSyntaxError:
            continue
        div = root.find("body/div1")
        text = div.find("text") if div is not None else None
        if text is None:
            continue
        for node in text.iter():
            if isinstance(node.tag, str) and ET.QName(node).localname == "lb":
                value = node.get("cu") or ""
                if value:
                    yield value


def main() -> int:
    from tlhdig.pua import load_status_table
    table = load_status_table(TABLE)
    declared = set(table["codepoints"])
    mapped = {cp for cp, item in table["codepoints"].items()
              if item["status"] == "mapped-deliberate-pua"}
    source_strings = Counter(source_cu())
    source_points = Counter()
    for cu, multiplicity in source_strings.items():
        source_points.update({cp: n * multiplicity
                              for cp, n in counts(cu, mapped)[2].items()})

    directory = ROOT / "tf" / TF_VERSION
    required = ("otype", "cu", "cu_pua", "cu_pua_unmapped")
    if any(not (directory / f"{name}.tf").is_file() for name in required):
        print("PUA gate: current TF artifact missing a required feature")
        return 1
    low, high = appcheck.node_ranges(directory)["line"]
    cu_lines = {n: value for n, value in compact.read_values(directory / "cu.tf").items()
                if low <= n <= high}
    tf_strings = Counter(cu_lines.values())
    tf_points = Counter()
    recorded_all = compact.read_values(directory / "cu_pua.tf")
    recorded_unmapped = compact.read_values(directory / "cu_pua_unmapped.tf")
    problems = []
    for line, cu in cu_lines.items():
        total, unresolved, points = counts(cu, mapped)
        tf_points.update(points)
        if int(recorded_all.get(line, 0) or 0) != total:
            problems.append(f"line {line}: cu_pua != {total}")
        if int(recorded_unmapped.get(line, 0) or 0) != unresolved:
            problems.append(f"line {line}: cu_pua_unmapped != {unresolved}")
    if any(n not in cu_lines for n in recorded_unmapped):
        problems.append("cu_pua_unmapped contains values outside cu-bearing lines")
    if source_strings != tf_strings:
        problems.append("verbatim source/TF cu line-string multisets disagree")
    if source_points != tf_points:
        problems.append("source/TF PUA codepoint inventories disagree")
    unseen = undeclared_codepoints(source_points | tf_points, declared)
    if unseen:
        problems.append(f"undeclared PUA values: {', '.join(unseen)}")
    total = sum(tf_points.values())
    direct = sum(tf_points[k] for k in mapped)
    unresolved = total - direct
    if (total, direct, unresolved) != (
        FROZEN_TOTAL, FROZEN_MAPPED, FROZEN_UNRESOLVED
    ):
        problems.append(f"PUA totals changed: {(total, direct, unresolved)}")
    print(f"PUA source/TF: {total:,} total; {direct:,} directly mapped; "
          f"{unresolved:,} unresolved; {len(unseen)} unknown")
    for problem in problems[:30]:
        print("PUA gate FAILED:", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
