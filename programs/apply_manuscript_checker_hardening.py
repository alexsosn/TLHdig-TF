#!/usr/bin/env python
from pathlib import Path

path = Path("programs/check_manuscript_joins.py")
text = path.read_text(encoding="utf8")

old_import = '''    FragmentRow,
    StatementRow,
    validate_fragments,
    validate_joined,
    validate_ledger,
    validate_witnesses,
)'''
new_import = '''    FragmentRow,
    StatementRow,
    validate_edge_types,
    validate_fragment_ownership,
    validate_fragments,
    validate_joined,
    validate_ledger,
    validate_witnesses,
)'''
assert old_import in text, "checker import block drifted"
text = text.replace(old_import, new_import, 1)

needle = '''    for src_file in sorted(graph_keys - source_keys):
        problems.append(f"{src_file}: graph document has no production-eligible source")

    # Authoritative statement ownership comes from joinDocument, not slot containment.
'''
replacement = '''    for src_file in sorted(graph_keys - source_keys):
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
'''
assert needle in text, "checker graph-key block drifted"
text = text.replace(needle, replacement, 1)

path.write_text(text, encoding="utf8")
