#!/usr/bin/env python
"""Inventory TLHdig directory-tree structure, including directories without XML files.

This complements analyze_source_paths.py, whose unit of observation is an XML record.
Archive releases can contain empty or non-XML directories that still reveal how the
source tree was organised; those must not silently disappear from path-grammar research.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath

import analyze_source_paths as paths

SUFFIX_RE = re.compile(r"_([A-Za-z][A-Za-z0-9]*)$")


def inventory(base: Path) -> dict:
    root = paths._find_root(base)
    directories = sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_dir() and "__MACOSX" not in p.parts
    )
    top = [d for d in directories if len(PurePosixPath(d).parts) == 1]
    nested = [d for d in directories if len(PurePosixPath(d).parts) > 1]

    # Mark every intermediate directory that is an ancestor of at least one XML file.
    with_xml: set[str] = set()
    for xml in root.rglob("*.xml"):
        rel = xml.relative_to(root)
        parent = rel.parent
        while len(parent.parts) > 1:
            with_xml.add(parent.as_posix())
            parent = parent.parent

    suffixes: Counter[str] = Counter()
    for d in nested:
        m = SUFFIX_RE.search(PurePosixPath(d).name)
        if m:
            suffixes[m.group(1)] += 1

    return {
        "root": root,
        "directories": directories,
        "top": top,
        "nested": nested,
        "nested_with_xml": sorted(set(nested) & with_xml),
        "nested_without_xml": sorted(set(nested) - with_xml),
        "suffixes": suffixes,
    }


def _table(rows: list[tuple[str, ...]]) -> list[str]:
    return [
        "| " + " | ".join(rows[0]) + " |",
        "|" + "|".join("---" for _ in rows[0]) + "|",
        *("| " + " | ".join(row) + " |" for row in rows[1:]),
    ]


def report(releases: dict[str, dict]) -> str:
    lines = ["## Directory-tree inventory", ""]
    lines += [
        "This section inventories directories independently of XML records. This matters for Beta 0.2,",
        "whose ZIP contains nested classification-looking directories that may contain no XML files.",
        "",
    ]
    rows = [("release", "top-level dirs", "nested dirs", "nested with XML", "nested without XML")]
    for label, data in releases.items():
        rows.append((
            label,
            f"{len(data['top']):,}",
            f"{len(data['nested']):,}",
            f"{len(data['nested_with_xml']):,}",
            f"{len(data['nested_without_xml']):,}",
        ))
    lines += _table(rows) + [""]

    for label, data in releases.items():
        lines += [f"### {label}: directory-only structure", ""]
        suffixes: Counter[str] = data["suffixes"]
        if suffixes:
            lines += ["Suffix-like tokens on nested directory names:", ""]
            lines += _table([
                ("token", "directories"),
                *((f"`{token}`", f"{count:,}") for token, count in suffixes.most_common()),
            ]) + [""]
        else:
            lines += ["No suffix-like `_TOKEN` component occurs on nested directory names.", ""]

        no_xml = data["nested_without_xml"]
        if no_xml:
            lines += ["Nested directories with no XML descendant (first 100):", ""]
            lines += [*(f"- `{d}`" for d in no_xml[:100]), ""]
            if len(no_xml) > 100:
                lines += [f"{len(no_xml) - 100:,} additional directories omitted from this display.", ""]

    labels = list(releases)
    if len(labels) >= 2:
        lines += ["### Cross-release directory observation", ""]
        older, newer = labels[0], labels[-1]
        old = releases[older]
        new = releases[newer]
        old_suffixes = set(old["suffixes"])
        new_projects = {
            m.group(2)
            for d in new["top"]
            if (m := paths.TOP_RE.match(PurePosixPath(d).name)) and m.group(2)
        }
        overlap = sorted(old_suffixes & new_projects)
        lines += [
            f"Nested suffix-like tokens in {older}: {', '.join(sorted(old_suffixes)) or 'none'}.",
            f"Top-level project codes in {newer}: {', '.join(sorted(new_projects)) or 'none'}.",
            f"Tokens occurring in both positions: {', '.join(overlap) or 'none'}.",
            "",
            "Directory-name overlap is descriptive evidence only. In particular, an empty Beta 0.2",
            "directory must not be treated as a record-level project assignment unless independent",
            "documentation or record correspondence supports that interpretation.",
            "",
        ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    releases = {}
    for arg in argv:
        if "=" not in arg:
            raise SystemExit(f"expected LABEL=PATH, got {arg!r}")
        label, raw = arg.split("=", 1)
        releases[label] = inventory(Path(raw).expanduser().resolve())
    print(report(releases))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
