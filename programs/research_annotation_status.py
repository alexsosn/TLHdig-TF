#!/usr/bin/env python
"""Research-only census for issue #79: annotation-stage evidence in TLHdig 0.3 XML.

This deliberately does not interpret the source markers. It measures where annotation
metadata lives, which leading marker glyphs occur in mrpN values, how mrp0sel relates
to those candidates, and whether those glyphs leaked into shipped lexical lemmas.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "TLHdig-0.3"
TF = ROOT / "tf" / "0.4.0"

WORD_RE = re.compile(r"<w\b([^>]*)>")
ANNOT_RE = re.compile(r"<annot\b([^>]*)/?>")
ATTR_RE = re.compile(r"([:\w.-]+)\s*=\s*([\"'])(.*?)\2", re.S)
MRP_RE = re.compile(r"^mrp(\d+)$")
DOCID_RE = re.compile(r"<docID>(.*?)</docID>", re.S)
# Marker-looking Unicode seen in HFR XML before the actual lemma. Keep this purely
# lexical: the research result decides semantics, not this detector.
MARKER_RE = re.compile(r"^([^\w\s@=+\-/]+)\s+")


def attrs(raw: str) -> dict[str, str]:
    return {m.group(1): m.group(3) for m in ATTR_RE.finditer(raw)}


def marker(value: str) -> str:
    m = MARKER_RE.match(value.lstrip())
    return m.group(1) if m else "<none>"


def project(rel: Path) -> str:
    return rel.parts[0] if rel.parts else ""


def main() -> int:
    files = [p for p in CORPUS.rglob("*") if p.is_file() and p.name != "LICENSE"]
    projects = Counter()
    annot_event_docs = Counter()
    annot_events = Counter()
    words = Counter()
    candidate_markers = Counter()
    selected_markers = Counter()
    selected_unresolved = Counter()
    docs_by_marker: dict[str, set[str]] = defaultdict(set)
    examples: dict[str, list[dict[str, str]]] = defaultdict(list)
    hfr_doc_classes = Counter()

    for path in files:
        try:
            text = path.read_text(encoding="utf8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(CORPUS)
        proj = project(rel)
        projects[proj] += 1
        dm = DOCID_RE.search(text)
        docid = (dm.group(1).strip() if dm else path.stem)

        events = [attrs(m.group(1)) for m in ANNOT_RE.finditer(text)]
        if events:
            annot_event_docs[proj] += 1
        for e in events:
            key = f"editor={e.get('editor','')}|date={bool(e.get('date'))}|data={bool(e.get('data'))}"
            annot_events[key] += 1

        doc_markers = set()
        doc_has_numeric_selection = False
        doc_has_unresolved = False
        for wm in WORD_RE.finditer(text):
            a = attrs(wm.group(1))
            mrps = {}
            for k, v in a.items():
                mm = MRP_RE.match(k)
                if mm:
                    idx = int(mm.group(1))
                    mk = marker(v)
                    mrps[idx] = (v, mk)
                    candidate_markers[mk] += 1
                    doc_markers.add(mk)
                    docs_by_marker[mk].add(str(rel))
                    if len(examples[mk]) < 8:
                        examples[mk].append({"file": str(rel), "docid": docid, "attribute": k, "value": v[:180]})
            if mrps:
                words["with_mrp"] += 1
            else:
                words["without_mrp"] += 1
            sel = (a.get("mrp0sel") or "").split()
            numeric = []
            for tok in sel:
                m = re.match(r"^(\d+)", tok)
                if m:
                    numeric.append(int(m.group(1)))
            if numeric:
                doc_has_numeric_selection = True
                words["numeric_selected"] += 1
                for idx in numeric:
                    if idx in mrps:
                        selected_markers[mrps[idx][1]] += 1
                    else:
                        selected_unresolved["selected_index_missing"] += 1
            if "???" in sel:
                doc_has_unresolved = True
                words["selector_unknown"] += 1
            for special in ("DEL", "AKK", "HURR", "HAT", "SUM", "LUW"):
                if special in sel:
                    words[f"selector_{special}"] += 1

        if proj.endswith("_XML_HFR"):
            if doc_has_numeric_selection and doc_has_unresolved:
                hfr_doc_classes["numeric+unknown"] += 1
            elif doc_has_numeric_selection:
                hfr_doc_classes["numeric_only"] += 1
            elif doc_has_unresolved:
                hfr_doc_classes["unknown_only"] += 1
            else:
                hfr_doc_classes["neither"] += 1
            hfr_doc_classes[f"marker_set:{' '.join(sorted(doc_markers)) or '<none>'}"] += 1

    # Check whether marker-like glyphs survive at the front of shipped lemma values.
    lemma_marker_lines = Counter()
    lemma_examples: list[str] = []
    lemma_path = TF / "lemma.tf"
    if lemma_path.is_file():
        for line in lemma_path.read_text(encoding="utf8", errors="replace").splitlines():
            if not line or line.startswith("@"):
                continue
            value = line.split("\t", 1)[-1]
            mk = marker(value)
            if mk != "<none>":
                lemma_marker_lines[mk] += 1
                if len(lemma_examples) < 20:
                    lemma_examples.append(value[:180])

    payload = {
        "schema": 1,
        "filesScanned": len(files),
        "projects": dict(projects.most_common()),
        "annotationHeaderDocumentsByProject": dict(annot_event_docs.most_common()),
        "annotationHeaderEvents": dict(annot_events.most_common()),
        "wordClasses": dict(words.most_common()),
        "candidateLeadingMarkers": dict(candidate_markers.most_common()),
        "selectedCandidateLeadingMarkers": dict(selected_markers.most_common()),
        "selectedResolutionProblems": dict(selected_unresolved.most_common()),
        "documentsByMarkerCount": {k: len(v) for k, v in sorted(docs_by_marker.items())},
        "hfrDocumentClasses": dict(hfr_doc_classes.most_common()),
        "markerExamples": dict(examples),
        "shippedLemmaLeadingMarkers": dict(lemma_marker_lines.most_common()),
        "shippedLemmaExamples": lemma_examples,
        "interpretationGuard": "Leading glyphs are measured as opaque source markers; this report does not assign them annotation-stage semantics.",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
