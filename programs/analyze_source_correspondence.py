#!/usr/bin/env python
"""Measure record correspondence across TLHdig releases by docID, CTH and content hash."""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import analyze_source_paths as paths


def _group(records, attr):
    out = defaultdict(list)
    for record in records:
        value = getattr(record, attr)
        if value:
            out[value].append(record)
    return out


def _table(rows):
    return [
        "| " + " | ".join(rows[0]) + " |",
        "|" + "|".join("---" for _ in rows[0]) + "|",
        *("| " + " | ".join(row) + " |" for row in rows[1:]),
    ]


def report(older_label, older, newer_label, newer):
    old_doc = _group(older, "docid")
    new_doc = _group(newer, "docid")
    common = sorted(set(old_doc) & set(new_doc))

    same_cth = []
    changed_cth = []
    unavailable_cth = []
    same_stem = []
    changed_stem = []
    for docid in common:
        old_cth = {r.cth for r in old_doc[docid] if r.cth}
        new_cth = {r.cth for r in new_doc[docid] if r.cth}
        if not old_cth or not new_cth:
            unavailable_cth.append(docid)
        elif old_cth & new_cth:
            same_cth.append(docid)
        else:
            changed_cth.append(docid)

        old_stem = {r.stem for r in old_doc[docid]}
        new_stem = {r.stem for r in new_doc[docid]}
        (same_stem if old_stem & new_stem else changed_stem).append(docid)

    old_hash = _group(older, "sha256")
    new_hash = _group(newer, "sha256")
    identical_hashes = set(old_hash) & set(new_hash)
    identical_changed_cth = []
    for digest in identical_hashes:
        old_cth = {r.cth for r in old_hash[digest] if r.cth}
        new_cth = {r.cth for r in new_hash[digest] if r.cth}
        if old_cth and new_cth and not (old_cth & new_cth):
            identical_changed_cth.append(digest)

    lines = ["## Cross-release record correspondence", ""]
    lines += [
        "Path churn can reflect either directory-layout changes or actual catalogue movement. The",
        "following comparison uses source `docID` and CTH independently of the path string. Records",
        "whose CTH cannot be parsed from at least one release path are kept out of the migration count.",
        "",
    ]
    lines += _table([
        ("measure", "value"),
        ("docIDs present in both releases", f"{len(common):,}"),
        ("common docIDs retaining at least one CTH", f"{len(same_cth):,}"),
        ("common docIDs with a parsed CTH but no CTH overlap", f"{len(changed_cth):,}"),
        ("common docIDs with CTH unavailable in at least one release", f"{len(unavailable_cth):,}"),
        ("common docIDs retaining at least one filename stem", f"{len(same_stem):,}"),
        ("common docIDs with no filename-stem overlap", f"{len(changed_stem):,}"),
        ("byte-identical payload hashes present in both", f"{len(identical_hashes):,}"),
        ("byte-identical payloads with parsed CTH but no CTH overlap", f"{len(identical_changed_cth):,}"),
    ]) + [""]

    if changed_cth:
        lines += ["### Examples with parsed CTH but no CTH overlap", ""]
        rows = [("docID", older_label + " CTH/path", newer_label + " CTH/path")]
        for docid in changed_cth[:50]:
            left = "<br>".join(f"CTH {r.cth}: `{r.rel}`" for r in old_doc[docid])
            right = "<br>".join(f"CTH {r.cth}: `{r.rel}`" for r in new_doc[docid])
            rows.append((f"`{docid}`", left, right))
        lines += _table(rows) + [""]

    if unavailable_cth:
        lines += ["### Records excluded from the CTH-migration count", ""]
        rows = [("docID", older_label + " path", newer_label + " path")]
        for docid in unavailable_cth[:50]:
            left = "<br>".join(f"`{r.rel}`" for r in old_doc[docid])
            right = "<br>".join(f"`{r.rel}`" for r in new_doc[docid])
            rows.append((f"`{docid}`", left, right))
        lines += _table(rows) + [""]

    if identical_changed_cth:
        lines += ["### Byte-identical records whose parsed CTH changed", ""]
        rows = [(older_label, newer_label)]
        for digest in identical_changed_cth[:50]:
            left = "<br>".join(f"CTH {r.cth}: `{r.rel}`" for r in old_hash[digest])
            right = "<br>".join(f"CTH {r.cth}: `{r.rel}`" for r in new_hash[digest])
            rows.append((left, right))
        lines += _table(rows) + [""]

    lines += [
        "The `docID` comparison is deliberately set-based because one manuscript identity may have",
        "multiple records/CTH contexts in either release. When both releases provide a parseable CTH,",
        "a lack of overlap is a strong signal of catalogue/context movement; retained CTH with a changed",
        "path is consistent with a layout-only reorganisation. Malformed or exceptional path grammar is",
        "reported separately rather than counted as a migration.",
        "",
    ]
    return "\n".join(lines)


def main(argv):
    if len(argv) != 2 or any("=" not in arg for arg in argv):
        raise SystemExit("usage: analyze_source_correspondence.py OLDER=PATH NEWER=PATH")
    labels = []
    datasets = []
    for arg in argv:
        label, raw = arg.split("=", 1)
        labels.append(label)
        datasets.append(paths.scan(label, Path(raw).expanduser().resolve()))
    print(report(labels[0], datasets[0], labels[1], datasets[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
