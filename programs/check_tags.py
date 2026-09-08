#!/usr/bin/env python
"""Contract B: every source construct has an explicit declared disposition.

Body markup and AOHeader metadata are inventoried separately because their preservation
semantics differ. Body ``raw`` survives in provenance; header ``known-unpreserved``
means exactly the opposite and remains visible until #57/#58 resolve it.
"""
from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import lxml.etree as LE

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import repair, tags
from tlhdig.paths import ENCRYPTED, PATCHES, REPORTS, corpus_files, rel


def _local(name: str) -> str:
    """Historical body contract: AO-prefixed body markup is keyed by local name."""
    return LE.QName(name).localname if name.startswith("{") else name


def _header_name(name: str) -> str:
    """Keep a header Clark name intact so a new namespace cannot impersonate a known field."""
    return name


def _direct_headers(root) -> list:
    """Return direct AOHeader-like children for complete inventory diagnostics."""
    return [
        el
        for el in root
        if isinstance(el.tag, str) and _local(el.tag) == "AOHeader"
    ]


def declaration_drift(observed, declared) -> tuple[list, list]:
    """Return (undeclared observed values, declared-but-unobserved values).

    Header declarations are a closed snapshot of the pinned source vocabulary, not a
    permissive future allowlist. Checking both directions prevents a speculative field
    from being declared today and then silently accepted if it appears in a later source.
    """
    observed_keys = set(observed)
    declared_keys = set(declared)
    return sorted(observed_keys - declared_keys), sorted(declared_keys - observed_keys)


def header_structure_problems(root) -> list[str]:
    """Validate the structural paths that the converter actually consumes.

    A name can be known while its placement is not: ``findtext('AOHeader/docID')`` and
    ``iterfind('AOHeader/meta//*')`` only consume very specific unqualified paths. A
    duplicate header or a known field moved elsewhere must therefore fail Contract B
    even though the vocabulary itself is unchanged.
    """
    header_like = _direct_headers(root)
    exact_headers = [el for el in header_like if el.tag == "AOHeader"]
    if len(header_like) != 1 or len(exact_headers) != 1:
        return [f"expected exactly one direct AOHeader, found {len(exact_headers)}"]

    header = exact_headers[0]
    problems: list[str] = []

    direct_docids = [
        el for el in header if isinstance(el.tag, str) and el.tag == "docID"
    ]
    if len(direct_docids) != 1:
        problems.append(
            f"expected exactly one direct AOHeader/docID, found {len(direct_docids)}"
        )

    all_docids = [
        el
        for el in header.iterdescendants()
        if isinstance(el.tag, str) and el.tag == "docID"
    ]
    if len(all_docids) != len(direct_docids):
        problems.append("misplaced docID outside direct AOHeader/docID path")

    direct_metas = {
        el for el in header if isinstance(el.tag, str) and el.tag == "meta"
    }
    for el in header.iterdescendants():
        if not isinstance(el.tag, str) or el.tag not in tags.EDIT_KINDS:
            continue
        parent = el.getparent()
        under_direct_meta = False
        while parent is not None and parent is not header:
            if parent in direct_metas:
                under_direct_meta = True
                break
            parent = parent.getparent()
        if not under_direct_meta:
            problems.append(f"edit event {el.tag} outside direct AOHeader/meta")

    return problems


@dataclass
class Inventory:
    body_elements: Counter = field(default_factory=Counter)
    header_elements: Counter = field(default_factory=Counter)
    header_attrs: Counter = field(default_factory=Counter)

    def add(self, other: "Inventory") -> None:
        self.body_elements.update(other.body_elements)
        self.header_elements.update(other.header_elements)
        self.header_attrs.update(other.header_attrs)


def inventory_root(root) -> Inventory:
    """Inventory one parsed AOxml root, keeping body/header namespaces distinct."""
    inv = Inventory()
    text = root.find(".//{*}text")
    if text is not None:
        for el in text.iter():
            if isinstance(el.tag, str):
                inv.body_elements[_local(el.tag)] += 1

    # Inventory every AOHeader-like direct child for diagnostics. The separate
    # structural contract decides whether that cardinality/namespace is consumable.
    for header in _direct_headers(root):
        for el in header.iter():
            if not isinstance(el.tag, str):
                continue
            name = _header_name(el.tag)
            inv.header_elements[name] += 1
            for attr in el.attrib:
                inv.header_attrs[(name, _header_name(attr))] += 1
    return inv


def _element_sections(found: Counter, destinations: dict, kinds: dict) -> list[str]:
    by_kind: dict[str, list[tuple[str, int]]] = {}
    for name, n in found.most_common():
        by_kind.setdefault(destinations.get(name, "UNDECLARED"), []).append((name, n))
    lines = []
    for kind, meaning in list(kinds.items()) + [("UNDECLARED", "no disposition declared")]:
        items = by_kind.get(kind)
        if not items:
            continue
        lines += [f"### `{kind}` — {meaning}", "", "| element | occurrences |", "|---|---:|"]
        lines.extend(f"| `{name}` | {count:,} |" for name, count in items)
        lines.append("")
    return lines


def render_report(inv: Inventory) -> str:
    """Render a regioned Contract-B report; known header loss is never called raw."""
    lines = [
        "# AOxml Contract B inventory", "",
        "Generated by `programs/check_tags.py` from the repaired source stream.", "",
        "## Body `<text>` element inventory", "",
        f"{len(inv.body_elements)} distinct element names under `<text>`.", "",
    ]
    lines.extend(_element_sections(inv.body_elements, tags.DESTINATION, tags.KINDS))
    lines += [
        "## `AOHeader` element inventory", "",
        f"{len(inv.header_elements)} distinct element names under `AOHeader`.", "",
        "`known-unpreserved` is an explicit current loss disposition; it does not mean preserved.", "",
    ]
    lines.extend(_element_sections(inv.header_elements, tags.HEADER_DESTINATION, tags.HEADER_KINDS))

    by_kind: dict[str, list[tuple[tuple[str, str], int]]] = {}
    for pair, n in inv.header_attrs.most_common():
        by_kind.setdefault(tags.HEADER_ATTR_DESTINATION.get(pair, "UNDECLARED"), []).append((pair, n))
    lines += [
        "## `AOHeader` attribute inventory", "",
        f"{len(inv.header_attrs)} distinct element/attribute pairs under `AOHeader`.", "",
    ]
    for kind, meaning in list(tags.HEADER_KINDS.items()) + [("UNDECLARED", "no disposition declared")]:
        items = by_kind.get(kind)
        if not items:
            continue
        lines += [f"### `{kind}` — {meaning}", "", "| element@attribute | occurrences |", "|---|---:|"]
        lines.extend(f"| `{el}@{attr}` | {count:,} |" for (el, attr), count in items)
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    man = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    inv = Inventory()
    structural: list[tuple[str, str]] = []
    for f in corpus_files():
        r = rel(f)
        if r == ENCRYPTED:
            continue
        data = f.read_bytes()
        entry = man.get(r)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError:
                continue
        try:
            root = LE.fromstring(data)
        except Exception:
            continue
        structural.extend((r, p) for p in header_structure_problems(root))
        inv.add(inventory_root(root))

    missing_body = tags.undeclared(inv.body_elements)
    missing_header, extra_header = declaration_drift(
        inv.header_elements, tags.HEADER_DESTINATION
    )
    missing_attrs, extra_attrs = declaration_drift(
        inv.header_attrs, tags.HEADER_ATTR_DESTINATION
    )

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "tags.md").write_text(render_report(inv), encoding="utf8")

    if structural or missing_body or missing_header or extra_header or missing_attrs or extra_attrs:
        print("CONTRACT B FAILED")
        if structural:
            print(f"  AOHeader structural contract violations ({len(structural)}):")
            for path, problem in structural[:200]:
                print(f"    {path}: {problem}")
        if missing_body:
            print(f"  undeclared body elements ({len(missing_body)}):")
            for name in missing_body:
                print(f"    {name} ({inv.body_elements[name]:,})")
        if missing_header:
            print(f"  undeclared AOHeader elements ({len(missing_header)}):")
            for name in missing_header:
                print(f"    {name} ({inv.header_elements[name]:,})")
        if extra_header:
            print(f"  declared but unobserved AOHeader elements ({len(extra_header)}):")
            for name in extra_header:
                print(f"    {name}")
        if missing_attrs:
            print(f"  undeclared AOHeader element@attribute pairs ({len(missing_attrs)}):")
            for el, attr in missing_attrs:
                print(f"    {el}@{attr} ({inv.header_attrs[(el, attr)]:,})")
        if extra_attrs:
            print(f"  declared but unobserved AOHeader element@attribute pairs ({len(extra_attrs)}):")
            for el, attr in extra_attrs:
                print(f"    {el}@{attr}")
        return 1

    known_loss_elements = sum(
        inv.header_elements[name]
        for name, kind in tags.HEADER_DESTINATION.items()
        if kind in {"known-unpreserved", "malformed-unpreserved"}
    )
    known_loss_attrs = sum(
        inv.header_attrs[pair]
        for pair, kind in tags.HEADER_ATTR_DESTINATION.items()
        if kind in {"known-unpreserved", "malformed-unpreserved"}
    )
    print(
        f"Contract B covers {len(inv.body_elements)} body elements, "
        f"{len(inv.header_elements)} header elements and {len(inv.header_attrs)} header attribute pairs"
    )
    print(
        f"explicit current header loss: {known_loss_elements:,} element occurrences, "
        f"{known_loss_attrs:,} attribute occurrences -> reports/tags.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
