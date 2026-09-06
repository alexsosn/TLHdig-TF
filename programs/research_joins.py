#!/usr/bin/env python
"""Corpus-wide research census for AO:Manuscripts join semantics (issue #18).

Research only: this script does not modify source or TF artifacts. It inventories the
ordered manuscript apparatus so a later plan can model joins without guessing that the
empty DirectJoin/InDirectJoin elements contain target identifiers.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig.paths import CORPUS, REPORTS, ROOT

OPERATORS = {"DirectJoin": "direct", "InDirectJoin": "indirect"}
META_JOIN_NAMES = {
    "join", "merge", "merged", "doc", "mDocID", "aufheb", "aufloes",
}
EURO = re.compile(r"€\d+")


def lname(element) -> str:
    tag = element.tag
    if not isinstance(tag, str):
        return ""
    return ET.QName(tag).localname


def text_value(element) -> str:
    return "".join(element.itertext()).strip()


def entry(element) -> dict:
    return {
        "tag": lname(element),
        "nr": (element.get("nr") or "").strip(),
        "text": text_value(element),
        "attrs": dict(sorted(element.attrib.items())),
    }


def identity(item: dict | None) -> str:
    if not item:
        return ""
    return f"{item['tag']}|{item['nr']}|{item['text']}"


def parse(data: bytes, *, recover: bool):
    parser = ET.XMLParser(recover=recover, huge_tree=True, resolve_entities=False)
    return ET.fromstring(data, parser=parser)


def main() -> int:
    files = sorted(CORPUS.rglob("*.xml"))
    summary = Counter()
    child_counts = Counter()
    operator_pairs = Counter()
    operator_positions = Counter()
    operator_texts = Counter()
    operator_attrs = Counter()
    operator_per_block = Counter()
    flat_values = {"direct": Counter(), "indirect": Counter()}
    endpoint_type_pairs = Counter()
    meta_join_events = Counter()
    duplicate_nr_shapes = Counter()
    nr_reference = Counter()
    relation_pair_kinds: dict[tuple[str, str], set[str]] = defaultdict(set)
    directed_relations: set[tuple[str, str, str]] = set()
    relations: list[dict] = []
    strict_failures: list[dict] = []
    anomalies: list[dict] = []

    for path in files:
        rel = path.relative_to(CORPUS).as_posix()
        data = path.read_bytes()
        summary["files"] += 1
        strict = True
        try:
            root = parse(data, recover=False)
        except ET.XMLSyntaxError as exc:
            strict = False
            summary["strict_parse_failures"] += 1
            strict_failures.append({"src_file": rel, "error": str(exc).split("\n", 1)[0]})
            try:
                root = parse(data, recover=True)
            except ET.XMLSyntaxError:
                root = None
        if root is None:
            summary["unrecoverable_for_research"] += 1
            continue

        docids = root.xpath("//*[local-name()='AOHeader']/*[local-name()='docID']/text()")
        docid = str(docids[0]).strip() if docids else Path(rel).stem
        for node in root.xpath("//*[local-name()='AOHeader']/*[local-name()='meta']//*"):
            name = lname(node)
            if name in META_JOIN_NAMES:
                meta_join_events[name] += 1

        used_sigla = set()
        for lb in root.xpath("//*[local-name()='lb']"):
            used_sigla.update(EURO.findall(lb.get("lnr") or ""))

        blocks = root.xpath("//*[local-name()='Manuscripts']")
        summary["blocks"] += len(blocks)
        if blocks:
            summary["files_with_blocks"] += 1
        for block_index, block in enumerate(blocks):
            children = [c for c in block if isinstance(c.tag, str)]
            for child in children:
                child_counts[lname(child)] += 1

            entries = [(i, entry(child)) for i, child in enumerate(children) if lname(child) not in OPERATORS]
            nr_groups: dict[str, list[dict]] = defaultdict(list)
            for _, item in entries:
                nr = item["nr"]
                if nr:
                    nr_groups[nr].append(item)
                    nr_reference["entry_nr_total"] += 1
                    if nr in used_sigla:
                        nr_reference["entry_nr_used_on_lines"] += 1
                    else:
                        nr_reference["entry_nr_not_used_on_lines"] += 1
                else:
                    nr_reference["entry_nr_missing"] += 1
            for nr, items in nr_groups.items():
                if len(items) > 1:
                    shape = "+".join(sorted(x["tag"] for x in items))
                    duplicate_nr_shapes[shape] += 1

            direct_texts: list[str] = []
            indirect_texts: list[str] = []
            nops = 0
            for i, child in enumerate(children):
                name = lname(child)
                if name not in OPERATORS:
                    continue
                kind = OPERATORS[name]
                nops += 1
                summary[f"{kind}_operators"] += 1
                txt = text_value(child)
                attrs = dict(sorted(child.attrib.items()))
                operator_texts[f"{kind}:{txt!r}"] += 1
                operator_attrs[f"{kind}:{json.dumps(attrs, sort_keys=True, ensure_ascii=False)}"] += 1
                if txt:
                    summary["operators_with_nonempty_text"] += 1
                if attrs:
                    summary["operators_with_attributes"] += 1
                (direct_texts if kind == "direct" else indirect_texts).append(txt)

                left_el = children[i - 1] if i > 0 else None
                right_el = children[i + 1] if i + 1 < len(children) else None
                left_name = lname(left_el) if left_el is not None else ""
                right_name = lname(right_el) if right_el is not None else ""
                left_op = left_name in OPERATORS
                right_op = right_name in OPERATORS
                left = None if left_el is None or left_op else entry(left_el)
                right = None if right_el is None or right_op else entry(right_el)

                if left_el is None:
                    position = "leading"
                elif right_el is None:
                    position = "trailing"
                elif left_op or right_op:
                    position = "consecutive-operator"
                else:
                    position = "between-entries"
                operator_positions[f"{kind}:{position}"] += 1
                operator_pairs[f"{kind}:{left_name or '<START>'}->{right_name or '<END>'}"] += 1

                row = {
                    "src_file": rel,
                    "docid": docid,
                    "strict_parse": strict,
                    "block": block_index,
                    "ordinal": i,
                    "kind": kind,
                    "position": position,
                    "operator_text": txt,
                    "operator_attrs": attrs,
                    "left": left,
                    "right": right,
                    "left_line_referenced": bool(left and left["nr"] and left["nr"] in used_sigla),
                    "right_line_referenced": bool(right and right["nr"] and right["nr"] in used_sigla),
                    "current_fragment_resolvable": bool(
                        left and right and left["tag"] == "TxtPubl" and right["tag"] == "TxtPubl"
                    ),
                }
                relations.append(row)

                if position != "between-entries":
                    anomalies.append(row)
                if left and right:
                    endpoint_type_pairs[f"{kind}:{left['tag']}->{right['tag']}"] += 1
                    li, ri = identity(left), identity(right)
                    if li == ri:
                        summary["self_relations_by_identity"] += 1
                    directed_relations.add((kind, li, ri))
                    relation_pair_kinds[tuple(sorted((li, ri)))].add(kind)
                    if row["current_fragment_resolvable"]:
                        summary["relations_resolvable_to_current_fragment_nodes"] += 1
                    else:
                        summary["relations_not_resolvable_to_two_current_fragment_nodes"] += 1
                else:
                    summary["relations_missing_endpoint"] += 1

            operator_per_block[str(nops)] += 1
            if direct_texts:
                flat_values["direct"][" | ".join(direct_texts)] += 1
            if indirect_texts:
                flat_values["indirect"][" | ".join(indirect_texts)] += 1

    summary["operators_total"] = summary["direct_operators"] + summary["indirect_operators"]
    summary["relations_in_recovered_strict_failures"] = sum(not row["strict_parse"] for row in relations)
    reciprocal = 0
    for kind, left, right in directed_relations:
        if left != right and (kind, right, left) in directed_relations:
            reciprocal += 1
    summary["oriented_relations_with_explicit_reverse_elsewhere"] = reciprocal
    summary["unordered_pairs_with_both_direct_and_indirect"] = sum(
        len(kinds) > 1 for kinds in relation_pair_kinds.values()
    )

    payload = {
        "schema": 1,
        "issue": 18,
        "corpus": str(CORPUS.relative_to(ROOT)),
        "summary": dict(sorted(summary.items())),
        "childCounts": dict(child_counts.most_common()),
        "operatorPositions": dict(sorted(operator_positions.items())),
        "operatorNeighborPairs": dict(operator_pairs.most_common()),
        "endpointTypePairs": dict(endpoint_type_pairs.most_common()),
        "operatorTexts": dict(operator_texts.most_common()),
        "operatorAttributes": dict(operator_attrs.most_common()),
        "operatorsPerBlock": dict(sorted(operator_per_block.items(), key=lambda kv: int(kv[0]))),
        "currentFlattenedValues": {
            kind: dict(values.most_common()) for kind, values in flat_values.items()
        },
        "entryNrCoverage": dict(sorted(nr_reference.items())),
        "duplicateNrShapes": dict(duplicate_nr_shapes.most_common()),
        "metaJoinEventCounts": dict(meta_join_events.most_common()),
        "strictParseFailures": strict_failures,
        "adjacencyAnomalies": anomalies,
        "relations": relations,
    }
    REPORTS.mkdir(exist_ok=True)
    json_path = REPORTS / "joins-research.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf8",
    )

    def rows(counter: Counter, limit: int | None = None):
        items = counter.most_common(limit)
        return [f"| `{key}` | {value:,} |" for key, value in items]

    md = [
        "# Manuscript join research census",
        "",
        "Generated by `programs/research_joins.py` for issue #18. This is a source",
        "inventory only; it does not assert graph direction, symmetry or transitivity.",
        "",
        "## Corpus summary",
        "",
        "| metric | count |",
        "|---|---:|",
    ]
    for key in (
        "files", "strict_parse_failures", "unrecoverable_for_research", "blocks",
        "direct_operators", "indirect_operators", "operators_total",
        "operators_with_nonempty_text", "operators_with_attributes",
        "relations_missing_endpoint", "relations_resolvable_to_current_fragment_nodes",
        "relations_not_resolvable_to_two_current_fragment_nodes",
        "relations_in_recovered_strict_failures", "self_relations_by_identity",
        "oriented_relations_with_explicit_reverse_elsewhere",
        "unordered_pairs_with_both_direct_and_indirect",
    ):
        md.append(f"| `{key}` | {summary[key]:,} |")
    md += [
        "",
        "## Manuscripts child elements",
        "",
        "| child | count |",
        "|---|---:|",
        *rows(child_counts),
        "",
        "## Join operator positions",
        "",
        "| kind/position | count |",
        "|---|---:|",
        *rows(operator_positions),
        "",
        "## Adjacent endpoint types",
        "",
        "| relation | count |",
        "|---|---:|",
        *rows(endpoint_type_pairs),
        "",
        "## Most common raw neighbour pairs",
        "",
        "| relation | count |",
        "|---|---:|",
        *rows(operator_pairs, 20),
        "",
        "## Fragment siglum coverage",
        "",
        "| metric | count |",
        "|---|---:|",
    ]
    for key, value in sorted(nr_reference.items()):
        md.append(f"| `{key}` | {value:,} |")
    md += [
        "",
        "## Duplicate `@nr` shapes within one manuscript block",
        "",
        "| shape | blocks |",
        "|---|---:|",
        *rows(duplicate_nr_shapes),
        "",
        "## Separate AOHeader edit-history join/merge events",
        "",
        "These are measured separately from the ordered `AO:Manuscripts` operators and",
        "must not be conflated with the structural witness relation without further evidence.",
        "",
        "| event | count |",
        "|---|---:|",
        *rows(meta_join_events),
        "",
        "## Current flattened feature values",
        "",
        "The current converter appends the text content of each join operator and joins",
        "those strings with ` | `. Empty self-closing operators therefore collapse to",
        "blank/separator-only document features; these counts quantify that information loss.",
        "",
    ]
    for kind in ("direct", "indirect"):
        md += [f"### {kind}", "", "| value | documents |", "|---|---:|"]
        for value, count in flat_values[kind].most_common(20):
            md.append(f"| `{value!r}` | {count:,} |")
        md.append("")
    md += [
        "## Anomalies requiring manual review",
        "",
        f"Non-between-entry operators: **{len(anomalies):,}**. Full records are in",
        "`reports/joins-research.json`.",
        "",
        "## Interpretation boundary",
        "",
        "This census deliberately treats `DirectJoin` and `InDirectJoin` as ordered",
        "operators and records their immediate neighbours. Whether the resulting relation",
        "is directed, symmetric, transitive, or whether repeated `@nr` entries are aliases",
        "must be established in the research/plan before production edge creation.",
        "",
    ]
    md_path = REPORTS / "joins-research.md"
    md_path.write_text("\n".join(md), encoding="utf8")

    print(md_path.read_text(encoding="utf8"))
    print(f"machine-readable inventory: {json_path} ({len(relations):,} operator records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
