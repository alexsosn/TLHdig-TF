#!/usr/bin/env python
"""Issue #20 research harness: inventory every PUA cuneiform occurrence.

Research-only.  This script does not classify or change corpus data.  It independently
counts PUA code points in the repaired source lb/@cu stream and the shipped TF graph,
then records how those code points participate in the existing sign alignment and in the
corpus-learned signmap.  Scholarly/external identity evidence is deliberately *not*
manufactured here; it belongs in the research interpretation alongside pinned sources.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys
import unicodedata

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, repair
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, PROGRAMS, REPORTS, ROOT, corpus_files, rel

JSON_OUT = REPORTS / "research-pua-inventory.json"
MD_OUT = REPORTS / "research-pua-inventory.md"


def is_pua_char(c: str) -> bool:
    cp = ord(c)
    return (
        0xE000 <= cp <= 0xF8FF
        or 0xF0000 <= cp <= 0xFFFFD
        or 0x100000 <= cp <= 0x10FFFD
    )


def cp_name(c: str) -> str:
    return f"U+{ord(c):04X}"


def _local(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else ""


def source_inventory() -> tuple[Counter, Counter, list[str]]:
    """Count PUA code points in the exact repaired source population used by build."""
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}
    points: Counter = Counter()
    lines: Counter = Counter()
    problems: list[str] = []

    for path in corpus_files():
        src_file = rel(path)
        if src_file == ENCRYPTED:
            continue
        data = path.read_bytes()
        entry = patches.get(src_file)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError as exc:
                problems.append(f"{src_file}: patch failed: {exc}")
                continue
        try:
            root = ET.fromstring(data)
        except ET.XMLSyntaxError:
            # Mirrors the current immutable conversion exclusion population: malformed
            # source is not silently invented into the graph.
            continue
        div1 = root.find("body/div1")
        text = div1.find("text") if div1 is not None else None
        if text is None:
            continue
        for node in text.iter():
            if _local(node) != "lb":
                continue
            cu = node.get("cu") or ""
            seen = set()
            for c in cu:
                if is_pua_char(c):
                    points[cp_name(c)] += 1
                    seen.add(cp_name(c))
            for cp in seen:
                lines[cp] += 1
    return points, lines, problems


def learned_signmap() -> dict[str, list[dict]]:
    """Record circular, corpus-learned evidence separately so it cannot masquerade as proof."""
    out: dict[str, list[dict]] = defaultdict(list)
    path = PROGRAMS / "signmap.tsv"
    with path.open(encoding="utf8", newline="") as fh:
        for row in csv.reader((line for line in fh if not line.startswith("#")), delimiter="\t"):
            if len(row) < 5:
                continue
            reading, glyph, confidence, top_obs, total_obs = row[:5]
            pua = sorted({cp_name(c) for c in glyph if is_pua_char(c)})
            for cp in pua:
                out[cp].append(
                    {
                        "reading": reading,
                        "glyph": glyph,
                        "confidence": float(confidence),
                        "topObs": int(top_obs),
                        "totalObs": int(total_obs),
                    }
                )
    for rows in out.values():
        rows.sort(key=lambda r: (-r["topObs"], r["reading"]))
    return dict(sorted(out.items()))


def graph_inventory() -> tuple[dict, list[str]]:
    from tf.fabric import Fabric

    tf_dir = ROOT / "tf" / TF_VERSION
    TF = Fabric(locations=str(tf_dir), silent="deep")
    api = TF.load("otype cu cu_pua cu_sign cu_aligned sym src_file lnr", silent="deep")
    if api is False or api is None:
        return {}, [f"tf/{TF_VERSION}: cannot load required PUA research features"]

    F = api.F
    occurrences: Counter = Counter()
    lines: Counter = Counter()
    alignment_levels: dict[str, Counter] = defaultdict(Counter)
    assigned: Counter = Counter()
    assigned_readings: dict[str, Counter] = defaultdict(Counter)
    mixed_values: dict[str, Counter] = defaultdict(Counter)
    examples: dict[str, list[dict]] = defaultdict(list)
    problems: list[str] = []

    for line in F.otype.s("line"):
        cu = F.cu.v(line) or ""
        pua_chars = [c for c in cu if is_pua_char(c)]
        if not pua_chars:
            if (F.cu_pua.v(line) or 0) != 0:
                problems.append(f"line {line}: cu_pua is nonzero but cu contains no PUA")
            continue
        expected = len(pua_chars)
        recorded = F.cu_pua.v(line) or 0
        if recorded != expected:
            problems.append(f"line {line}: cu_pua={recorded} but counted {expected}")
        cps = [cp_name(c) for c in pua_chars]
        for cp in cps:
            occurrences[cp] += 1
            alignment_levels[cp][str(F.cu_aligned.v(line) or 0)] += 1
        for cp in set(cps):
            lines[cp] += 1
            if len(examples[cp]) < 10:
                examples[cp].append(
                    {
                        "lineNode": line,
                        "lnr": F.lnr.v(line),
                        "cu": cu,
                    }
                )

    for sign in F.otype.s("sign"):
        value = F.cu_sign.v(sign)
        if not value:
            continue
        pua_chars = [c for c in value if is_pua_char(c)]
        if not pua_chars:
            continue
        non_pua = [c for c in value if not is_pua_char(c)]
        reading = F.sym.v(sign) or ""
        for c in pua_chars:
            cp = cp_name(c)
            assigned[cp] += 1
            assigned_readings[cp][reading] += 1
            if non_pua:
                mixed_values[cp][value] += 1

    result = {}
    for cp in sorted(set(occurrences) | set(assigned)):
        result[cp] = {
            "codepoint": cp,
            "occurrencesInTfCu": occurrences[cp],
            "linesInTfCu": lines[cp],
            "alignedAssignments": assigned[cp],
            "alignmentLevelOccurrences": dict(sorted(alignment_levels[cp].items(), key=lambda x: int(x[0]))),
            "topAssignedReadings": [
                {"reading": reading, "count": count}
                for reading, count in assigned_readings[cp].most_common(30)
            ],
            "mixedAssignedValues": [
                {"value": value, "count": count}
                for value, count in mixed_values[cp].most_common(20)
            ],
            "examples": examples[cp],
        }
    return result, problems


def write_outputs(payload: dict) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf8")

    lines = [
        "# PUA cuneiform research inventory",
        "",
        f"TF version: `{payload['tfVersion']}`",
        "",
        "Research-only measurement for issue #20. `mapped`/`unmapped` is intentionally not",
        "assigned here; corpus-learned readings are circular evidence and are listed separately.",
        "",
        "| codepoint | source occurrences | TF occurrences | TF lines | aligned assignments | level 0 occurrences |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cp, row in payload["codepoints"].items():
        levels = row["alignmentLevelOccurrences"]
        lines.append(
            f"| `{cp}` | {row['occurrencesInSourceCu']:,} | {row['occurrencesInTfCu']:,} | "
            f"{row['linesInTfCu']:,} | {row['alignedAssignments']:,} | {levels.get('0', 0):,} |"
        )
        tops = row.get("topAssignedReadings", [])[:10]
        if tops:
            lines.extend([
                "",
                f"### `{cp}` top aligned readings",
                "",
                ", ".join(f"`{r['reading']}` {r['count']:,}" for r in tops),
            ])
        learned = row.get("learnedSignmap", [])[:10]
        if learned:
            lines.extend([
                "",
                "Corpus-learned signmap evidence (not independent proof):",
                "",
                ", ".join(
                    f"`{r['reading']}` {r['topObs']:,}/{r['totalObs']:,} ({r['confidence']:.3f})"
                    for r in learned
                ),
            ])
    if payload["problems"]:
        lines.extend(["", "## Problems", ""] + [f"- {p}" for p in payload["problems"]])
    else:
        lines.extend(["", "## Integrity", "", "Source/TF PUA counts agree and every existing `cu_pua` value equals the codepoint count on its line."])
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf8")


def main() -> int:
    src_points, src_lines, src_problems = source_inventory()
    graph, graph_problems = graph_inventory()
    learned = learned_signmap()
    problems = list(src_problems) + list(graph_problems)

    all_cps = sorted(set(src_points) | set(graph))
    codepoints = {}
    for cp in all_cps:
        row = dict(graph.get(cp, {}))
        row.setdefault("codepoint", cp)
        row["occurrencesInSourceCu"] = src_points[cp]
        row["linesInSourceCu"] = src_lines[cp]
        row["learnedSignmap"] = learned.get(cp, [])
        codepoints[cp] = row
        if row.get("occurrencesInTfCu", 0) != src_points[cp]:
            problems.append(
                f"{cp}: source occurrences {src_points[cp]} != TF occurrences {row.get('occurrencesInTfCu', 0)}"
            )
        if row.get("linesInTfCu", 0) != src_lines[cp]:
            problems.append(
                f"{cp}: source lines {src_lines[cp]} != TF lines {row.get('linesInTfCu', 0)}"
            )

    payload = {
        "schema": 1,
        "issue": 20,
        "tfVersion": TF_VERSION,
        "sourceCorpus": str(CORPUS.relative_to(ROOT)),
        "codepoints": codepoints,
        "problems": problems,
    }
    write_outputs(payload)

    print("PUA RESEARCH INVENTORY")
    print(f"tfVersion={TF_VERSION}")
    for cp, row in codepoints.items():
        print(
            f"{cp}: source={row['occurrencesInSourceCu']:,} "
            f"tf={row.get('occurrencesInTfCu', 0):,} "
            f"lines={row.get('linesInTfCu', 0):,} "
            f"assigned={row.get('alignedAssignments', 0):,}"
        )
        tops = row.get("topAssignedReadings", [])[:8]
        if tops:
            print("  aligned readings: " + ", ".join(f"{r['reading']}={r['count']:,}" for r in tops))
    if problems:
        print(f"FAIL: {len(problems)} integrity problem(s)")
        for problem in problems[:20]:
            print("  " + problem)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
