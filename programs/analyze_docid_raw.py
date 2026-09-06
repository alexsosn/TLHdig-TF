#!/usr/bin/env python
"""Measure docID semantics at the TLHdig converter input boundary.

Research-only utility for issue #10. It intentionally follows the same repaired
source stream and parse boundary as convert.director(), without changing TF output.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from xml.parsers import expat

import lxml.etree as LE

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import repair, source
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, corpus_files, rel as rel_key


EXAMPLE_LIMIT = 12


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    files = corpus_files()
    counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, object]]] = {
        "trim_diff": [],
        "missing": [],
        "empty": [],
        "whitespace_only": [],
        "special_ws": [],
        "fallback": [],
        "nested": [],
    }
    trim_deltas: Counter[tuple[int, int]] = Counter()

    def example(kind: str, rel: str, raw=None, extra=None) -> None:
        if len(examples[kind]) >= EXAMPLE_LIMIT:
            return
        item: dict[str, object] = {"path": rel}
        if raw is not None:
            item["raw_repr"] = repr(raw)
        if extra is not None:
            item["extra"] = extra
        examples[kind].append(item)

    for path in files:
        counts["source_xml"] += 1
        rel = rel_key(path, CORPUS)
        if rel == ENCRYPTED:
            counts["encrypted"] += 1
            continue

        data = path.read_bytes()
        entry = patches.get(rel)
        if entry:
            counts["patched_files"] += 1
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError:
                counts["patch_failed"] += 1
                continue

        try:
            # Match convert.director(): source.scan() is part of the parse boundary.
            source.scan(data)
            root = LE.fromstring(data)
        except (expat.ExpatError, LE.XMLSyntaxError, ValueError):
            counts["unparseable_after_repair"] += 1
            continue

        counts["parseable_after_repair"] += 1
        if root.find("body/div1/text") is None:
            counts["no_text_element"] += 1
            continue

        counts["converter_documents"] += 1
        element = root.find("AOHeader/docID")
        if element is None:
            counts["docid_element_missing"] += 1
            raw = None
            example("missing", rel)
        else:
            counts["docid_element_present"] += 1
            if len(element):
                counts["docid_with_child_elements"] += 1
                example("nested", rel, element.text, [child.tag for child in element])
            raw = root.findtext("AOHeader/docID")
            if raw is None:
                counts["docid_findtext_none_present"] += 1

        stem = Path(rel).stem
        current_docid = (raw or stem).strip()
        # TF 0.2.0 writes docid_raw=current_docid.
        current_docid_raw = current_docid

        if raw is None:
            # Candidate policy only; the plan will decide omit-vs-empty for missing.
            counts["candidate_empty_for_missing_changes_current"] += int(
                current_docid_raw != ""
            )
        else:
            if raw == "":
                counts["docid_empty_string"] += 1
                example("empty", rel, raw)
            elif raw.strip() == "":
                counts["docid_whitespace_only"] += 1
                example("whitespace_only", rel, raw)
            if raw != raw.strip():
                counts["docid_trim_diff"] += 1
                trim_deltas[
                    (len(raw) - len(raw.lstrip()), len(raw) - len(raw.rstrip()))
                ] += 1
                example("trim_diff", rel, raw, f"stripped={raw.strip()!r}")
            if any(ch in raw for ch in ("\t", "\n", "\r")):
                counts["docid_tab_newline_cr"] += 1
                example("special_ws", rel, raw)
            if raw != current_docid_raw:
                counts["candidate_preserve_present_raw_changes_current"] += 1

        if not raw:
            counts["current_filename_fallback"] += 1
            example("fallback", rel, raw, f"current_docid={current_docid!r}")
        if raw is not None and raw != "" and raw.strip() == "":
            counts["current_blank_docid_from_whitespace_only"] += int(
                current_docid == ""
            )
        if current_docid == stem:
            counts["current_docid_equals_filename_stem"] += 1

    assert counts["source_xml"] == len(files)
    assert counts["patch_failed"] == 0
    assert counts["converter_documents"] == 23884, counts
    assert (
        counts["converter_documents"]
        + counts["encrypted"]
        + counts["unparseable_after_repair"]
        + counts["no_text_element"]
        == counts["source_xml"]
    ), counts

    def n(key: str) -> str:
        return f"{counts[key]:,}"

    def table(kind: str) -> str:
        items = examples[kind]
        if not items:
            return "_None observed._\n"
        lines = ["| path | parsed value / note |", "|---|---|"]
        for item in items:
            text = str(item.get("raw_repr", ""))
            if item.get("extra") is not None:
                text = (text + " — " if text else "") + str(item["extra"])
            text = text.replace("|", "\\|")
            lines.append(f"| `{item['path']}` | `{text}` |")
        return "\n".join(lines) + "\n"

    trim_summary = ", ".join(
        f"lead={lead}, trail={trail}: {count:,}"
        for (lead, trail), count in sorted(trim_deltas.items())
    ) or "none"

    lines = [
        "# Research: `docid_raw` semantics in TLHdig Beta 0.3",
        "",
        "This report is the empirical prerequisite for issue #10. It was generated from the pinned",
        "TLHdig Beta 0.3 corpus before any Phase 4 production or test change.",
        "",
        "## Question",
        "",
        "The converter currently computes:",
        "",
        "```python",
        'docid = (root.findtext("AOHeader/docID") or Path(rel).stem).strip()',
        "docid_raw = docid",
        "```",
        "",
        "So `docid_raw` is normalized/fallback-derived rather than source-derived. The research",
        "measures the actual source cases before choosing a replacement contract.",
        "",
        "## Method",
        "",
        "The measurement follows the converter input boundary, not just parse-clean raw XML:",
        "",
        "1. enumerate `corpus_files()` from the pinned corpus;",
        "2. skip the encrypted record exactly as the converter does;",
        "3. apply `patches.yaml` with its expected SHA;",
        "4. run `source.scan()` and `lxml.etree.fromstring()`, matching `convert.director()`;",
        "5. exclude records still unparseable and records with no `body/div1/text`;",
        "6. inspect `AOHeader/docID` with both `find()` and the converter's `findtext()` API.",
        "",
        "Here **raw means parsed XML element text before `.strip()` and before filename fallback**.",
        "It is not byte-for-byte XML markup: XML entity expansion and parser line-ending semantics",
        "have already been applied.",
        "",
        "## Population",
        "",
        "| category | count |",
        "|---|---:|",
        f"| source `*.xml` records | {n('source_xml')} |",
        f"| files with repair-manifest entries | {n('patched_files')} |",
        f"| encrypted exclusions | {n('encrypted')} |",
        f"| unparseable after approved repairs | {n('unparseable_after_repair')} |",
        f"| missing text element | {n('no_text_element')} |",
        f"| **converter document population** | **{n('converter_documents')}** |",
        "",
        "The converter-document count is asserted to equal 23,884, matching TF 0.2.0.",
        "",
        "## `<docID>` observations on converter documents",
        "",
        "| observation | count |",
        "|---|---:|",
        f"| `<docID>` element present | {n('docid_element_present')} |",
        f"| `<docID>` element missing | {n('docid_element_missing')} |",
        f"| present element with `findtext() is None` | {n('docid_findtext_none_present')} |",
        f"| parsed value is exactly empty string | {n('docid_empty_string')} |",
        f"| parsed value is non-empty but whitespace-only | {n('docid_whitespace_only')} |",
        f"| parsed value differs from `.strip()` | {n('docid_trim_diff')} |",
        f"| parsed value contains TAB/LF/CR | {n('docid_tab_newline_cr')} |",
        f"| `<docID>` has child elements | {n('docid_with_child_elements')} |",
        f"| current filename-fallback cases (`not raw`) | {n('current_filename_fallback')} |",
        f"| current `docid` blank because raw is whitespace-only | {n('current_blank_docid_from_whitespace_only')} |",
        f"| current `docid` happens to equal filename stem | {n('current_docid_equals_filename_stem')} |",
        "",
        f"Trim-delta distribution: **{trim_summary}**.",
        "",
        "## Artifact impact under candidate policies",
        "",
        "This measures consequences; it does not choose policy.",
        "",
        f"- Preserving parsed text for every **present** `<docID>` would change **{n('candidate_preserve_present_raw_changes_current')}** `docid_raw` values relative to TF 0.2.0.",
        f"- Representing a **missing** `<docID>` by an empty string would change another **{n('candidate_empty_for_missing_changes_current')}** fallback-derived values. Omitting the feature is a distinct plan-stage option.",
        f"- Missing/empty values that currently trigger filename fallback: **{n('current_filename_fallback')}**.",
        "",
        "Therefore the plan must not assume this is metadata-only: release impact follows from the",
        "measured populations plus the explicit missing/empty representation chosen later.",
        "",
        "## Examples where raw text differs from normalized `docid`",
        "",
        table("trim_diff").rstrip(),
        "",
        "## Missing `<docID>` examples",
        "",
        table("missing").rstrip(),
        "",
        "## Empty `<docID>` examples",
        "",
        table("empty").rstrip(),
        "",
        "## Whitespace-only `<docID>` examples",
        "",
        table("whitespace_only").rstrip(),
        "",
        "## TAB/newline/carriage-return examples",
        "",
        table("special_ws").rstrip(),
        "",
        "## Current filename-fallback examples",
        "",
        table("fallback").rstrip(),
        "",
        "## Nested-content examples",
        "",
        table("nested").rstrip(),
        "",
        "## Constraints for the implementation plan",
        "",
        "1. Preserve the existing `docid` expression and observable behavior in this ticket;",
        "   whitespace-only behavior is measured here, not silently repaired.",
        "2. `docid_raw` must be source-derived. Filename fallback may be useful for `docid`, but",
        "   calling a fallback value `raw` is semantically false.",
        "3. Missing and present-empty are distinguishable at the XML API boundary even if TF",
        "   ultimately chooses the same representation; the plan must state that choice.",
        "4. TAB/LF/CR counts determine whether current corpus data needs a serialization policy;",
        "   future robustness may still justify a synthetic TF round-trip test.",
        "5. Do not change section addressing, duplicate grouping, or introduce a record ID.",
        "",
    ]
    report = "\n".join(lines)
    out = Path("docs/research-docid-raw.md")
    out.write_text(report, encoding="utf8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
