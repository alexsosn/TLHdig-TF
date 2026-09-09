#!/usr/bin/env python
"""Research-only census for issue #79: annotation-stage evidence in shipped TLHdig XML.

This script deliberately does *not* turn selector state into a validation-status feature.
It measures only source facts needed to decide whether that inference would be justified:
which mrp0sel states occur in the production XML population, where annotation history
lives, and which selector classes are already preserved by TF 0.4.0.

Opaque leading glyphs inside mrpN values are a separate morphology/source-fidelity
problem tracked by #92 and are intentionally not interpreted here.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "TLHdig-0.3"
EXCLUDED = ROOT / "programs" / "excluded.txt"
TF = ROOT / "tf" / "0.4.0"

WORD_RE = re.compile(r"<w\b([^>]*)>")
ANNOT_RE = re.compile(r"<annot\b([^>]*)/?>")
ATTR_RE = re.compile(r"([:\w.-]+)\s*=\s*([\"'])(.*?)\2", re.S)
MRP_RE = re.compile(r"^mrp(\d+)$")
DOCID_RE = re.compile(r"<docID>(.*?)</docID>", re.S)
NUMERIC_TOKEN_RE = re.compile(r"^\d+[A-Za-z]*$")
SPECIAL = frozenset({"DEL", "AKK", "HURR", "HAT", "SUM", "LUW"})


def attrs(raw: str) -> dict[str, str]:
    return {m.group(1): m.group(3) for m in ATTR_RE.finditer(raw)}


def excluded_paths() -> set[str]:
    out = set()
    for raw in EXCLUDED.read_text(encoding="utf8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line.split("\t", 1)[0])
    return out


def project(rel: Path) -> str:
    return rel.parts[0] if rel.parts else ""


def selector_class(value: str | None) -> str:
    if value is None or not value.strip():
        return "empty"
    toks = value.split()
    if "???" in toks:
        return "unknown"
    specials = [t for t in toks if t in SPECIAL]
    numerics = [t for t in toks if NUMERIC_TOKEN_RE.match(t)]
    if numerics and specials:
        return "special+numeric"
    if numerics:
        return "numeric"
    if specials:
        return "special:" + "+".join(sorted(set(specials)))
    return "other"


def feature_value_counts(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not path.is_file():
        return counts
    for line in path.read_text(encoding="utf8", errors="replace").splitlines():
        if not line or line.startswith("@"):
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            counts[parts[1]] += 1
    return counts


def main() -> int:
    xml_files = sorted(CORPUS.rglob("*.xml"))
    excluded = excluded_paths()
    production = [p for p in xml_files if str(p.relative_to(CORPUS)) not in excluded]

    projects = Counter()
    hfr_projects = Counter()
    selector_words = Counter()
    hfr_selector_words = Counter()
    selector_docs = Counter()
    hfr_selector_docs = Counter()
    header_annot_docs = Counter()
    hfr_header_annot_docs = Counter()
    header_events = Counter()
    hfr_header_events = Counter()
    candidate_counts = Counter()
    hfr_candidate_counts = Counter()
    examples: dict[str, list[dict[str, str]]] = {}

    for path in production:
        text = path.read_text(encoding="utf8", errors="replace")
        rel = path.relative_to(CORPUS)
        proj = project(rel)
        is_hfr = proj.endswith("_XML_HFR")
        projects[proj] += 1
        if is_hfr:
            hfr_projects[proj] += 1
        dm = DOCID_RE.search(text)
        docid = dm.group(1).strip() if dm else path.stem

        events = [attrs(m.group(1)) for m in ANNOT_RE.finditer(text)]
        if events:
            header_annot_docs["with_annot_event"] += 1
            if is_hfr:
                hfr_header_annot_docs["with_annot_event"] += 1
        else:
            header_annot_docs["without_annot_event"] += 1
            if is_hfr:
                hfr_header_annot_docs["without_annot_event"] += 1
        for e in events:
            key = f"editor={e.get('editor','')}|date={bool(e.get('date'))}|data={bool(e.get('data'))}"
            header_events[key] += 1
            if is_hfr:
                hfr_header_events[key] += 1

        doc_classes = set()
        for wm in WORD_RE.finditer(text):
            a = attrs(wm.group(1))
            mrps = [k for k in a if MRP_RE.match(k)]
            cls = selector_class(a.get("mrp0sel"))
            selector_words[cls] += 1
            doc_classes.add(cls)
            candidate_counts["words_with_mrp_candidates" if mrps else "words_without_mrp_candidates"] += 1
            if is_hfr:
                hfr_selector_words[cls] += 1
                hfr_candidate_counts["words_with_mrp_candidates" if mrps else "words_without_mrp_candidates"] += 1
            bucket = examples.setdefault(cls, [])
            if len(bucket) < 5:
                bucket.append({
                    "file": str(rel),
                    "docid": docid,
                    "mrp0sel": a.get("mrp0sel", "<missing>"),
                    "candidateCount": str(len(mrps)),
                })

        for cls in doc_classes:
            selector_docs[cls] += 1
            if is_hfr:
                hfr_selector_docs[cls] += 1

    payload = {
        "schema": 2,
        "sourceXmlFiles": len(xml_files),
        "excludedXmlFiles": len(excluded),
        "productionXmlFiles": len(production),
        "productionProjects": dict(projects.most_common()),
        "hfrProductionXmlFiles": sum(hfr_projects.values()),
        "selectorWordClasses": dict(selector_words.most_common()),
        "hfrSelectorWordClasses": dict(hfr_selector_words.most_common()),
        "selectorDocumentClasses": dict(selector_docs.most_common()),
        "hfrSelectorDocumentClasses": dict(hfr_selector_docs.most_common()),
        "candidatePresence": dict(candidate_counts.most_common()),
        "hfrCandidatePresence": dict(hfr_candidate_counts.most_common()),
        "headerAnnotationDocuments": dict(header_annot_docs.most_common()),
        "hfrHeaderAnnotationDocuments": dict(hfr_header_annot_docs.most_common()),
        "headerAnnotationEvents": dict(header_events.most_common()),
        "hfrHeaderAnnotationEvents": dict(hfr_header_events.most_common()),
        "tf04MrpselKindValues": dict(feature_value_counts(TF / "mrpsel_kind.tf").most_common()),
        "selectorExamples": examples,
        "interpretationGuards": [
            "mrp0sel is measured as a source disambiguation selector; this report does not rename it validation status.",
            "Header annot events are document edit history and are not assumed to be word-level validation state.",
            "Opaque mrpN leading markers are out of scope here and tracked by issue #92.",
            "Excluded source files are not used to infer the semantics of the shipped TF population.",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
