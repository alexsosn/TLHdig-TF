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
# Longest first. ``(+)?`` / ``(+)?``-like uncertainty is kept distinct rather than
# silently normalised to an ordinary indirect join.
MARKER = re.compile(r"\(\+\)\s*\?|\(\+\)|\+\+|\+\s*\?|\+")
PURE_SEP = re.compile(r"^[\s{}€0-9()+?#.¬]+$")


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


def main() -> int:
    summary = Counter()
    marker_counts = Counter()
    marker_contexts = Counter()
    block_families = Counter()
    endpoint_pairs = Counter()
    tail_sigla = Counter()
    attr_vs_tail_sigla = Counter()
    text_only_shapes = Counter()
    unresolved_chunks = Counter()
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
                initial_markers = MARKER.findall(initial)
                if initial_markers:
                    has_textual = True
                    for raw in initial_markers:
                        marker_counts[marker_kind(raw)] += 1
                        marker_contexts[f"block-text:{marker_kind(raw)}"] += 1
                    # Text-only / legacy composite strings need a separate parser. Do not
                    # invent endpoint boundaries here; retain them as unresolved grammar.
                    text_only_shapes[initial] += 1
                    unresolved.append(
                        {
                            "src_file": rel,
                            "docid": docid,
                            "block": block_index,
                            "where": "block.text",
                            "text": initial,
                            "reason": "textual marker outside an element-tail adjacency",
                        }
                    )
                elif not children:
                    text_only_shapes[initial] += 1

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

                markers = MARKER.findall(tail)
                if not markers:
                    remainder = SIGLUM.sub("", tail).strip()
                    if remainder and not PURE_SEP.match(remainder):
                        unresolved_chunks[remainder] += 1
                    continue

                has_textual = True
                for raw in markers:
                    kind = marker_kind(raw)
                    marker_counts[kind] += 1
                    marker_contexts[f"tail:{name}:{kind}"] += 1

                # A well-formed textual binary relation has exactly one marker in the
                # current entry's tail and the next relevant child is another entry,
                # without an explicit operator intervening.
                right = next_entry(children, index)
                between = children[index + 1 : children.index(right)] if right is not None else []
                explicit_between = any(lname(c) in OPERATOR_TAGS for c in between)
                if len(markers) == 1 and right is not None and not explicit_between:
                    raw = markers[0]
                    kind = marker_kind(raw)
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
                                f"markers={markers!r}, right={lname(right) if right is not None else None}, "
                                f"explicitBetween={explicit_between}"
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
    summary["distinct_unresolved_chunks"] = len(unresolved_chunks)

    payload = {
        "schema": 1,
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
        "unresolvedChunks": dict(unresolved_chunks.most_common()),
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
        "AO:InDirectJoin elements.",
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
        "The extractor only counts an element-tail marker as a binary relation when the",
        "next manuscript child is another entry and no explicit AO join operator occurs",
        "between them. Text-only composites, malformed partial markers and mixed/ambiguous",
        "forms remain explicit in the JSON inventory for manual classification.",
        "",
    ]
    md_path = REPORTS / "joins-textual-research.md"
    md_path.write_text("\n".join(lines), encoding="utf8")
    print(md_path.read_text(encoding="utf8"))
    print(f"machine-readable inventory: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
