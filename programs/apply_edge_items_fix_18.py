#!/usr/bin/env python
from pathlib import Path

path = Path("programs/check_manuscript_joins.py")
text = path.read_text(encoding="utf8")
old_import = '''    FragmentRow,
    StatementRow,
    validate_edge_types,
'''
new_import = '''    FragmentRow,
    StatementRow,
    edge_type_rows,
    validate_edge_types,
'''
assert old_import in text, "checker import block drifted"
text = text.replace(old_import, new_import, 1)
old_loop = '''    edge_rows: list[tuple[str, str, str]] = []
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
'''
new_loop = '''    edge_rows: list[tuple[str, str, str]] = []
    for edge_name in (
        "joinDocument", "joinLeft", "joinRight", "joined", "witness", "witness_resolution"
    ):
        feature = getattr(E, edge_name, None)
        if feature is None:
            continue
        edge_rows.extend(edge_type_rows(edge_name, feature.items(), F.otype.v))
'''
assert old_loop in text, "checker global edge loop drifted"
text = text.replace(old_loop, new_loop, 1)
path.write_text(text, encoding="utf8")
