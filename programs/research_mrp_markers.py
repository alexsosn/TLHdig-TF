#!/usr/bin/env python
"""Research-only corpus inventory for issue #92.

This deliberately over-collects leading non-lexical prefixes instead of assuming a
closed marker vocabulary. It measures source `mrpN` strings, current TF lemma/lex
identities, selector relationship, and the *hypothetical* identity effect of separating
a leading prefix from the lemma. It does not decide that every observed prefix is safe
to strip; that disposition belongs in the research/plan.

The source side is independent of the production morphology parser, but it deliberately
uses the same *document population* as conversion: committed repairs are applied, XML is
parsed strictly, and only `body/div1/text` is inspected. Raw-regex scanning the complete
file counts `<w>` material outside the converted text and is not a valid TF conservation
baseline.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re
import sys
import unicodedata

import lxml.etree as LE

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = ROOT / "programs"
sys.path.insert(0, str(PROGRAMS))

from tlhdig import TF_VERSION, repair  # noqa: E402
from tlhdig.paths import PATCHES  # noqa: E402

CORPUS = ROOT / "corpus" / "TLHdig-0.3"
EXCLUDED = PROGRAMS / "excluded.txt"

MRP_RE = re.compile(r"^mrp(\d+)$")
NUMERIC_SELECTOR_RE = re.compile(r"^(\d+)[A-Za-z]*$")

# Structural clitic-only prefixes are syntax, not annotation-generation markers.
CLITIC_ONLY_RE = re.compile(r"^\s*@?\s*(?:\+=|\+(?=@))")


def excluded_paths() -> set[str]:
    out = set()
    for raw in EXCLUDED.read_text(encoding="utf8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.add(line.split("\t", 1)[0])
    return out


def source_base_field(raw: str) -> str:
    """Extract the source base-lemma field without using the production parser."""
    if CLITIC_ONLY_RE.match(raw):
        return ""
    return raw.split("@", 1)[0].strip()


def is_ordinary_lexical_start(ch: str) -> bool:
    """A deliberately small negative definition for research discovery.

    Letters (including Hittite diacritics), decimal digits, and '+' are accepted as
    ordinary lexical starts. Everything else is surfaced as a possible prefix. This
    intentionally catches punctuation/symbol false positives for later disposition.
    """
    cat = unicodedata.category(ch)
    return cat.startswith("L") or cat == "Nd" or ch == "+"


def split_broad_prefix(field: str) -> tuple[str, str]:
    """Return (possible non-lexical prefix, remainder) without a closed glyph set."""
    s = field.lstrip()
    i = 0
    while i < len(s) and not is_ordinary_lexical_start(s[i]):
        i += 1
    if i == 0:
        return "", s
    prefix = s[:i].strip()
    return prefix, s[i:].lstrip()


def codepoints(text: str) -> list[dict[str, str]]:
    return [
        {
            "char": ch,
            "codepoint": f"U+{ord(ch):04X}",
            "name": unicodedata.name(ch, "<unnamed>"),
            "category": unicodedata.category(ch),
        }
        for ch in text
        if not ch.isspace()
    ]


def selected_indices(raw_selector: str | None) -> set[int]:
    out: set[int] = set()
    for tok in (raw_selector or "").split():
        m = NUMERIC_SELECTOR_RE.match(tok)
        if m:
            out.add(int(m.group(1)))
    return out


def selection_state(index: int, indices: set[int]) -> str:
    if not indices:
        return "no_numeric_selector"
    return "selected" if index in indices else "not_selected"


def sample_add(bucket: list, row: dict, limit: int = 8) -> None:
    if len(bucket) < limit:
        bucket.append(row)


def source_inventory() -> dict:
    excluded = excluded_paths()
    patches = repair.read_manifest(PATCHES) if PATCHES.exists() else {}
    xml_files = sorted(CORPUS.rglob("*.xml"))
    production = [p for p in xml_files if str(p.relative_to(CORPUS)) not in excluded]

    prefix_counts = Counter()
    prefix_projects: dict[str, Counter] = defaultdict(Counter)
    prefix_indices: dict[str, Counter] = defaultdict(Counter)
    prefix_selection: dict[str, Counter] = defaultdict(Counter)
    prefix_examples: dict[str, list] = defaultdict(list)
    suspicious_first = Counter()
    suspicious_examples: dict[str, list] = defaultdict(list)
    source_candidates = 0
    source_candidate_words = 0
    marker_candidates = 0
    marker_words: set[tuple[str, int]] = set()
    raw_marker_hash = sha256()
    parsed_files = 0
    repaired_files = 0
    unexpected_parse_failures: list[str] = []
    unexpected_no_text: list[str] = []

    for path in production:
        rel = str(path.relative_to(CORPUS))
        project = Path(rel).parts[0] if Path(rel).parts else ""
        data = path.read_bytes()
        entry = patches.get(rel)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
                repaired_files += 1
            except repair.PatchError as e:
                unexpected_parse_failures.append(f"{rel}: patch failed: {e}")
                continue
        try:
            root = LE.fromstring(data)
        except (LE.XMLSyntaxError, ValueError) as e:
            unexpected_parse_failures.append(f"{rel}: {type(e).__name__}: {e}")
            continue

        div1 = root.find("body/div1")
        text_el = div1.find("text") if div1 is not None else None
        if text_el is None:
            unexpected_no_text.append(rel)
            continue
        parsed_files += 1

        for word_ordinal, word in enumerate(text_el.iter("w"), start=1):
            a = word.attrib
            candidates = []
            for k, raw in a.items():
                m = MRP_RE.match(k)
                if m:
                    candidates.append((int(m.group(1)), k, raw))
            if candidates:
                source_candidate_words += 1
            sels = selected_indices(a.get("mrp0sel"))
            for index, attr_name, raw in sorted(candidates):
                source_candidates += 1
                field = source_base_field(raw)
                if field:
                    first = field[0]
                    if not is_ordinary_lexical_start(first):
                        key = f"U+{ord(first):04X} {unicodedata.name(first, '<unnamed>')}"
                        suspicious_first[key] += 1
                        sample_add(
                            suspicious_examples[key],
                            {
                                "file": rel,
                                "project": project,
                                "attribute": attr_name,
                                "mrp0sel": a.get("mrp0sel", ""),
                                "field": field,
                            },
                        )
                prefix, remainder = split_broad_prefix(field)
                if not prefix:
                    continue
                marker_candidates += 1
                marker_words.add((rel, word_ordinal))
                prefix_counts[prefix] += 1
                prefix_projects[prefix][project] += 1
                prefix_indices[prefix][str(index)] += 1
                state = selection_state(index, sels)
                prefix_selection[prefix][state] += 1
                raw_marker_hash.update(rel.encode("utf8"))
                raw_marker_hash.update(b"\0")
                raw_marker_hash.update(attr_name.encode("ascii"))
                raw_marker_hash.update(b"\0")
                raw_marker_hash.update(raw.encode("utf8"))
                raw_marker_hash.update(b"\n")
                sample_add(
                    prefix_examples[prefix],
                    {
                        "file": rel,
                        "project": project,
                        "wordOrdinal": word_ordinal,
                        "attribute": attr_name,
                        "candidateIndex": index,
                        "selectionState": state,
                        "mrp0sel": a.get("mrp0sel", ""),
                        "prefix": prefix,
                        "remainder": remainder,
                        "raw": raw,
                    },
                )

    prefixes = []
    for prefix, count in prefix_counts.most_common():
        prefixes.append(
            {
                "prefix": prefix,
                "occurrences": count,
                "codepoints": codepoints(prefix),
                "projects": dict(prefix_projects[prefix].most_common()),
                "candidateIndices": dict(prefix_indices[prefix].most_common()),
                "selectionState": dict(prefix_selection[prefix].most_common()),
                "examples": prefix_examples[prefix],
            }
        )

    return {
        "sourceXmlFiles": len(xml_files),
        "excludedXmlFiles": len(excluded),
        "productionXmlFiles": len(production),
        "parsedProductionXmlFiles": parsed_files,
        "repairedProductionXmlFiles": repaired_files,
        "unexpectedParseFailures": unexpected_parse_failures,
        "unexpectedNoText": unexpected_no_text,
        "sourceCandidateWords": source_candidate_words,
        "sourceMrpCandidates": source_candidates,
        "possiblePrefixCandidates": marker_candidates,
        "possiblePrefixWords": len(marker_words),
        "possiblePrefixes": prefixes,
        "suspiciousFirstCodepoints": dict(suspicious_first.most_common()),
        "suspiciousFirstCodepointExamples": suspicious_examples,
        "markerBearingRawDigest": f"sha256:{raw_marker_hash.hexdigest()}",
    }


def tf_inventory() -> dict:
    from tf.fabric import Fabric

    tf_dir = ROOT / "tf" / TF_VERSION
    TF = Fabric(locations=str(tf_dir), silent="deep")
    api = TF.load("otype lemma gloss raw index lexeme", silent="deep")
    if api is False or api is None:
        raise SystemExit(f"cannot load {tf_dir}")
    F, E = api.F, api.E

    analysis_nodes = list(F.otype.s("analysis"))
    lex_nodes = list(F.otype.s("lex"))
    prefix_counts = Counter()
    prefix_raw = Counter()
    examples: dict[str, list] = defaultdict(list)
    marker_analysis_nodes = []

    for n in analysis_nodes:
        lemma = F.lemma.v(n) or ""
        prefix, remainder = split_broad_prefix(lemma)
        if not prefix:
            continue
        marker_analysis_nodes.append(n)
        prefix_counts[prefix] += 1
        raw = F.raw.v(n) or ""
        prefix_raw[prefix] += bool(raw)
        sample_add(
            examples[prefix],
            {
                "node": n,
                "index": F.index.v(n),
                "lemma": lemma,
                "normalizedLemmaCandidate": remainder,
                "gloss": F.gloss.v(n) or "",
                "rawFeature": raw,
                "lexNode": (E.lexeme.f(n)[0] if E.lexeme.f(n) else None),
            },
        )

    current_keys: dict[tuple[str, str], list[int]] = defaultdict(list)
    normalized_keys: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    contaminated_lex = []
    for n in lex_nodes:
        lemma = F.lemma.v(n) or ""
        gloss = F.gloss.v(n) or ""
        current = (lemma, gloss)
        current_keys[current].append(n)
        prefix, remainder = split_broad_prefix(lemma)
        normalized = (remainder if prefix else lemma, gloss)
        normalized_keys[normalized].add(current)
        if prefix:
            contaminated_lex.append(
                {
                    "node": n,
                    "prefix": prefix,
                    "lemma": lemma,
                    "normalizedLemmaCandidate": remainder,
                    "gloss": gloss,
                }
            )

    collisions = []
    for normalized, originals in normalized_keys.items():
        if len(originals) <= 1:
            continue
        if not any(split_broad_prefix(key[0])[0] for key in originals):
            continue
        collisions.append(
            {
                "normalizedLemma": normalized[0],
                "gloss": normalized[1],
                "currentKeys": [
                    {"lemma": lemma, "gloss": gloss}
                    for lemma, gloss in sorted(originals)
                ],
            }
        )
    collisions.sort(key=lambda x: (-len(x["currentKeys"]), x["normalizedLemma"], x["gloss"]))

    return {
        "tfVersion": TF_VERSION,
        "analysisNodes": len(analysis_nodes),
        "lexNodes": len(lex_nodes),
        "possiblePrefixAnalysisAssignments": len(marker_analysis_nodes),
        "possiblePrefixAnalysisByPrefix": dict(prefix_counts.most_common()),
        "rawFeaturePresentByPrefix": dict(prefix_raw.most_common()),
        "possiblePrefixAnalysisExamples": examples,
        "possiblePrefixLexNodes": len(contaminated_lex),
        "possiblePrefixLexExamples": contaminated_lex[:50],
        "hypotheticalNormalizedLexNodeCount": len(normalized_keys),
        "hypotheticalLexNodeDelta": len(normalized_keys) - len(lex_nodes),
        "hypotheticalCollisionGroups": len(collisions),
        "hypotheticalCollisionExamples": collisions[:100],
        "warning": (
            "Hypothetical normalization removes every broadly detected prefix. "
            "These counts measure risk; they are not a decision that every prefix is non-lexical."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    source = source_inventory()
    tf = tf_inventory()
    guards = []
    if source["unexpectedParseFailures"]:
        guards.append(
            f"unexpected parse/repair failures in production population: {len(source['unexpectedParseFailures'])}"
        )
    if source["unexpectedNoText"]:
        guards.append(
            f"unexpected production documents without body/div1/text: {len(source['unexpectedNoText'])}"
        )
    if source["sourceMrpCandidates"] != tf["analysisNodes"]:
        guards.append(
            f"source/TF analysis population differs: source={source['sourceMrpCandidates']} tf={tf['analysisNodes']}"
        )
    if source["possiblePrefixCandidates"] != tf["possiblePrefixAnalysisAssignments"]:
        guards.append(
            "source/TF possible-prefix population differs: "
            f"source={source['possiblePrefixCandidates']} tf={tf['possiblePrefixAnalysisAssignments']}"
        )

    payload = {
        "schema": 2,
        "issue": 92,
        "source": source,
        "tf": tf,
        "guards": guards,
        "interpretationGuards": [
            "Source comparison uses repaired strictly parsed body/div1/text, matching conversion scope without reusing the production morphology parser.",
            "Detection is intentionally broad and not a closed list of known HFR glyphs.",
            "A detected prefix is not automatically safe to strip; every family requires a disposition.",
            "Source selection state is measured independently from annotation validation status.",
            "Current TF output is used to measure contamination/identity effects, not to prove source semantics.",
            "Any future derived normalization must keep exact mrpN recoverable through raw/source provenance.",
        ],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf8")
    else:
        print(text, end="")
    if guards:
        for g in guards:
            print(f"RESEARCH GUARD: {g}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
