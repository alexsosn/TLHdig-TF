#!/usr/bin/env python
"""Independently verify manuscript apparatus source evidence against the shipped TF graph.

The production emitter is deliberately not imported.  The source side reparses the same
repaired, strict XML population accepted by the converter; the graph side reconstructs
fragment occurrences, authoritative join-statement ledgers, witnesses and convenience
``joined`` edges from Text-Fabric features.  Pure comparison rules live in
``tlhdig.manuscript_conservation`` so invented reverse/transitive/cross-block edges cannot
be blessed by reusing emitter code.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import sys
from xml.parsers import expat

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, lineref, manuscripts, repair, source, sourcepath
from tlhdig.manuscript_conservation import (
    FragmentRow,
    StatementRow,
    validate_edge_types,
    validate_fragment_ownership,
    validate_fragments,
    validate_joined,
    validate_ledger,
    validate_witnesses,
)
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, REPORTS, ROOT, corpus_files, rel

NEEDED = " ".join(
    (
        "otype oslots src_file srcln manuscript_block",
        "fragment_order fragment_kind fragment_label frag frag_raw",
        "siglum_source siglum_ambiguous siglum_candidates siglum_raw_candidates",
        "join_order join_kind join_encoding join_raw join_resolved",
        "witness witness_resolution joinLeft joinRight joinDocument joined",
    )
)


def _lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else ""


def _normalise_siglum(raw: str | None) -> str:
    """Independent lookup normalisation measured for the source siglum grammar."""
    value = " ".join((raw or "").split())
    if value.startswith("€"):
        return "€" + "".join(value[1:].split())
    return value


def _line_parts(raw_lnr: str | None) -> tuple[str, ...]:
    ref = lineref.parse(raw_lnr)
    if not ref.frag:
        return ()
    return tuple(_normalise_siglum(part) for part in ref.frags if _normalise_siglum(part))


def _split_feature(value) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in str(value).split(" | ") if part.strip())


def _value(feature, node, default=""):
    value = feature.v(node)
    return default if value is None else value


def _edge_targets(E, name: str, node) -> tuple:
    feature = getattr(E, name, None)
    if feature is None:
        return ()
    return tuple(feature.f(node))


def _edge_values(E, name: str, node) -> dict:
    feature = getattr(E, name, None)
    if feature is None:
        return {}
    return dict(feature.f(node))


def _source_documents() -> tuple[dict[str, dict], Counter, list[str]]:
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}
    expected: dict[str, dict] = {}
    stats = Counter()
    problems: list[str] = []

    for path in corpus_files():
        src_file = rel(path)
        stats["source_files"] += 1
        if src_file == ENCRYPTED:
            stats["source_excluded_encrypted"] += 1
            continue

        parsed_path = sourcepath.parse(src_file)
        if not parsed_path.parse_ok or not parsed_path.project:
            problems.append(
                f"{src_file}: source path rejected by production grammar: "
                f"{parsed_path.parse_error or 'missing_project'}"
            )
            continue

        data = path.read_bytes()
        patch_entry = patches.get(src_file)
        if patch_entry:
            try:
                data = repair.apply(data, patch_entry[1], expect_sha=patch_entry[0])
            except repair.PatchError as exc:
                problems.append(f"{src_file}: repair manifest failed: {exc}")
                continue

        try:
            # Production requires both the byte scanner and strict XML parser to accept
            # the repaired stream.  A recovery parser here would compare a population
            # the converter intentionally excludes.
            source.scan(data)
            root = ET.fromstring(data)
        except (expat.ExpatError, ET.XMLSyntaxError, ValueError):
            stats["source_excluded_unparseable"] += 1
            continue

        div1 = root.find("body/div1")
        text = div1.find("text") if div1 is not None else None
        if text is None:
            stats["source_excluded_no_text"] += 1
            continue

        document = manuscripts.parse_document(div1)
        fragments: list[FragmentRow] = []
        statements: list[StatementRow] = []
        witnesses: set[tuple[int, int, int, str]] = set()
        by_siglum: dict[tuple[int, str], list[int]] = defaultdict(list)

        for block in document.blocks:
            stats["source_blocks"] += 1
            apparatus = block.apparatus
            for entry in apparatus.entries:
                ambiguous = bool(
                    entry.siglum and entry.siglum in apparatus.duplicate_sigla
                )
                fragments.append(
                    FragmentRow(
                        block=block.order,
                        order=entry.order,
                        kind=entry.kind,
                        label=entry.label,
                        siglum=entry.siglum,
                        siglum_source=entry.siglum_source,
                        siglum_raw=entry.siglum_raw,
                        siglum_candidates=tuple(entry.siglum_candidates),
                        siglum_raw_candidates=tuple(entry.siglum_raw_candidates),
                        ambiguous=ambiguous,
                    )
                )
                if entry.siglum:
                    by_siglum[(block.order, entry.siglum)].append(entry.order)

            for statement in apparatus.statements:
                statements.append(
                    StatementRow(
                        block=block.order,
                        order=statement.order,
                        kind=statement.kind,
                        encoding=statement.encoding,
                        raw=statement.raw,
                        resolved=statement.resolved,
                        left=statement.left,
                        right=statement.right,
                    )
                )

        # Converter line order is text-local and one-based (`srcln`).  Apparatus scope,
        # however, is document-order under div1, so use parse_document's exact element
        # identities to join the two views without guessing from position strings.
        scope = {id(line.element): line.block for line in document.lines}
        line_order = 0
        for node in text.iter():
            if _lname(node) != "lb":
                continue
            line_order += 1
            block_order = scope.get(id(node))
            if block_order is None:
                continue
            for part in _line_parts(node.get("lnr")):
                targets = by_siglum.get((block_order, part), ())
                if not targets:
                    continue
                resolution = "unique" if len(targets) == 1 else "ambiguous"
                for fragment_order in targets:
                    witnesses.add((line_order, block_order, fragment_order, resolution))

        expected[src_file] = {
            "fragments": tuple(fragments),
            "statements": tuple(statements),
            "witnesses": tuple(sorted(witnesses)),
        }
        stats["source_documents"] += 1
        stats["source_fragments"] += len(fragments)
        stats["source_statements"] += len(statements)
        stats["source_witness_rows"] += len(witnesses)

    return expected, stats, problems


def _graph_documents(expected: dict[str, dict]):
    from tf.fabric import Fabric

    TF = Fabric(locations=str(ROOT / "tf" / TF_VERSION), silent="deep")
    api = TF.load(NEEDED, silent="deep")
    if api is False or api is None:
        return None, Counter(), [f"tf/{TF_VERSION}: manuscript feature set does not load"]

    F, L, E = api.F, api.L, api.E
    stats = Counter()
    problems: list[str] = []

    docs_by_rel: dict[str, int] = {}
    for doc in F.otype.s("document"):
        src_file = F.src_file.v(doc)
        if not src_file:
            problems.append(f"graph document {doc}: missing src_file")
            continue
        if src_file in docs_by_rel:
            problems.append(
                f"graph src_file {src_file!r}: duplicate document nodes "
                f"{docs_by_rel[src_file]} and {doc}"
            )
            continue
        docs_by_rel[src_file] = doc
    stats["graph_documents"] = len(docs_by_rel)

    source_keys = set(expected)
    graph_keys = set(docs_by_rel)
    for src_file in sorted(source_keys - graph_keys):
        problems.append(f"{src_file}: source document missing from graph")
    for src_file in sorted(graph_keys - source_keys):
        problems.append(f"{src_file}: graph document has no production-eligible source")

    # Global integrity must be checked before document-local comparison. Otherwise an
    # orphan fragment, or an edge whose source/target has the wrong node type, can sit
    # outside every expected document traversal and escape the conservation ledger.
    ownership = [
        (node, len(tuple(L.u(node, otype="document"))))
        for node in F.otype.s("fragment")
    ]
    problems.extend(validate_fragment_ownership(ownership))

    edge_rows: list[tuple[str, str, str]] = []
    for edge_name in (
        "joinDocument", "joinLeft", "joinRight", "joined", "witness", "witness_resolution"
    ):
        feature = getattr(E, edge_name, None)
        if feature is None:
            continue
        for (source_node, target_node), _value in feature.items():
            edge_rows.append(
                (edge_name, str(F.otype.v(source_node)), str(F.otype.v(target_node)))
            )
    problems.extend(validate_edge_types(edge_rows))
    stats["graph_fragment_ownership_checked"] = len(ownership)
    stats["graph_manuscript_edges_type_checked"] = len(edge_rows)

    # Authoritative statement ownership comes from joinDocument, not slot containment.
    statements_by_doc: dict[int, list[int]] = defaultdict(list)
    for node in F.otype.s("joinstmt"):
        targets = _edge_targets(E, "joinDocument", node)
        if len(targets) != 1:
            problems.append(
                f"joinstmt {node}: expected exactly one joinDocument edge, got {targets!r}"
            )
            continue
        statements_by_doc[targets[0]].append(node)

    for src_file in sorted(source_keys & graph_keys):
        doc = docs_by_rel[src_file]
        source_rows = expected[src_file]

        fragment_nodes = tuple(L.d(doc, otype="fragment"))
        fragment_node_set = set(fragment_nodes)
        fragment_rows: list[FragmentRow] = []
        node_identity: dict[int, tuple[int, int]] = {}

        for node in fragment_nodes:
            block = int(_value(F.manuscript_block, node, 0) or 0)
            order = int(_value(F.fragment_order, node, 0) or 0)
            siglum = str(_value(F.frag, node, "") or "")
            raw = str(_value(F.frag_raw, node, "") or "")
            candidates = _split_feature(F.siglum_candidates.v(node)) or ((siglum,) if siglum else ())
            raw_candidates = _split_feature(F.siglum_raw_candidates.v(node)) or ((raw,) if raw else ())
            fragment_rows.append(
                FragmentRow(
                    block=block,
                    order=order,
                    kind=str(_value(F.fragment_kind, node, "") or ""),
                    label=str(_value(F.fragment_label, node, "") or ""),
                    siglum=siglum,
                    siglum_source=str(_value(F.siglum_source, node, "") or ""),
                    siglum_raw=raw,
                    siglum_candidates=tuple(candidates),
                    siglum_raw_candidates=tuple(raw_candidates),
                    ambiguous=bool(_value(F.siglum_ambiguous, node, 0) or 0),
                )
            )
            node_identity[node] = (block, order)

        local = validate_fragments(source_rows["fragments"], fragment_rows)
        problems.extend(f"{src_file}: {problem}" for problem in local)
        stats["graph_fragments"] += len(fragment_rows)

        graph_statements: list[StatementRow] = []
        for node in statements_by_doc.get(doc, ()):
            block = int(_value(F.manuscript_block, node, 0) or 0)
            left_targets = _edge_targets(E, "joinLeft", node)
            right_targets = _edge_targets(E, "joinRight", node)
            if len(left_targets) > 1:
                problems.append(f"{src_file}: joinstmt {node} has multiple joinLeft targets")
            if len(right_targets) > 1:
                problems.append(f"{src_file}: joinstmt {node} has multiple joinRight targets")

            def endpoint(targets, edge_name):
                if len(targets) != 1:
                    return None
                target = targets[0]
                identity = node_identity.get(target)
                if identity is None:
                    problems.append(
                        f"{src_file}: joinstmt {node} {edge_name} target {target} "
                        "is not a fragment in its document"
                    )
                    return None
                target_block, target_order = identity
                if target_block != block:
                    problems.append(
                        f"{src_file}: joinstmt {node} {edge_name} crosses apparatus blocks "
                        f"{block}->{target_block}"
                    )
                return target_order

            left = endpoint(left_targets, "joinLeft")
            right = endpoint(right_targets, "joinRight")
            resolved = bool(_value(F.join_resolved, node, 0) or 0)
            kind = str(_value(F.join_kind, node, "") or "")
            if resolved and (kind not in {"direct", "indirect"} or left is None or right is None):
                problems.append(
                    f"{src_file}: joinstmt {node} claims resolved without two confident endpoints"
                )
            graph_statements.append(
                StatementRow(
                    block=block,
                    order=int(_value(F.join_order, node, 0) or 0),
                    kind=kind,
                    encoding=str(_value(F.join_encoding, node, "") or ""),
                    raw=str(_value(F.join_raw, node, "") or ""),
                    resolved=resolved,
                    left=left,
                    right=right,
                )
            )

        local = validate_ledger(source_rows["statements"], graph_statements)
        problems.extend(f"{src_file}: {problem}" for problem in local)
        stats["graph_statements"] += len(graph_statements)

        joined_rows: list[tuple[int, int, int, str]] = []
        for left_node in fragment_nodes:
            left_identity = node_identity.get(left_node)
            if left_identity is None:
                continue
            left_block, left_order = left_identity
            for right_node, kind in _edge_values(E, "joined", left_node).items():
                right_identity = node_identity.get(right_node)
                if right_identity is None:
                    problems.append(
                        f"{src_file}: joined edge {left_node}->{right_node} leaves its document"
                    )
                    continue
                right_block, right_order = right_identity
                if right_block != left_block:
                    problems.append(
                        f"{src_file}: joined edge crosses apparatus blocks "
                        f"{left_block}->{right_block}"
                    )
                joined_rows.append((left_block, left_order, right_order, str(kind)))
        local = validate_joined(source_rows["statements"], joined_rows)
        problems.extend(f"{src_file}: {problem}" for problem in local)
        stats["graph_joined_edges"] += len(joined_rows)

        graph_witnesses: list[tuple[int, int, int, str]] = []
        for line in L.d(doc, otype="line"):
            plain = set(_edge_targets(E, "witness", line))
            valued = _edge_values(E, "witness_resolution", line)
            if plain != set(valued):
                problems.append(
                    f"{src_file}: line {line} witness and witness_resolution target sets differ"
                )
            if not plain and not valued:
                continue
            line_order = int(_value(F.srcln, line, 0) or 0)
            line_block = int(_value(F.manuscript_block, line, 0) or 0)
            for target, resolution in valued.items():
                identity = node_identity.get(target)
                if identity is None:
                    problems.append(
                        f"{src_file}: line {line} witness target {target} is not a fragment in document"
                    )
                    continue
                fragment_block, fragment_order = identity
                if fragment_block != line_block:
                    problems.append(
                        f"{src_file}: line {line} witness crosses apparatus blocks "
                        f"{line_block}->{fragment_block}"
                    )
                graph_witnesses.append(
                    (line_order, line_block, fragment_order, str(resolution))
                )
        local = validate_witnesses(source_rows["witnesses"], graph_witnesses)
        problems.extend(f"{src_file}: {problem}" for problem in local)
        stats["graph_witness_rows"] += len(graph_witnesses)

    return api, stats, problems


def main() -> int:
    expected, source_stats, source_problems = _source_documents()
    api, graph_stats, graph_problems = _graph_documents(expected)
    problems = [*source_problems, *graph_problems]
    stats = source_stats + graph_stats

    lines = [
        "# Manuscript apparatus source-to-graph conservation",
        "",
        "Generated by `programs/check_manuscript_joins.py`. The source side applies the",
        "pinned repair manifest, then requires the same strict scanner/XML eligibility as",
        "the production converter. The graph side is reconstructed from the shipped TF",
        "artifact without importing the production manuscript graph emitter.",
        "",
        "| check | count |",
        "|---|---:|",
        f"| production-eligible source documents | {stats['source_documents']:,} |",
        f"| source apparatus blocks | {stats['source_blocks']:,} |",
        f"| source fragment occurrences | {stats['source_fragments']:,} |",
        f"| graph fragment occurrences | {stats['graph_fragments']:,} |",
        f"| source join statements | {stats['source_statements']:,} |",
        f"| graph join statements | {stats['graph_statements']:,} |",
        f"| source witness rows | {stats['source_witness_rows']:,} |",
        f"| graph witness rows | {stats['graph_witness_rows']:,} |",
        f"| graph convenience `joined` edges | {stats['graph_joined_edges']:,} |",
        f"| problems | {len(problems):,} |",
        "",
        "The `joined` check accepts only direct source-backed block-local boundaries; it",
        "rejects inferred reverse/transitive edges and suppresses direct/indirect conflicts.",
        "Authoritative statement multiplicity remains on `joinstmt` nodes.",
        "",
    ]
    if problems:
        lines.extend(("## Problems", ""))
        lines.extend(f"- {problem}" for problem in problems[:500])
        if len(problems) > 500:
            lines.append(f"- … {len(problems) - 500:,} additional problems omitted")
        lines.append("")

    REPORTS.mkdir(exist_ok=True)
    report = REPORTS / "manuscript-joins.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf8")
    print("\n".join(lines[:24]))
    if api is None or problems:
        print(f"MANUSCRIPT JOIN CONSERVATION FAILED -> {report}")
        return 1
    print("manuscript apparatus source evidence is conserved in the shipped graph")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
