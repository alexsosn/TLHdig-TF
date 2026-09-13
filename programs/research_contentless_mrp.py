#!/usr/bin/env python
"""Research-only diagnosis for the source->TF morphology deficit found by #92.

Measure mrpN attributes attached to source <w> elements that the release converter turns
into layout nodes because keep_empty=False leaves no sign-producing token.  This script
shares byte spans/word tokenisation with conversion only to classify that representation
boundary; it does not reuse the morphology parser.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = ROOT / "programs"
sys.path.insert(0, str(PROGRAMS))

from tlhdig import repair, signs, source  # noqa: E402
from tlhdig.paths import PATCHES  # noqa: E402
from research_mrp_markers import split_broad_prefix, source_base_field  # noqa: E402

CORPUS = ROOT / "corpus" / "TLHdig-0.3"
EXCLUDED = PROGRAMS / "excluded.txt"
MRP_RE = re.compile(r"^mrp(\d+)$")


def exclusions() -> set[str]:
    out = set()
    for raw in EXCLUDED.read_text(encoding="utf8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.add(line.split("\t", 1)[0])
    return out


def in_span(child, parent) -> bool:
    return (
        parent.inner_start is not None
        and parent.inner_end is not None
        and parent.inner_start <= child.outer_start
        and child.outer_end <= parent.inner_end
    )


def main() -> int:
    excluded = exclusions()
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    candidate_total = 0
    marker_total = 0
    word_total = 0
    prefix_counts = Counter()
    project_counts = Counter()
    examples = []
    anomalies = []

    for path in sorted(CORPUS.rglob("*.xml")):
        rel = str(path.relative_to(CORPUS))
        if rel in excluded:
            continue
        data = path.read_bytes()
        entry = patches.get(rel)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError as e:
                anomalies.append(f"{rel}: patch failed: {e}")
                continue
        try:
            spans = source.scan(data)
        except Exception as e:
            anomalies.append(f"{rel}: scan failed: {type(e).__name__}: {e}")
            continue
        text_spans = [sp for sp in spans if sp.tag == "text"]
        if len(text_spans) != 1:
            anomalies.append(f"{rel}: expected one text span, got {len(text_spans)}")
            continue
        text_sp = text_spans[0]
        project = Path(rel).parts[0]
        for sp in spans:
            if sp.tag != "w" or not in_span(sp, text_sp):
                continue
            candidates = [
                (int(m.group(1)), k, v)
                for k, v in sp.attrs.items()
                if (m := MRP_RE.match(k))
            ]
            if not candidates:
                continue
            toks = signs.tokenise_word(source.inner_bytes(data, sp))
            keep = [t for t in toks if t.type != "empty"]
            if keep:
                continue
            word_total += 1
            project_counts[project] += 1
            for index, attr, raw in sorted(candidates):
                candidate_total += 1
                prefix, remainder = split_broad_prefix(source_base_field(raw))
                if prefix:
                    marker_total += 1
                    prefix_counts[prefix] += 1
                if len(examples) < 40:
                    examples.append({
                        "file": rel,
                        "attribute": attr,
                        "index": index,
                        "mrp0sel": sp.attrs.get("mrp0sel", ""),
                        "raw": raw,
                        "possiblePrefix": prefix,
                        "remainder": remainder,
                        "tokenTypes": [t.type for t in toks],
                    })

    payload = {
        "schema": 1,
        "layoutOnlyCandidateWords": word_total,
        "layoutOnlyMrpCandidates": candidate_total,
        "layoutOnlyPossiblePrefixCandidates": marker_total,
        "possiblePrefixCounts": dict(prefix_counts.most_common()),
        "projects": dict(project_counts.most_common()),
        "examples": examples,
        "anomalies": anomalies,
        "interpretation": (
            "These mrpN attributes are source morphology attached to <w> elements "
            "that keep_empty=False represents as layout rather than word nodes; the "
            "current converter returns before emitting analysis nodes for them."
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if anomalies else 0


if __name__ == "__main__":
    raise SystemExit(main())
