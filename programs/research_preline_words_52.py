#!/usr/bin/env python
"""Research-only inventory of top-level words before the first line boundary.

This script deliberately does not change converter behavior. It inventories the repaired
production source, reconciles source-token counts against the currently shipped TF graph,
and writes a detailed report used to freeze issue #52's design.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import html
import sys
from xml.parsers import expat

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import repair, signs, source, sourcepath
from tlhdig.paths import ENCRYPTED, PATCHES, ROOT, corpus_files, rel

TF_BASELINE = "0.3.0"
REPORT = ROOT / "reports" / "research-preline-52.md"
EXPECTED_PRELINE_WORDS = 36
EXPECTED_PRELINE_READABLE_SIGNS = 22


def lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else ""


def short(value: str | None, limit: int = 100) -> str:
    if not value:
        return ""
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def span_pairing(data: bytes, text, spans):
    text_span = next(
        (sp for sp in spans if sp.tag == "text" and sp.inner_start is not None), None
    )
    all_word_spans = [sp for sp in spans if sp.tag == "w"]
    if text_span is not None:
        all_word_spans = [
            sp
            for sp in all_word_spans
            if text_span.inner_start <= sp.outer_start < text_span.inner_end
        ]
    word_spans = []
    for sp in all_word_spans:
        if any(
            other is not sp
            and other.outer_start <= sp.outer_start
            and sp.outer_end <= other.outer_end
            for other in all_word_spans
        ):
            continue
        word_spans.append(sp)

    top_words = [
        node
        for node in text.iter()
        if lname(node) == "w"
        and not any(lname(ancestor) == "w" for ancestor in node.iterancestors())
    ]
    if len(top_words) != len(word_spans):
        raise ValueError(f"top-level word/span pairing {len(top_words)} != {len(word_spans)}")
    return {id(node): sp for node, sp in zip(top_words, word_spans)}, top_words


def source_inventory():
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}
    rows = []
    stats = Counter()
    parent_counts = Counter()
    ancestor_counts = Counter()
    readable_parent_counts = Counter()
    all_source_signs = 0
    postline_source_signs = 0

    for path in corpus_files():
        src_file = rel(path)
        stats["files"] += 1
        if src_file == ENCRYPTED:
            stats["encrypted"] += 1
            continue
        parsed_path = sourcepath.parse(src_file)
        if not parsed_path.parse_ok or not parsed_path.project:
            stats["bad_source_path"] += 1
            continue
        data = path.read_bytes()
        patch = patches.get(src_file)
        if patch:
            try:
                data = repair.apply(data, patch[1], expect_sha=patch[0])
            except repair.PatchError:
                stats["repair_failure"] += 1
                continue
        try:
            spans = source.scan(data)
            root = ET.fromstring(data)
        except (expat.ExpatError, ET.XMLSyntaxError, ValueError):
            stats["unparseable"] += 1
            continue
        div1 = root.find("body/div1")
        text = div1.find("text") if div1 is not None else None
        if text is None:
            stats["no_text"] += 1
            continue
        stats["documents"] += 1

        try:
            span_for, top_words = span_pairing(data, text, spans)
        except ValueError as exc:
            rows.append({"src_file": src_file, "error": str(exc)})
            stats["pairing_failure"] += 1
            continue

        first_lb = next((n for n in text.iter() if lname(n) == "lb"), None)
        first_lb_seen = False
        preline_index = 0
        tree = root.getroottree()

        for node in text.iter():
            if not isinstance(node.tag, str):
                continue
            tag = lname(node)
            if tag == "lb":
                first_lb_seen = True
                continue
            if tag != "w" or id(node) not in span_for:
                continue

            sp = span_for[id(node)]
            inner = source.inner_bytes(data, sp)
            toks = signs.tokenise_word(inner)
            readable = [t for t in toks if t.type != "empty"]
            all_source_signs += len(readable)
            if first_lb_seen:
                postline_source_signs += len(readable)
                continue

            preline_index += 1
            stats["preline_words"] += 1
            stats["preline_readable_signs"] += len(readable)
            if readable:
                stats["preline_readable_words"] += 1
            else:
                stats["preline_nonreadable_words"] += 1

            markers = [name for t in toks for name, _off in t.markers]
            note_attrs = [attrs for t in toks for attrs in t.note_attrs]
            if markers:
                stats["preline_words_with_markers"] += 1
            if note_attrs:
                stats["preline_words_with_notes"] += 1
            if not readable and markers:
                stats["marker_only_words"] += 1
            if not readable and note_attrs:
                stats["note_only_words"] += 1

            ancestors = [lname(a) for a in node.iterancestors() if lname(a)]
            parent = lname(node.getparent()) if node.getparent() is not None else ""
            parent_counts[parent] += 1
            if readable:
                readable_parent_counts[parent] += 1
            ancestor_counts.update(ancestors)

            prev = node.getprevious()
            nxt = node.getnext()
            child_tags = [lname(c) for c in node if lname(c)]
            raw = data[sp.outer_start : sp.outer_end].decode("utf8", errors="replace")
            first_lb_desc = ""
            if first_lb is not None:
                first_lb_desc = ", ".join(
                    f"{k}={v!r}" for k, v in first_lb.attrib.items()
                )

            rows.append(
                {
                    "src_file": src_file,
                    "index": preline_index,
                    "path": tree.getpath(node),
                    "span": f"{sp.outer_start}:{sp.outer_end}",
                    "parent": parent,
                    "ancestors": "/".join(reversed(ancestors)),
                    "prev": lname(prev) if prev is not None else "",
                    "next": lname(nxt) if nxt is not None else "",
                    "children": ",".join(child_tags),
                    "attrs": dict(node.attrib),
                    "readable": len(readable),
                    "symbols": [t.sym for t in readable],
                    "types": [t.type for t in readable],
                    "markers": markers,
                    "notes": len(note_attrs),
                    "raw": short(raw, 180),
                    "has_lb": first_lb is not None,
                    "first_lb": first_lb_desc,
                }
            )

        if preline_index:
            stats["documents_with_preline_words"] += 1
            if first_lb is None:
                stats["preline_documents_without_lb"] += 1

    stats["all_source_signs"] = all_source_signs
    stats["postline_source_signs"] = postline_source_signs
    return rows, stats, parent_counts, readable_parent_counts, ancestor_counts


def graph_inventory():
    from tf.fabric import Fabric

    tf_dir = ROOT / "tf" / TF_BASELINE
    TF = Fabric(locations=str(tf_dir), silent="deep")
    api = TF.load("otype anchor", silent="deep")
    if api is False or api is None:
        raise RuntimeError(f"cannot load tf/{TF_BASELINE}")
    F = api.F
    graph = Counter()
    for sign in F.otype.s("sign"):
        if F.anchor.v(sign):
            graph["anchors"] += 1
        else:
            graph["non_anchor_signs"] += 1
    return graph


def write_report(rows, stats, parents, readable_parents, ancestors, graph):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    problems = []
    if stats["preline_words"] != EXPECTED_PRELINE_WORDS:
        problems.append(
            f"pre-line words {stats['preline_words']} != prior measurement {EXPECTED_PRELINE_WORDS}"
        )
    if stats["preline_readable_signs"] != EXPECTED_PRELINE_READABLE_SIGNS:
        problems.append(
            "pre-line readable signs "
            f"{stats['preline_readable_signs']} != prior measurement {EXPECTED_PRELINE_READABLE_SIGNS}"
        )
    source_minus_tf = stats["all_source_signs"] - graph["non_anchor_signs"]
    if source_minus_tf != stats["preline_readable_signs"]:
        problems.append(
            "all readable source signs minus TF non-anchor signs "
            f"{source_minus_tf} != pre-line readable signs {stats['preline_readable_signs']}"
        )

    lines = [
        "# Research: readable words before the first line boundary",
        "",
        "Research-only production inventory for issue #52. No converter behavior is changed.",
        "",
        "## Population reconciliation",
        "",
        f"- production-eligible source documents: **{stats['documents']:,}**",
        f"- documents containing pre-line top-level words: **{stats['documents_with_preline_words']:,}**",
        f"- pre-line top-level words: **{stats['preline_words']:,}**",
        f"- pre-line words with readable signs: **{stats['preline_readable_words']:,}**",
        f"- pre-line words without readable signs: **{stats['preline_nonreadable_words']:,}**",
        f"- readable pre-line signs: **{stats['preline_readable_signs']:,}**",
        f"- all readable top-level source signs: **{stats['all_source_signs']:,}**",
        f"- currently represented non-anchor TF {TF_BASELINE} signs: **{graph['non_anchor_signs']:,}**",
        f"- exact source-minus-TF delta: **{stats['all_source_signs'] - graph['non_anchor_signs']:,}**",
        f"- current technical anchor signs: **{graph['anchors']:,}**",
        f"- pre-line words carrying damage markers: **{stats['preline_words_with_markers']:,}**",
        f"- pre-line words carrying notes: **{stats['preline_words_with_notes']:,}**",
        f"- pre-line documents with no `<lb>` anywhere: **{stats['preline_documents_without_lb']:,}**",
        "",
        "## Structural owners",
        "",
        "| parent | all pre-line words | readable pre-line words |",
        "| --- | ---: | ---: |",
    ]
    for parent, count in parents.most_common():
        lines.append(f"| `{parent or '(none)'}` | {count:,} | {readable_parents[parent]:,} |")
    lines.extend([
        "",
        "Most common ancestor tags: "
        + ", ".join(f"`{tag}` {count:,}" for tag, count in ancestors.most_common(12)),
        "",
        "## Complete pre-line inventory",
        "",
        "| source | XML path | bytes | parent | readable | symbols | markers | notes | first line | source word |",
        "| --- | --- | ---: | --- | ---: | --- | --- | ---: | --- | --- |",
    ])
    for row in rows:
        if "error" in row:
            lines.append(
                f"| `{row['src_file']}` | ERROR |  |  |  |  |  |  |  | `{row['error']}` |"
            )
            continue
        symbols = " ".join(row["symbols"]) or "—"
        markers = " ".join(row["markers"]) or "—"
        first_line = row["first_lb"] if row["has_lb"] else "NO LB"
        raw = html.escape(row["raw"]).replace("|", "\\|")
        lines.append(
            f"| `{row['src_file']}` | `{row['path']}` | `{row['span']}` | `{row['parent']}` | "
            f"{row['readable']} | `{symbols}` | `{markers}` | {row['notes']} | "
            f"`{short(first_line, 80)}` | `{raw}` |"
        )

    lines.extend(["", "## Research gate result", ""])
    if problems:
        lines.append("**FAIL** — population assumptions do not reconcile:")
        lines.extend(f"- {p}" for p in problems)
    else:
        lines.append(
            "**PASS** — the previously measured 36 pre-line words / 22 readable signs "
            "reconcile exactly with the shipped non-anchor sign deficit."
        )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf8")
    return problems


def main() -> int:
    rows, stats, parents, readable_parents, ancestors = source_inventory()
    graph = graph_inventory()
    problems = write_report(rows, stats, parents, readable_parents, ancestors, graph)
    print(REPORT.read_text(encoding="utf8"))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
