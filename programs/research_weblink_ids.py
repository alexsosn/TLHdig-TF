#!/usr/bin/env python3
"""Inventory document identities relevant to TLHdig online web links (#41).

This is a research tool, not an app dependency. It reads the committed Text-Fabric
``otype`` and ``docid`` files directly so the duplicate/identifier-shape census is
reproducible without loading ``oslots`` or the multi-gigabyte graph.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROGRAMS = Path(__file__).resolve().parent
ROOT = PROGRAMS.parent
sys.path.insert(0, str(PROGRAMS))

from tlhdig import TF_VERSION


def data_rows(path: Path):
    """Yield ``(node_spec, value)`` rows after a TF feature header."""

    in_body = False
    with path.open(encoding="utf8") as stream:
        for raw in stream:
            line = raw.rstrip("\r\n")
            if not in_body:
                if not line:
                    in_body = True
                continue
            if not line:
                continue
            spec, sep, value = line.partition("\t")
            if not sep:
                raise ValueError(f"{path}: malformed TF data row: {line!r}")
            yield spec, value


def expand_node_spec(spec: str):
    """Expand TF comma/range node notation used by node features."""

    for part in spec.split(","):
        part = part.strip()
        if not part:
            raise ValueError(f"empty node-spec part in {spec!r}")
        if "-" in part:
            first, last = part.split("-", 1)
            first_i = int(first)
            last_i = int(last)
            if last_i < first_i:
                raise ValueError(f"descending node range {part!r}")
            yield from range(first_i, last_i + 1)
        else:
            yield int(part)


def document_nodes(otype_path: Path) -> set[int]:
    result: set[int] = set()
    for spec, value in data_rows(otype_path):
        if value == "document":
            result.update(expand_node_spec(spec))
    if not result:
        raise ValueError(f"{otype_path}: no document nodes found")
    return result


def document_docids(docid_path: Path, documents: set[int]) -> dict[int, str]:
    result: dict[int, str] = {}
    for spec, value in data_rows(docid_path):
        for node in expand_node_spec(spec):
            if node not in documents:
                continue
            if node in result:
                raise ValueError(f"{docid_path}: duplicate assignment for node {node}")
            result[node] = value
    missing = documents - result.keys()
    if missing:
        sample = sorted(missing)[:10]
        raise ValueError(f"{docid_path}: {len(missing)} document nodes lack docid; sample={sample}")
    return result


def normalize_lookup(value: str) -> str | None:
    """Mirror the evidenced TLHdig ``d=`` lookup normalization for research."""

    if not value or value.endswith("(+)") or value.endswith("++"):
        return None
    if value.endswith("+"):
        value = value[:-1]
    return value or None


def identifier_flags(value: str) -> list[str]:
    flags: list[str] = []
    if value.endswith("(+)"):
        flags.append("trailing_indirect_join_marker")
    elif value.endswith("+"):
        flags.append("trailing_direct_join_marker")
    if "+" in value[:-1] if value.endswith("+") else "+" in value:
        flags.append("internal_plus")
    if "/" in value:
        flags.append("slash")
    if "_" in value:
        flags.append("underscore")
    if any(ch in value for ch in "′´'"):
        flags.append("prime_or_apostrophe")
    if any(ord(ch) > 127 for ch in value):
        flags.append("non_ascii")
    if " " in value:
        flags.append("space")
    if "(" in value or ")" in value:
        flags.append("parenthesis")
    return flags


def report(tf_dir: Path) -> dict:
    documents = document_nodes(tf_dir / "otype.tf")
    by_node = document_docids(tf_dir / "docid.tf", documents)

    groups: dict[str, list[int]] = defaultdict(list)
    for node, value in by_node.items():
        groups[value].append(node)

    duplicates = [
        {"docid": value, "document_nodes": sorted(nodes), "record_count": len(nodes)}
        for value, nodes in sorted(groups.items())
        if len(nodes) > 1
    ]

    lookup_groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    unsupported_lookup_docids: dict[str, list[int]] = defaultdict(list)
    for node, raw in by_node.items():
        lookup = normalize_lookup(raw)
        if lookup is None:
            unsupported_lookup_docids[raw].append(node)
        else:
            lookup_groups[lookup].append((node, raw))

    lookup_collisions = []
    normalization_only_collisions = []
    for lookup, records in sorted(lookup_groups.items()):
        if len(records) <= 1:
            continue
        raw_docids = sorted({raw for _, raw in records})
        item = {
            "lookup": lookup,
            "raw_docids": raw_docids,
            "document_nodes": sorted(node for node, _ in records),
            "record_count": len(records),
        }
        lookup_collisions.append(item)
        if len(raw_docids) > 1:
            normalization_only_collisions.append(item)

    flag_counts = Counter()
    flagged_values: dict[str, list[str]] = {}
    for value in sorted(groups):
        flags = identifier_flags(value)
        for flag in flags:
            flag_counts[flag] += 1
        if flags:
            flagged_values[value] = flags

    return {
        "tf_version": tf_dir.name,
        "document_count": len(documents),
        "distinct_docid_count": len(groups),
        "duplicate_docid_count": len(duplicates),
        "documents_in_duplicate_groups": sum(item["record_count"] for item in duplicates),
        "lookup_collision_count": len(lookup_collisions),
        "normalization_only_collision_count": len(normalization_only_collisions),
        "unsupported_lookup_docid_count": len(unsupported_lookup_docids),
        "identifier_flag_counts": dict(sorted(flag_counts.items())),
        "duplicate_groups": duplicates,
        "lookup_collision_groups": lookup_collisions,
        "normalization_only_collision_groups": normalization_only_collisions,
        "unsupported_lookup_docids": {
            raw: sorted(nodes) for raw, nodes in sorted(unsupported_lookup_docids.items())
        },
        "flagged_identifiers": flagged_values,
    }


def _version_key(path: Path) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in path.name.split("."))
    except ValueError:
        return ()


def default_tf_dir() -> Path:
    """Use the target TF release when materialized, else the newest committed release."""

    target = ROOT / "tf" / TF_VERSION
    if (target / "otype.tf").is_file():
        return target
    candidates = [
        path
        for path in (ROOT / "tf").iterdir()
        if path.is_dir() and (path / "otype.tf").is_file() and _version_key(path)
    ]
    if not candidates:
        raise ValueError("no committed Text-Fabric artifact contains otype.tf")
    return max(candidates, key=_version_key)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tf-dir",
        type=Path,
        default=None,
        help="released TF directory (default: target release if materialized, otherwise newest committed release)",
    )
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    parser.add_argument(
        "--expect-duplicate-count",
        type=int,
        help="fail if the measured raw duplicate-docid group count differs",
    )
    parser.add_argument(
        "--expect-normalization-only-collision-count",
        type=int,
        help="fail if distinct raw docids collapse to an unexpected number of lookup keys",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print only compact identity-safety counts instead of full group detail",
    )
    args = parser.parse_args(argv)

    try:
        result = report(args.tf_dir or default_tf_dir())
    except (OSError, ValueError) as exc:
        print(f"weblink identity research: ERROR: {exc}", file=sys.stderr)
        return 1

    if (
        args.expect_duplicate_count is not None
        and result["duplicate_docid_count"] != args.expect_duplicate_count
    ):
        print(
            "weblink identity research: duplicate count mismatch: "
            f"expected {args.expect_duplicate_count}, got {result['duplicate_docid_count']}",
            file=sys.stderr,
        )
        return 1

    if (
        args.expect_normalization_only_collision_count is not None
        and result["normalization_only_collision_count"]
        != args.expect_normalization_only_collision_count
    ):
        print(
            "weblink identity research: normalization-only collision count mismatch: "
            f"expected {args.expect_normalization_only_collision_count}, "
            f"got {result['normalization_only_collision_count']}",
            file=sys.stderr,
        )
        return 1

    if args.summary:
        result = {
            key: result[key]
            for key in (
                "tf_version",
                "document_count",
                "distinct_docid_count",
                "duplicate_docid_count",
                "documents_in_duplicate_groups",
                "lookup_collision_count",
                "normalization_only_collision_count",
                "unsupported_lookup_docid_count",
            )
        }

    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
