#!/usr/bin/env python
"""Measure whether AOHeader can be preserved byte-exactly on document nodes.

Research-only analyser for issues #57/#58. It follows the converter's repaired parse
stream, then maps the repaired AOHeader span back to the immutable on-disk source bytes.
No TF artifact is written.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from xml.parsers import expat

import lxml.etree as LE

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import repair, source
from tlhdig.paths import ENCRYPTED, PATCHES, corpus_files, rel


def analyze() -> tuple[Counter, list[str], list[str]]:
    manifest = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    stats = Counter()
    problems: list[str] = []
    changed_examples: list[str] = []

    for path in corpus_files():
        source_rel = rel(path)
        if source_rel == ENCRYPTED:
            stats["encrypted_skipped"] += 1
            continue

        original = path.read_bytes()
        data = original
        omap = None
        entry = manifest.get(source_rel)
        if entry:
            stats["patched_source_files"] += 1
            try:
                omap = repair.OffsetMap(original, entry[1])
                data = repair.apply(original, entry[1], expect_sha=entry[0])
            except repair.PatchError:
                stats["patch_failure"] += 1
                continue

        try:
            spans = source.scan(data)
            root = LE.fromstring(data)
        except (expat.ExpatError, LE.XMLSyntaxError, ValueError):
            stats["unparseable_after_repair"] += 1
            continue

        # Match the production converter population: a parseable document without the
        # body text container is not emitted as a document node.
        div1 = root.find("body/div1")
        text = div1.find("text") if div1 is not None else None
        if text is None:
            stats["parseable_without_text"] += 1
            continue

        stats["converted_documents"] += 1
        headers = [sp for sp in spans if sp.tag == "AOHeader" and sp.depth == 1]
        if len(headers) != 1:
            problems.append(
                f"{source_rel}: expected one depth-1 AOHeader span, found {len(headers)}"
            )
            continue
        header = headers[0]

        repaired_span = header.outer
        original_span = (
            omap.span_to_original(*repaired_span) if omap is not None else repaired_span
        )
        a, b = original_span
        if not (0 <= a < b <= len(original)):
            problems.append(
                f"{source_rel}: mapped AOHeader span {a}-{b} outside {len(original)} bytes"
            )
            continue

        raw_start = original.find(b"<AOHeader")
        raw_close = original.find(b"</AOHeader>", raw_start if raw_start >= 0 else 0)
        raw_end = raw_close + len(b"</AOHeader>") if raw_close >= 0 else -1
        if raw_start < 0 or raw_close < 0:
            problems.append(f"{source_rel}: original bytes have no complete AOHeader")
            continue
        if original_span != (raw_start, raw_end):
            problems.append(
                f"{source_rel}: mapped {a}-{b}, raw AOHeader is {raw_start}-{raw_end}"
            )
            continue

        chunk = original[a:b]
        if not chunk.startswith(b"<AOHeader") or not chunk.endswith(b"</AOHeader>"):
            problems.append(f"{source_rel}: mapped slice is not an AOHeader element")
            continue

        stats["exact_original_header_spans"] += 1
        stats["header_bytes_total"] += len(chunk)
        if omap is not None and original_span != repaired_span:
            stats["header_offsets_shifted_by_repairs_elsewhere"] += 1
        repaired_chunk = data[header.outer_start : header.outer_end]
        if repaired_chunk != chunk:
            stats["header_bytes_changed_by_repair"] += 1
            if len(changed_examples) < 20:
                changed_examples.append(source_rel)

        # Whole-header values exercise all TF string escaping cases we care about.
        text_value = chunk.decode("utf8", "surrogateescape")
        stats["headers_with_newline"] += int("\n" in text_value or "\r" in text_value)
        stats["headers_with_tab"] += int("\t" in text_value)
        stats["headers_with_backslash"] += int("\\" in text_value)

        docid = root.find("AOHeader/docID")
        raw_docid = None if docid is None else docid.text
        normalized = (raw_docid or Path(source_rel).stem).strip()
        if raw_docid is None:
            stats["missing_docid"] += 1
        elif raw_docid == "":
            stats["empty_docid"] += 1
        if raw_docid is not None and raw_docid != normalized:
            stats["docid_raw_differs_from_docid"] += 1

    return stats, problems, changed_examples


def main() -> int:
    stats, problems, changed = analyze()
    order = (
        "converted_documents",
        "exact_original_header_spans",
        "patched_source_files",
        "header_offsets_shifted_by_repairs_elsewhere",
        "header_bytes_changed_by_repair",
        "header_bytes_total",
        "headers_with_newline",
        "headers_with_tab",
        "headers_with_backslash",
        "docid_raw_differs_from_docid",
        "missing_docid",
        "empty_docid",
        "unparseable_after_repair",
        "parseable_without_text",
        "patch_failure",
    )
    for key in order:
        print(f"{key:42} {stats[key]:,}")
    if changed:
        print("header bytes changed by repair:")
        for item in changed:
            print(f"  {item}")
    if problems:
        print(f"HEADER PROVENANCE RESEARCH FAILED: {len(problems)} problem(s)")
        for problem in problems[:100]:
            print(f"  {problem}")
        return 1
    if stats["exact_original_header_spans"] != stats["converted_documents"]:
        print("HEADER PROVENANCE RESEARCH FAILED: incomplete exact-span coverage")
        return 1
    print("all converted documents have an exact AOHeader span in original source bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
