#!/usr/bin/env python
"""Measure manuscript-join semantics at the converter input boundary (issue #18).

This is a research-only program. It follows the converter's repaired/strict XML input
path, inventories every DirectJoin/InDirectJoin marker in AO:Manuscripts, and records
the neighbouring manuscript entries without assigning graph semantics to their order.

Use ``--write`` to materialize both the machine-readable and human-readable research
artifacts under reports/ and docs/.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from xml.parsers import expat

import lxml.etree as LE

PROGRAMS = Path(__file__).resolve().parent
ROOT = PROGRAMS.parent
sys.path.insert(0, str(PROGRAMS))

from tlhdig import repair, source
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, REPORTS, corpus_files, rel as rel_key

AO = "{http://hethiter.net/ns/AO/1.0}"
JOIN_TAGS = {"DirectJoin": "direct", "InDirectJoin": "indirect"}
ENTRY_TAGS = frozenset({"TxtPubl", "InvNr"})


def local_name(tag) -> str:
    if not isinstance(tag, str):
        return ""
    return LE.QName(tag).localname


def text(element) -> str:
    return "".join(element.itertext())


def public_element(element) -> dict:
    return {
        "tag": local_name(element.tag),
        "nr": (element.get("nr") or "").strip(),
        "text": text(element).strip(),
        "attrs": dict(sorted(element.attrib.items())),
        "children": [local_name(child.tag) for child in element if isinstance(child.tag, str)],
    }


def endpoint(element) -> dict | None:
    if element is None:
        return None
    row = public_element(element)
    return row if row["tag"] in ENTRY_TAGS else None


def nearest_entry(children, at: int, step: int) -> tuple[int | None, dict | None]:
    i = at + step
    while 0 <= i < len(children):
        row = endpoint(children[i])
        if row is not None:
            return i, row
        i += step
    return None, None


def source_population():
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    counts = Counter()
    statements: list[dict] = []
    document_rows: list[dict] = []

    for path in corpus_files():
        counts["source_xml"] += 1
        rel = rel_key(path, CORPUS)
        if rel == ENCRYPTED:
            counts["encrypted"] += 1
            continue

        data = path.read_bytes()
        patch = patches.get(rel)
        if patch:
            counts["patched_files"] += 1
            try:
                data = repair.apply(data, patch[1], expect_sha=patch[0])
            except repair.PatchError:
                counts["patch_failed"] += 1
                continue
        try:
            source.scan(data)
            root = LE.fromstring(data)
        except (expat.ExpatError, LE.XMLSyntaxError, ValueError):
            counts["unparseable_after_repair"] += 1
            continue
        counts["parseable_after_repair"] += 1

        text_el = root.find("body/div1/text")
        if text_el is None:
            counts["no_text_element"] += 1
            continue
        counts["converter_documents"] += 1

        block = text_el.find(f"{AO}Manuscripts")
        if block is None:
            continue
        counts["manuscript_blocks"] += 1
        children = [child for child in block if isinstance(child.tag, str)]
        docid = (root.findtext("AOHeader/docID") or Path(rel).stem).strip()

        entries = []
        by_nr: dict[str, list[dict]] = defaultdict(list)
        current_fragment_keys = set()
        flattened = {"direct": [], "indirect": []}
        doc_statement_start = len(statements)

        for i, child in enumerate(children):
            name = local_name(child.tag)
            e = endpoint(child)
            if e is not None:
                e = {**e, "index": i}
                entries.append(e)
                if e["nr"]:
                    by_nr[e["nr"]].append(e)
                if name == "TxtPubl":
                    current_fragment_keys.add(e["nr"] or e["text"])
                counts[f"entry_{name}"] += 1
                if not e["nr"]:
                    counts[f"entry_{name}_without_nr"] += 1
                continue

            kind = JOIN_TAGS.get(name)
            if kind is None:
                continue
            counts[f"join_{kind}"] += 1
            raw_text = text(child).strip()
            flattened[kind].append(raw_text)

            prev_immediate = endpoint(children[i - 1]) if i > 0 else None
            next_immediate = endpoint(children[i + 1]) if i + 1 < len(children) else None
            prev_i, prev_nearest = nearest_entry(children, i, -1)
            next_i, next_nearest = nearest_entry(children, i, +1)

            shape = (
                f"{prev_immediate['tag'] if prev_immediate else '-'}>"
                f"{name}>"
                f"{next_immediate['tag'] if next_immediate else '-'}"
            )
            counts[f"shape:{shape}"] += 1
            if prev_immediate is not None and next_immediate is not None:
                counts["join_immediate_two_entries"] += 1
            if prev_nearest is not None and next_nearest is not None:
                counts["join_nearest_two_entries"] += 1
            if raw_text:
                counts["join_nonempty_text"] += 1
            if child.attrib:
                counts["join_with_attrs"] += 1
            if len(child):
                counts["join_with_children"] += 1

            prev_nr = prev_nearest["nr"] if prev_nearest else ""
            next_nr = next_nearest["nr"] if next_nearest else ""
            pair = (prev_nr, next_nr) if prev_nr and next_nr else None
            if pair and pair[0] == pair[1]:
                counts["join_self_same_nr"] += 1

            current_resolved = bool(
                prev_nearest
                and next_nearest
                and (prev_nearest["nr"] or prev_nearest["text"]) in current_fragment_keys
                and (next_nearest["nr"] or next_nearest["text"]) in current_fragment_keys
            )
            # current_fragment_keys is still being accumulated in source order here;
            # recompute after all entries are known below.
            statements.append(
                {
                    "path": rel,
                    "docid": docid,
                    "kind": kind,
                    "marker_tag": name,
                    "marker_index": i,
                    "marker_text": raw_text,
                    "marker_attrs": dict(sorted(child.attrib.items())),
                    "marker_children": [local_name(c.tag) for c in child if isinstance(c.tag, str)],
                    "immediate_previous": prev_immediate,
                    "immediate_next": next_immediate,
                    "nearest_previous_index": prev_i,
                    "nearest_previous": prev_nearest,
                    "nearest_next_index": next_i,
                    "nearest_next": next_nearest,
                    "pair_nr": list(pair) if pair else None,
                    "current_fragment_resolved_provisional": current_resolved,
                }
            )

        # Resolve against exactly what the current converter models: TxtPubl entries.
        for statement in statements[doc_statement_start:]:
            a = statement["nearest_previous"]
            b = statement["nearest_next"]
            a_key = (a["nr"] or a["text"]) if a else ""
            b_key = (b["nr"] or b["text"]) if b else ""
            statement["current_fragment_resolved"] = bool(
                a_key and b_key and a_key in current_fragment_keys and b_key in current_fragment_keys
            )
            statement.pop("current_fragment_resolved_provisional", None)
            if statement["current_fragment_resolved"]:
                counts["join_current_fragment_resolved"] += 1
            if a and b and a["nr"] and b["nr"]:
                # A candidate local resolution based only on explicit source sigla,
                # regardless of whether current TF creates an endpoint for that entry.
                if len(by_nr[a["nr"]]) == 1 and len(by_nr[b["nr"]]) == 1:
                    counts["join_unique_local_nr_resolved"] += 1
                else:
                    counts["join_ambiguous_local_nr"] += 1
            else:
                counts["join_missing_endpoint_nr"] += 1

        document_rows.append(
            {
                "path": rel,
                "docid": docid,
                "entries": entries,
                "duplicate_nr": {
                    nr: rows for nr, rows in sorted(by_nr.items()) if len(rows) > 1
                },
                "current_fragment_keys": sorted(k for k in current_fragment_keys if k),
                "flattened_current": {
                    kind: " | ".join(values) if values else None
                    for kind, values in flattened.items()
                },
                "join_count": len(statements) - doc_statement_start,
            }
        )

    return counts, statements, document_rows


def derived_diagnostics(counts: Counter, statements: list[dict], docs: list[dict]) -> dict:
    pair_occurrences = Counter()
    ordered_by_doc = defaultdict(Counter)
    unresolved_reasons = Counter()
    endpoint_tag_pairs = Counter()
    marker_texts = Counter()
    marker_attrs = Counter()

    for s in statements:
        a = s["nearest_previous"]
        b = s["nearest_next"]
        if a and b:
            endpoint_tag_pairs[f"{a['tag']}->{b['tag']}"] += 1
        pair = s["pair_nr"]
        if pair:
            p = tuple(pair)
            pair_occurrences[(s["path"], s["kind"], p)] += 1
            ordered_by_doc[(s["path"], s["kind"])][p] += 1
        else:
            if a is None:
                unresolved_reasons["no_previous_entry"] += 1
            if b is None:
                unresolved_reasons["no_next_entry"] += 1
            if a is not None and not a["nr"]:
                unresolved_reasons["previous_entry_without_nr"] += 1
            if b is not None and not b["nr"]:
                unresolved_reasons["next_entry_without_nr"] += 1
        marker_texts[s["marker_text"]] += 1
        marker_attrs[json.dumps(s["marker_attrs"], sort_keys=True, ensure_ascii=False)] += 1

    duplicate_statements = sum(n - 1 for n in pair_occurrences.values() if n > 1)
    reciprocal_occurrences = 0
    reciprocal_pairs = set()
    for key, pairs in ordered_by_doc.items():
        for (a, b), n in pairs.items():
            if a == b or (b, a) not in pairs:
                continue
            canonical = tuple(sorted(((a, b), (b, a))))
            if (key, canonical) in reciprocal_pairs:
                continue
            reciprocal_pairs.add((key, canonical))
            reciprocal_occurrences += min(n, pairs[(b, a)]) * 2

    duplicate_nr_docs = [d for d in docs if d["duplicate_nr"]]
    flattened_nonempty = Counter()
    for d in docs:
        for kind, value in d["flattened_current"].items():
            if value is not None:
                flattened_nonempty[(kind, value)] += 1

    return {
        "endpoint_tag_pairs": dict(sorted(endpoint_tag_pairs.items())),
        "unresolved_reasons": dict(sorted(unresolved_reasons.items())),
        "duplicate_pair_statements_beyond_first": duplicate_statements,
        "explicit_reverse_pair_occurrences": reciprocal_occurrences,
        "documents_with_duplicate_nr": len(duplicate_nr_docs),
        "marker_text_values": dict(marker_texts.most_common()),
        "marker_attribute_shapes": {
            key: n for key, n in marker_attrs.most_common()
        },
        "current_flattened_values": [
            {"kind": kind, "value": value, "documents": n}
            for (kind, value), n in flattened_nonempty.most_common()
        ],
        "shape_counts": {
            key.removeprefix("shape:"): value
            for key, value in sorted(counts.items())
            if key.startswith("shape:")
        },
    }


def sample(statements: list[dict], predicate, limit=8) -> list[dict]:
    return [s for s in statements if predicate(s)][:limit]


def markdown(payload: dict) -> str:
    c = payload["counts"]
    d = payload["diagnostics"]
    total = c.get("join_direct", 0) + c.get("join_indirect", 0)

    def pc(n, denominator=total):
        return f"{(100*n/denominator):.1f}%" if denominator else "0.0%"

    lines = [
        "# Research: manuscript join semantics (#18)",
        "",
        "This census follows the converter input boundary: frozen TLHdig 0.3 files, checked",
        "repair manifest, `source.scan()`, strict XML parse, and the same `body/div1/text`",
        "population used by the converter. The machine-readable statement-level evidence is",
        "`reports/manuscript-joins-research.json`.",
        "",
        "No graph semantics are inferred by this report. In particular, XML sibling order is",
        "recorded as evidence but is not treated as relationship direction.",
        "",
        "## Population",
        "",
        "| measure | count |",
        "|---|---:|",
        f"| source XML files | {c.get('source_xml', 0):,} |",
        f"| converter documents | {c.get('converter_documents', 0):,} |",
        f"| AO:Manuscripts blocks | {c.get('manuscript_blocks', 0):,} |",
        f"| AO:TxtPubl entries | {c.get('entry_TxtPubl', 0):,} |",
        f"| AO:InvNr entries | {c.get('entry_InvNr', 0):,} |",
        f"| direct join markers | {c.get('join_direct', 0):,} |",
        f"| indirect join markers | {c.get('join_indirect', 0):,} |",
        f"| **all join markers** | **{total:,}** |",
        "",
        "## Marker payload and adjacency",
        "",
        f"- Markers with non-empty text: **{c.get('join_nonempty_text', 0):,}** / {total:,}.",
        f"- Markers with attributes: **{c.get('join_with_attrs', 0):,}** / {total:,}.",
        f"- Markers with child elements: **{c.get('join_with_children', 0):,}** / {total:,}.",
        f"- Markers immediately between two manuscript entries: **{c.get('join_immediate_two_entries', 0):,}** / {total:,} ({pc(c.get('join_immediate_two_entries', 0))}).",
        f"- Markers with a manuscript entry on both sides after skipping non-entry siblings: **{c.get('join_nearest_two_entries', 0):,}** / {total:,} ({pc(c.get('join_nearest_two_entries', 0))}).",
        "",
        "Immediate sibling shapes:",
        "",
        "| previous > marker > next | count |",
        "|---|---:|",
    ]
    for shape, n in sorted(d["shape_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| `{shape}` | {n:,} |")

    lines += [
        "",
        "Endpoint-entry tag pairs using nearest manuscript entries:",
        "",
        "| previous -> next | count |",
        "|---|---:|",
    ]
    for shape, n in sorted(d["endpoint_tag_pairs"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| `{shape}` | {n:,} |")

    lines += [
        "",
        "## Local sigla and current TF resolvability",
        "",
        f"- Join markers with unique explicit `@nr` on both neighbouring entries: **{c.get('join_unique_local_nr_resolved', 0):,}** / {total:,} ({pc(c.get('join_unique_local_nr_resolved', 0))}).",
        f"- Join markers whose endpoints both resolve to fragment nodes under the **current** converter's `TxtPubl`-only model: **{c.get('join_current_fragment_resolved', 0):,}** / {total:,} ({pc(c.get('join_current_fragment_resolved', 0))}).",
        f"- Join markers missing an endpoint `@nr`: **{c.get('join_missing_endpoint_nr', 0):,}**.",
        f"- Join markers whose local `@nr` is ambiguous because the same siglum labels multiple entries: **{c.get('join_ambiguous_local_nr', 0):,}**.",
        f"- Documents with duplicate manuscript-entry `@nr` values: **{d['documents_with_duplicate_nr']:,}**.",
        "",
        "Unresolved-reason counts are diagnostic dimensions and may overlap:",
        "",
        "| reason | count |",
        "|---|---:|",
    ]
    for reason, n in d["unresolved_reasons"].items():
        lines.append(f"| `{reason}` | {n:,} |")

    lines += [
        "",
        "## Cardinality and ordering diagnostics",
        "",
        f"- Duplicate same-kind, same-ordered-pair statements beyond the first in one document: **{d['duplicate_pair_statements_beyond_first']:,}**.",
        f"- Occurrences participating in an explicitly present reverse ordered pair in the same document/kind: **{d['explicit_reverse_pair_occurrences']:,}**.",
        f"- Same-`@nr` self pairs: **{c.get('join_self_same_nr', 0):,}**.",
        "",
        "These numbers do not establish directionality, symmetry, or transitivity. They only test",
        "whether treating XML order as a directed edge would create duplicate/reverse/self cases.",
        "",
        "## Information lost by the current flattened features",
        "",
        "The current converter appends the marker's own text to `document.directjoin` or",
        "`document.indirectjoin`. The statement-level evidence above records endpoints from XML",
        "position; the flattened string does not. Its observed values are:",
        "",
        "| kind | flattened value | documents |",
        "|---|---|---:|",
    ]
    for row in d["current_flattened_values"][:20]:
        shown = repr(row["value"])
        lines.append(f"| `{row['kind']}` | `{shown}` | {row['documents']:,} |")
    if len(d["current_flattened_values"]) > 20:
        lines.append(f"| … | … | {len(d['current_flattened_values']) - 20} additional distinct values |")

    lines += [
        "",
        "## Evidence examples",
        "",
        "The JSON report contains every statement. These small samples cover the cases that",
        "matter to the design gate.",
        "",
    ]
    for title, key in (
        ("InvNr endpoint", "invnr_endpoint"),
        ("not immediately bounded by entries", "non_immediate"),
        ("missing/ambiguous local resolution", "unresolved"),
        ("marker carrying payload", "payload"),
    ):
        lines += [f"### {title}", ""]
        rows = payload["examples"][key]
        if not rows:
            lines.append("_None observed._")
        for row in rows:
            a = row.get("nearest_previous") or {}
            b = row.get("nearest_next") or {}
            lines.append(
                f"- `{row['path']}` `{row['kind']}`: "
                f"{a.get('tag', '-')}/{a.get('nr', '-')}/{a.get('text', '')!r} -> "
                f"{b.get('tag', '-')}/{b.get('nr', '-')}/{b.get('text', '')!r}; "
                f"marker text={row['marker_text']!r}, attrs={row['marker_attrs']!r}."
            )
        lines.append("")

    lines += [
        "## Research constraints for the design",
        "",
        "1. A join statement must be conserved as a statement even when its endpoints cannot be",
        "   resolved; dropping an empty marker because it has no text would erase the source fact.",
        "2. `TxtPubl`-only fragment modelling is insufficient whenever a join endpoint is an",
        "   `InvNr` entry with its own local siglum. The plan must decide whether such entries",
        "   become fragment nodes or remain explicit unresolved endpoint records.",
        "3. XML order may identify the two adjacent entries, but it is not evidence that the",
        "   relationship is directed. No reciprocal or transitive edge may be synthesized without",
        "   an upstream semantic definition.",
        "4. Direct and indirect markers must remain distinguishable and statement multiplicity",
        "   must not be lost through a valued-edge overwrite.",
        "5. The existing document string features are compatibility/preservation data at best;",
        "   they cannot serve as the normalized relationship because they discard endpoint identity.",
        "",
        "## External documentation search",
        "",
        "Repository-wide and web searches for public AOxml documentation defining",
        "`DirectJoin`/`InDirectJoin` did not locate an authoritative schema/semantic definition.",
        "The implementation plan therefore must be limited to semantics forced by the measured",
        "source structure unless a stronger upstream definition is found before RED.",
        "",
    ]
    return "\n".join(lines)


def build_payload() -> dict:
    counts, statements, docs = source_population()
    diagnostics = derived_diagnostics(counts, statements, docs)
    examples = {
        "invnr_endpoint": sample(
            statements,
            lambda s: any(
                (e or {}).get("tag") == "InvNr"
                for e in (s["nearest_previous"], s["nearest_next"])
            ),
        ),
        "non_immediate": sample(
            statements,
            lambda s: s["immediate_previous"] is None or s["immediate_next"] is None,
        ),
        "unresolved": sample(
            statements,
            lambda s: not s["current_fragment_resolved"]
            or not s["pair_nr"],
        ),
        "payload": sample(
            statements,
            lambda s: bool(s["marker_text"] or s["marker_attrs"] or s["marker_children"]),
        ),
    }
    return {
        "schema": 1,
        "issue": 18,
        "input_contract": "converter repaired/strict XML population",
        "counts": dict(sorted(counts.items())),
        "diagnostics": diagnostics,
        "examples": examples,
        "statements": statements,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write", action="store_true", help="write JSON and Markdown research artifacts")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    payload = build_payload()
    total = payload["counts"].get("join_direct", 0) + payload["counts"].get("join_indirect", 0)
    if args.write:
        REPORTS.mkdir(exist_ok=True)
        (REPORTS / "manuscript-joins-research.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf8",
        )
        (ROOT / "docs" / "research-manuscript-joins.md").write_text(
            markdown(payload) + "\n", encoding="utf8"
        )
    else:
        print(markdown(payload))

    # Research itself is a reproducibility gate. Unexpected patch failure or an empty
    # population makes a checked-in report worse than no report.
    if payload["counts"].get("patch_failed", 0):
        print("research failed: repair manifest could not be applied", file=sys.stderr)
        return 1
    if payload["counts"].get("converter_documents", 0) == 0 or total == 0:
        print("research failed: no converter documents/join statements measured", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
