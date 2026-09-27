#!/usr/bin/env python
"""Research-only diagnosis of morphology on top-level words before first `<lb>` for #92.

The converter currently returns from `_State.word()` while `self.line is None`, so #52/#83
has already established that readable top-level pre-line words are not represented as TF
word/sign nodes. This probe measures only their `mrpN` candidates so the morphology census
can distinguish that known fidelity lane from marker parsing.
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

from tlhdig import repair, signs, source  # noqa: E402
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


def top_word_spans(data: bytes, spans: list, text_span) -> list:
    """Mirror converter top-level word-span selection, independent of morphology parsing."""
    w_all = [
        sp for sp in spans
        if sp.tag == "w"
        and text_span.inner_start <= sp.outer_start < text_span.inner_end
    ]
    out = []
    for sp in w_all:
        if any(
            other is not sp
            and other.outer_start <= sp.outer_start
            and sp.outer_end <= other.outer_end
            for other in w_all
        ):
            continue
        out.append(sp)
    return out


def main() -> int:
    excluded = exclusions()
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    words = 0
    readable_words = 0
    candidates = 0
    readable_candidates = 0
    marker_candidates = 0
    prefix_counts: Counter[str] = Counter()
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
            spans = source.scan(data)
            root = LE.fromstring(data)
        except (LE.XMLSyntaxError, ValueError) as exc:
            anomalies.append(f"{rel}: parse failed: {type(exc).__name__}: {exc}")
            continue
        div1 = root.find("body/div1")
        text = div1.find("text") if div1 is not None else None
        if text is None:
            anomalies.append(f"{rel}: missing body/div1/text")
            continue
        text_span = next((sp for sp in spans if sp.tag == "text" and sp.inner_start is not None), None)
        if text_span is None:
            anomalies.append(f"{rel}: missing text byte span")
            continue
        top_words = [
            node for node in text.iter("w")
            if not any(a.tag == "w" for a in node.iterancestors())
        ]
        word_spans = top_word_spans(data, spans, text_span)
        if len(top_words) != len(word_spans):
            anomalies.append(f"{rel}: top word/span mismatch {len(top_words)} != {len(word_spans)}")
            continue

        before_line = True
        span_for = {id(node): sp for node, sp in zip(top_words, word_spans)}
        for node in text.iter():
            if not isinstance(node.tag, str):
                continue
            if node.tag == "lb":
                before_line = False
                continue
            if node.tag != "w" or id(node) not in span_for or not before_line:
                continue
            rows = []
            for attr, raw in node.attrib.items():
                m = MRP_RE.match(attr)
                if not m:
                    continue
                prefix, remainder = split_broad_prefix(source_base_field(raw))
                rows.append((int(m.group(1)), attr, raw, prefix, remainder))
            if not rows:
                continue
            words += 1
            sp = span_for[id(node)]
            toks = signs.tokenise_word(source.inner_bytes(data, sp))
            readable = any(t.type != "empty" for t in toks)
            if readable:
                readable_words += 1
            for index, attr, raw, prefix, remainder in sorted(rows):
                candidates += 1
                if readable:
                    readable_candidates += 1
                if prefix:
                    marker_candidates += 1
                    prefix_counts[prefix] += 1
                if len(examples) < 40:
                    examples.append({
                        "file": rel,
                        "attribute": attr,
                        "index": index,
                        "readable": readable,
                        "mrp0sel": node.get("mrp0sel", ""),
                        "raw": raw,
                        "possiblePrefix": prefix,
                        "remainder": remainder,
                        "wordText": "".join(node.itertext())[:160],
                    })

    payload = {
        "schema": 1,
        "prelineCandidateWords": words,
        "prelineReadableCandidateWords": readable_words,
        "prelineMrpCandidates": candidates,
        "prelineReadableMrpCandidates": readable_candidates,
        "prelinePossiblePrefixCandidates": marker_candidates,
        "possiblePrefixCounts": dict(prefix_counts.most_common()),
        "examples": examples,
        "anomalies": anomalies,
        "interpretation": (
            "These candidates belong to top-level source words before the first line boundary. "
            "The current converter's pre-line guard is already tracked by #52/#83; this probe "
            "only measures its morphology impact for #92 accounting."
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if anomalies else 0


if __name__ == "__main__":
    raise SystemExit(main())
