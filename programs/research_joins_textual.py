#!/usr/bin/env python
"""Research-only census of textual join notation in AO:Manuscripts (issue #18).

TLHdig encodes joins both as empty AO:DirectJoin/AO:InDirectJoin elements and in
mixed-content notation such as ``{€1} +`` and ``{€2} (+)`` after manuscript entries.
This script measures the latter family without changing conversion behavior.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig.paths import CORPUS, REPORTS, ROOT

ENTRY_TAGS = {"TxtPubl", "InvNr", "TextPubl"}
OPERATOR_TAGS = {"DirectJoin", "InDirectJoin"}
SIGLUM = re.compile(r"\{\s*(€\d+)\s*\}")
MARKER = re.compile(r"\(\+\)\s*\?|\(\+\)|\+\+|\+\s*\?|\+")
FULL_MARKER = re.compile(r"^(?:\(\+\)\s*\?|\(\+\)|\+\+|\+\s*\?|\+)$")
SPACED_DIRECT = re.compile(r"\s+\+\s+")
STATUS_SUFFIX = re.compile(r"(?:\+\+|\(\+\)(?:\(\+\))*|\+)$")


def lname(element) -> str:
    tag = element.tag
    return ET.QName(tag).localname if isinstance(tag, str) else ""


def parse(data: bytes):
    for recover in (False, True):
        try:
            root = ET.fromstring(
                data,
                parser=ET.XMLParser(recover=recover, huge_tree=True, resolve_entities=False),
            )
        except ET.XMLSyntaxError:
            continue
        if root is not None:
            return root, not recover
    return None, False


def text_value(element) -> str:
    return " ".join("".join(element.itertext()).split())


def entry(element) -> dict:
    return {
        "tag": lname(element),
        "text": text_value(element),
        "nrAttr": (element.get("nr") or "").strip(),
    }


def marker_kind(raw: str) -> str:
    compact = raw.replace(" ", "")
    if compact == "+":
        return "direct"
    if compact == "++":
        return "direct-multi"
    if compact == "(+)":
        return "indirect"
    if compact in {"(+)?", "+?"}:
        return "uncertain"
    return "other"


def clean_chunk(raw: str | None) -> str:
    return " ".join((raw or "").split())


def next_entry(children, start: int):
    for child in children[start + 1 :]:
        if lname(child) in ENTRY_TAGS:
            return child
        if lname(child) in OPERATOR_TAGS:
            return None
    return None


def add_text_chain(relations, endpoint_pairs, *, rel, docid, block_index, text) -> int:
    """Record unambiguous ``label + label [+ label]`` text-only chains."""
    labels = [part.strip() for part in SPACED_DIRECT.split(text)]
    if len(labels) < 2 or any(not label for label in labels):
        return 0
    count = 0
    for left, right in zip(labels, labels[1:]):
        endpoint_pairs["direct:PlainText->PlainText"] += 1
        relations.append(
            {
                "src_file": rel,
                "docid": docid,
                "block": block_index,
                "kind": "direct",
                "rawMarker": "+",
                "left": {"tag": "PlainText", "text": left, "nrAttr": ""},
                "right": {"tag": "PlainText", "text": right, "nrAttr": ""},
                "leftTail": text,
                "grammar": "text-only-chain",
            }
        )
        count += 1
    return count


def main() -> int:
    summary = Counter()
    marker_counts = Counter()
    marker_contexts = Counter()
    block_families = Counter()
    endpoint_pairs = Counter()
    tail_sigla = Counter()
    attr_vs_tail_sigla = Counter()
    text_only_shapes = Counter()
    ignored_comments = Counter()
    relations = []
    unresolved = []

    for path in sorted(CORPUS.rglob("*.xml")):
        rel = path.relative_to(CORPUS).as_posix()
        summary["files"] += 1
        root, strict = parse(path.read_bytes())
        if root is None:
            summary["unrecoverable"] += 1
            continue
        if not strict:
            summary["recovered_files"] += 1

        docids = root.xpath("//*[local-name()='AOHeader']/*[local-name()='docID']/text()")
        docid = str(docids[0]).strip() if docids else Path(rel).stem

        for block_index, block in enumerate(root.xpath("//*[local-name()='Manuscripts']")):
            summary["blocks"] += 1
            children = [c for c in block if isinstance(c.tag, str)]
            has_explicit = any(lname(c) in OPERATOR_TAGS for c in children)
            has_textual = False
            textual_relations_here = 0

            initial = clean_chunk(block.text)
            if initial:
                text_only_shapes[initial] += 1
                chain_count = add_text_chain(
                    relations,
                    endpoint_pairs,
                    rel=rel,
                    docid=docid,
                    block_index=block_index,
                    text=initial,
                )
                if chain_count:
                    has_textual = True
                    textual_relations_here += chain_count
                    marker_counts["direct"] += chain_count
                    marker_contexts["block-text:direct"] += chain_count
                elif STATUS_SUFFIX.search(initial):
                    # A trailing ``+``, ``++`` or ``(+)`` says the record participates in
                    # a composite/join but does not name a target in this block. Preserve
                    # it as unresolved status; do not invent an edge.
                    has_textual = True
                    raw_markers = MARKER.findall(initial)
                    for raw in raw_markers:
                        marker_counts[marker_kind(raw)] += 1
                        marker_contexts[f"block-status:{marker_kind(raw)}"] += 1
                    unresolved.append(
                        {
                            "src_file": rel,
                            "docid": docid,
                            "block": block_index,
                            "where": "block.text",
                            "text": initial,
                            "reason": "join-status suffix without named target",
                        }
                    )

            for index, child in enumerate(children):
                name = lname(child)
                tail = clean_chunk(child.tail)
                if name not in ENTRY_TAGS:
                    continue

                sigla = SIGLUM.findall(tail)
                if sigla:
                    for siglum in sigla:
                        tail_sigla[siglum] += 1
                    attr = (child.get("nr") or "").strip()
                    if attr:
                        attr_vs_tail_sigla["both"] += 1
                        if attr in sigla:
                            attr_vs_tail_sigla["same"] += 1
                        else:
                            attr_vs_tail_sigla["conflict"] += 1
                    else:
                        attr_vs_tail_sigla["tail-only"] += 1
                elif (child.get("nr") or "").strip():
                    attr_vs_tail_sigla["attr-only"] += 1

                remainder = clean_chunk(SIGLUM.sub("", tail))
                if not remainder:
                    continue
                if remainder.startswith("#"):
                    ignored_comments[remainder] += 1
                    continue
                if not FULL_MARKER.fullmatch(remainder):
                    # Partial punctuation such as ``(+`` in repaired XML or free prose is
                    # evidence, but not a safely parseable relation.
                    if any(ch in remainder for ch in "+("):
                        has_textual = True
                        unresolved.append(
                            {
                                "src_file": rel,
                                "docid": docid,
                                "block": block_index,
                                "where": f"tail:{name}",
                                "text": tail,
                                "reason": "non-canonical textual join tail",
                            }
                        )
                    continue

                raw = remainder
                kind = marker_kind(raw)
                has_textual = True
                marker_counts[kind] += 1
                marker_contexts[f"tail:{name}:{kind}"] += 1

                right = next_entry(children, index)
                if right is not None:
                    right_index = children.index(right)
                    between = children[index + 1 : right_index]
                else:
                    between = []
                explicit_between = any(lname(c) in OPERATOR_TAGS for c in between)
                nonentry_between = any(
                    lname(c) not in ENTRY_TAGS and lname(c) not in OPERATOR_TAGS for c in between
                )
                if right is not None and not explicit_between and not nonentry_between:
                    left_row = entry(child)
                    right_row = entry(right)
                    endpoint_pairs[f"{kind}:{left_row['tag']}->{right_row['tag']}"] += 1
                    relations.append(
                        {
                            "src_file": rel,
                            "docid": docid,
                            "block": block_index,
                            "kind": kind,
                            "rawMarker": raw,
                            "left": left_row,
                            "right": right_row,
                            "leftTail": tail,
                            "grammar": "element-tail",
                        }
                    )
                    textual_relations_here += 1
                else:
                    unresolved.append(
                        {
                            "src_file": rel,
                            "docid": docid,
                            "block": block_index,
                            "where": f"tail:{name}",
                            "text": tail,
                            "reason": (
                                "ambiguous textual join adjacency: "
                                f"right={lname(right) if right is not None else None}, "
                                f"explicitBetween={explicit_between}, nonEntryBetween={nonentry_between}"
                            ),
                        }
                    )

            if has_explicit and has_textual:
                family = "mixed-explicit-and-textual"
            elif has_explicit:
                family = "explicit-only"
            elif has_textual:
                family = "textual-only"
            else:
                family = "no-join-marker"
            block_families[family] += 1
            if textual_relations_here:
                summary["blocks_with_extracted_textual_relations"] += 1

    summary["textual_relations_extracted"] = len(relations)
    summary["textual_relations_unresolved"] = len(unresolved)
    summary["textual_markers_total"] = sum(marker_counts.values())
    summary["tail_sigla_total"] = sum(tail_sigla.values())
    summary["ignored_comment_chunks"] = sum(ignored_comments.values())

    payload = {
        "schema": 2,
        "issue": 18,
        "corpus": str(CORPUS.relative_to(ROOT)),
        "summary": dict(sorted(summary.items())),
        "blockFamilies": dict(block_families.most_common()),
        "markerCounts": dict(marker_counts.most_common()),
        "markerContexts": dict(marker_contexts.most_common()),
        "endpointTypePairs": dict(endpoint_pairs.most_common()),
        "tailSigla": dict(tail_sigla.most_common()),
        "attrVsTailSigla": dict(attr_vs_tail_sigla.most_common()),
        "textOnlyShapes": dict(text_only_shapes.most_common()),
        "ignoredComments": dict(ignored_comments.most_common()),
        "relations": relations,
        "unresolved": unresolved,
    }
    REPORTS.mkdir(exist_ok=True)
    json_path = REPORTS / "joins-textual-research.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf8")

    lines = [
        "# Textual manuscript join notation census",
        "",
        "Research-only supplement for issue #18. It measures mixed-content `+`, `++`,",
        "`(+)` and uncertainty-shaped markers separately from AO:DirectJoin /",
        "AO:InDirectJoin elements. Comment text and publication-label `+` suffixes are",
        "not promoted to binary relations.",
        "",
        "## Summary",
        "",
        "| metric | count |",
        "|---|---:|",
    ]
    for key, value in sorted(summary.items()):
        lines.append(f"| `{key}` | {value:,} |")
    for title, counter in (
        ("Block encoding families", block_families),
        ("Textual marker kinds", marker_counts),
        ("Extracted endpoint types", endpoint_pairs),
        ("Siglum storage", attr_vs_tail_sigla),
    ):
        lines += ["", f"## {title}", "", "| value | count |", "|---|---:|"]
        for key, value in counter.most_common():
            lines.append(f"| `{key}` | {value:,} |")
    lines += [
        "",
        "## Research boundary",
        "",
        "Binary relations are emitted only for a canonical element-tail marker followed",
        "by another manuscript entry without an intervening explicit operator/corrupt",
        "child, or for an unambiguous text-only `label + label` chain. Target-less status",
        "suffixes and malformed punctuation remain explicit unresolved records.",
        "",
    ]
    md_path = REPORTS / "joins-textual-research.md"
    md_path.write_text("\n".join(lines), encoding="utf8")
    print(md_path.read_text(encoding="utf8"))
    print(f"machine-readable inventory: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
