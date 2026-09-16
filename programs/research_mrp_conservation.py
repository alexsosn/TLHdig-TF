#!/usr/bin/env python
"""Research-only structural source→TF morphology conservation gate for issue #92.

Every source ``mrpN`` candidate in repaired ``body/div1/text`` is assigned to exactly
one representation class before counts are compared with the current TF artifact:

* ``nested`` — the source ``<w>`` is contained in another source ``<w>`` (#109);
* ``preline`` — a top-level word precedes the first ``<lb>`` (#52/#83);
* ``layout_only`` — a later top-level word has no sign-producing token (#105);
* ``represented`` — the population that the current converter can represent as a word
  with analysis nodes.

This is deliberately independent of the production morphology parser. It shares the
converter's byte scanner and sign tokeniser only to classify XML/slot representation
boundaries. Marker detection is imported from the broad research detector, not from
production parsing.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = ROOT / "programs"
sys.path.insert(0, str(PROGRAMS))

from tlhdig import repair, signs, source  # noqa: E402
from tlhdig.paths import PATCHES  # noqa: E402
from research_mrp_markers import (  # noqa: E402
    CORPUS,
    excluded_paths,
    source_base_field,
    source_inventory,
    split_broad_prefix,
    tf_inventory,
)

MRP_RE = re.compile(r"^mrp(\d+)$")
CATEGORIES = ("nested", "preline", "layout_only", "represented")
OWNERS = {
    "nested": "#109",
    "preline": "#52/#83",
    "layout_only": "#105",
    "represented": "#92 target population",
}


def in_span(child, parent) -> bool:
    return (
        parent.inner_start is not None
        and parent.inner_end is not None
        and parent.inner_start <= child.outer_start
        and child.outer_end <= parent.inner_end
    )


def nested_word_ids(word_spans: list) -> set[int]:
    """Classify XML-nested words in O(n log n) without morphology semantics."""
    nested: set[int] = set()
    stack: list = []
    for sp in sorted(word_spans, key=lambda x: (x.outer_start, -x.outer_end)):
        while stack and sp.outer_start >= stack[-1].outer_end:
            stack.pop()
        if stack:
            if sp.outer_end > stack[-1].outer_end:
                raise ValueError("crossing <w> byte spans in strictly parsed XML")
            nested.add(id(sp))
        stack.append(sp)
    return nested


def candidate_rows(sp) -> list[tuple[int, str, str]]:
    rows = []
    for key, raw in sp.attrs.items():
        match = MRP_RE.match(key)
        if match:
            rows.append((int(match.group(1)), key, raw))
    return sorted(rows)


def representation_accounting() -> dict:
    excluded = excluded_paths()
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    candidate_counts = Counter()
    marker_counts = Counter()
    word_counts = Counter()
    prefix_counts: dict[str, Counter] = defaultdict(Counter)
    examples: dict[str, list] = defaultdict(list)
    anomalies: list[str] = []

    for path in sorted(CORPUS.rglob("*.xml")):
        rel = str(path.relative_to(CORPUS))
        if rel in excluded:
            continue
        data = path.read_bytes()
        entry = patches.get(rel)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError as exc:
                anomalies.append(f"{rel}: patch failed: {exc}")
                continue
        try:
            spans = source.scan(data)
        except Exception as exc:
            anomalies.append(f"{rel}: scan failed: {type(exc).__name__}: {exc}")
            continue

        text_spans = [sp for sp in spans if sp.tag == "text"]
        if len(text_spans) != 1:
            anomalies.append(f"{rel}: expected one text span, got {len(text_spans)}")
            continue
        text_sp = text_spans[0]
        word_spans = [sp for sp in spans if sp.tag == "w" and in_span(sp, text_sp)]
        try:
            nested_ids = nested_word_ids(word_spans)
        except ValueError as exc:
            anomalies.append(f"{rel}: {exc}")
            continue
        line_starts = [
            sp.outer_start for sp in spans if sp.tag == "lb" and in_span(sp, text_sp)
        ]
        first_line = min(line_starts) if line_starts else None

        for sp in word_spans:
            rows = candidate_rows(sp)
            if not rows:
                continue
            if id(sp) in nested_ids:
                category = "nested"
            elif first_line is None or sp.outer_start < first_line:
                category = "preline"
            else:
                try:
                    toks = signs.tokenise_word(source.inner_bytes(data, sp))
                except Exception as exc:
                    anomalies.append(
                        f"{rel}: cannot tokenise word at byte {sp.outer_start}: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    continue
                category = (
                    "represented" if any(tok.type != "empty" for tok in toks)
                    else "layout_only"
                )

            word_counts[category] += 1
            for index, attr, raw in rows:
                candidate_counts[category] += 1
                prefix, remainder = split_broad_prefix(source_base_field(raw))
                if prefix:
                    marker_counts[category] += 1
                    prefix_counts[category][prefix] += 1
                if len(examples[category]) < 8:
                    examples[category].append(
                        {
                            "file": rel,
                            "byteStart": sp.outer_start,
                            "attribute": attr,
                            "index": index,
                            "raw": raw,
                            "possiblePrefix": prefix,
                            "remainder": remainder,
                        }
                    )

    return {
        "candidateCounts": {name: candidate_counts[name] for name in CATEGORIES},
        "markerCounts": {name: marker_counts[name] for name in CATEGORIES},
        "candidateWords": {name: word_counts[name] for name in CATEGORIES},
        "prefixCounts": {
            name: dict(prefix_counts[name].most_common()) for name in CATEGORIES
        },
        "owners": OWNERS,
        "examples": {name: examples[name] for name in CATEGORIES},
        "anomalies": anomalies,
        "classificationOrder": list(CATEGORIES),
        "interpretation": (
            "Categories are mutually exclusive structural representation classes. "
            "Only represented candidates are expected to have one-for-one current TF "
            "analysis nodes; the other populations remain explicit fidelity/ontology lanes."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    source_inv = source_inventory()
    tf_inv = tf_inventory()
    accounting = representation_accounting()
    guards: list[str] = []

    if source_inv["unexpectedParseFailures"]:
        guards.append(
            "source inventory has unexpected parse/repair failures: "
            f"{len(source_inv['unexpectedParseFailures'])}"
        )
    if source_inv["unexpectedNoText"]:
        guards.append(
            "source inventory has documents without body/div1/text: "
            f"{len(source_inv['unexpectedNoText'])}"
        )
    if accounting["anomalies"]:
        guards.append(
            f"representation classifier has anomalies: {len(accounting['anomalies'])}"
        )

    classified_candidates = sum(accounting["candidateCounts"].values())
    if classified_candidates != source_inv["sourceMrpCandidates"]:
        guards.append(
            "structural candidate partition is not exhaustive: "
            f"classified={classified_candidates} source={source_inv['sourceMrpCandidates']}"
        )
    classified_markers = sum(accounting["markerCounts"].values())
    if classified_markers != source_inv["possiblePrefixCandidates"]:
        guards.append(
            "structural marker partition is not exhaustive: "
            f"classified={classified_markers} source={source_inv['possiblePrefixCandidates']}"
        )

    represented = accounting["candidateCounts"]["represented"]
    if represented != tf_inv["analysisNodes"]:
        guards.append(
            "represented source analyses differ from TF analysis population: "
            f"source={represented} tf={tf_inv['analysisNodes']}"
        )
    represented_markers = accounting["markerCounts"]["represented"]
    if represented_markers != tf_inv["possiblePrefixAnalysisAssignments"]:
        guards.append(
            "represented source marker population differs from TF: "
            f"source={represented_markers} "
            f"tf={tf_inv['possiblePrefixAnalysisAssignments']}"
        )

    payload = {
        "schema": 3,
        "issue": 92,
        "source": source_inv,
        "tf": tf_inv,
        "representationAccounting": accounting,
        "guards": guards,
        "interpretationGuards": [
            "A source record being structurally accounted for does not mean its semantics are preserved in TF.",
            "Nested-word morphology remains a separate fidelity/ontology research lane (#109).",
            "Pre-line morphology remains owned by the pre-line fidelity lane (#52/#83).",
            "Layout-only morphology remains owned by #105.",
            "#92 marker normalization is evaluated only on the represented source population.",
            "The broad prefix detector is discovery-oriented; every prefix family still requires an evidence-backed disposition before production normalization.",
            "Exact raw mrpN/source provenance must remain recoverable after any future derived normalization.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf8",
    )

    print("candidate accounting:", accounting["candidateCounts"])
    print("marker accounting:", accounting["markerCounts"])
    print("TF analyses:", tf_inv["analysisNodes"])
    print("TF possible-prefix assignments:", tf_inv["possiblePrefixAnalysisAssignments"])
    if guards:
        for guard in guards:
            print(f"RESEARCH GUARD: {guard}", file=sys.stderr)
        return 1
    print("structural source→TF morphology accounting: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
