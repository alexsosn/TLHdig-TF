#!/usr/bin/env python
"""Research-only diagnosis of `mrpN` on nested source `<w>` elements for #92.

TLHdig-TF intentionally does not emit a second `word`/`analysis` node for a `<w>` nested
inside another `<w>`: the enclosing word's byte span already contains the nested word.
This script measures the morphology attached to those skipped nested elements so the
source→TF analysis census can distinguish ontology scope from accidental loss.

No production morphology parser is reused here.  We apply only the committed repair
manifest and inspect parsed XML attributes directly.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re
import sys

import lxml.etree as LE

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = ROOT / "programs"
sys.path.insert(0, str(PROGRAMS))

from tlhdig import repair  # noqa: E402
from tlhdig.paths import PATCHES  # noqa: E402
from research_mrp_markers import source_base_field, split_broad_prefix  # noqa: E402

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


def main() -> int:
    excluded = exclusions()
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    nested_words = 0
    nested_candidate_words = 0
    candidates = 0
    marker_candidates = 0
    prefix_counts: Counter[str] = Counter()
    project_counts: Counter[str] = Counter()
    examples: list[dict[str, object]] = []
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
            root = LE.fromstring(data)
        except LE.XMLSyntaxError as exc:
            anomalies.append(f"{rel}: XML parse failed: {exc}")
            continue
        div1 = root.find("body/div1")
        text = div1.find("text") if div1 is not None else None
        if text is None:
            anomalies.append(f"{rel}: missing body/div1/text")
            continue

        project = Path(rel).parts[0]
        for word in text.iter("w"):
            if not any(a.tag == "w" for a in word.iterancestors()):
                continue
            nested_words += 1
            rows = []
            for attr, raw in word.attrib.items():
                m = MRP_RE.match(attr)
                if not m:
                    continue
                index = int(m.group(1))
                prefix, remainder = split_broad_prefix(source_base_field(raw))
                rows.append((index, attr, raw, prefix, remainder))
            if not rows:
                continue
            nested_candidate_words += 1
            project_counts[project] += 1
            for index, attr, raw, prefix, remainder in sorted(rows):
                candidates += 1
                if prefix:
                    marker_candidates += 1
                    prefix_counts[prefix] += 1
                if len(examples) < 60:
                    examples.append(
                        {
                            "file": rel,
                            "attribute": attr,
                            "index": index,
                            "mrp0sel": word.get("mrp0sel", ""),
                            "raw": raw,
                            "possiblePrefix": prefix,
                            "remainder": remainder,
                            "parentWordText": "".join(word.getparent().itertext())[:240]
                            if word.getparent() is not None
                            else "",
                            "nestedWordText": "".join(word.itertext())[:160],
                        }
                    )

    payload = {
        "schema": 1,
        "nestedWords": nested_words,
        "nestedCandidateWords": nested_candidate_words,
        "nestedMrpCandidates": candidates,
        "nestedPossiblePrefixCandidates": marker_candidates,
        "possiblePrefixCounts": dict(prefix_counts.most_common()),
        "projects": dict(project_counts.most_common()),
        "examples": examples,
        "anomalies": anomalies,
        "interpretation": (
            "These are morphology candidates attached to <w> elements nested inside "
            "another <w>. The converter intentionally skips those elements as separate "
            "word/analysis nodes because the enclosing word's byte span already covers "
            "their textual content."
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if anomalies else 0


if __name__ == "__main__":
    raise SystemExit(main())
