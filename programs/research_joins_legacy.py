#!/usr/bin/env python
"""Research-only census of legacy textual separators in AO:Manuscripts.

Issue #18 started from AO:DirectJoin/AO:InDirectJoin, but corpus inspection shows an
older mixed-content grammar where an entry element is followed by text such as
``{€2} +`` or ``{€2} (+)``.  This pass reconstructs that syntax without assigning
philological semantics beyond the literal source notation.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig.paths import CORPUS, REPORTS, ROOT

ENTRY_TAGS = {"TxtPubl", "TextPubl", "InvNr"}
XML_SEPARATORS = {"DirectJoin": "xml-direct", "InDirectJoin": "xml-indirect"}
PLAIN_ENTRY = re.compile(r"(?P<label>[^{}<>\n]+?)\s*\{\s*(?P<nr>€\d+)\s*\}")
EURO = re.compile(r"\{\s*(?P<nr>€\d+)\s*\}")
INDIRECT = re.compile(r"^\s*\(\s*\+\s*\)\s*$")
DIRECT = re.compile(r"^\s*\+\s*$")


def lname(element) -> str:
    tag = element.tag
    return ET.QName(tag).localname if isinstance(tag, str) else ""


def parse(data: bytes):
    for recover in (False, True):
        try:
            root = ET.fromstring(
                data,
                parser=ET.XMLParser(recover=recover, huge_tree=True, resolve_entities=False),
            )
        except ET.XMLSyntaxError:
            continue
        if root is not None:
            return root, not recover
    return None, False


def normalized(raw: str | None) -> str:
    return " ".join((raw or "").split())


def plain_tokens(raw: str | None) -> tuple[list[dict], str]:
    """Extract explicit ``label {€n}`` entries, returning residual text."""
    raw = raw or ""
    entries = []
    spans = []
    for match in PLAIN_ENTRY.finditer(raw):
        label = normalized(match.group("label"))
        if label:
            entries.append({"type": "entry", "tag": "PlainText", "text": label, "nr": match.group("nr")})
            spans.append((match.start(), match.end()))
    remainder = raw
    for start, end in reversed(spans):
        remainder = remainder[:start] + " " + remainder[end:]
    return entries, normalized(remainder)


def tail_parts(raw: str | None) -> tuple[str, str, str]:
    """Return (siglum, separator-kind, unclassified-residual) for an entry tail."""
    text = normalized(raw)
    if not text:
        return "", "", ""
    sigla = EURO.findall(text)
    siglum = sigla[0] if len(sigla) == 1 else ""
    remainder = EURO.sub(" ", text)
    remainder = normalized(remainder)
    if DIRECT.fullmatch(remainder):
        return siglum, "text-plus", ""
    if INDIRECT.fullmatch(remainder):
        return siglum, "text-parenthesized-plus", ""
    if not remainder:
        return siglum, "", ""
    return siglum, "", remainder


def main() -> int:
    counts = Counter()
    separator_positions = Counter()
    endpoint_pairs = Counter()
    residuals = Counter()
    records = []

    for path in sorted(CORPUS.rglob("*.xml")):
        counts["files"] += 1
        rel = path.relative_to(CORPUS).as_posix()
        root, strict = parse(path.read_bytes())
        if root is None:
            counts["unrecoverable"] += 1
            continue
        if not strict:
            counts["recovered_files"] += 1
        docids = root.xpath("//*[local-name()='AOHeader']/*[local-name()='docID']/text()")
        docid = str(docids[0]).strip() if docids else Path(rel).stem

        for block_index, block in enumerate(root.xpath("//*[local-name()='Manuscripts']")):
            counts["blocks"] += 1
            tokens: list[dict] = []
            initial, initial_residual = plain_tokens(block.text)
            tokens.extend(initial)
            counts["plain_text_entries"] += len(initial)
            if initial_residual:
                residuals[f"block.text:{initial_residual}"] += 1

            for child in block:
                if not isinstance(child.tag, str):
                    continue
                name = lname(child)
                if name in XML_SEPARATORS:
                    tokens.append({"type": "separator", "kind": XML_SEPARATORS[name], "raw": name})
                    counts[XML_SEPARATORS[name]] += 1
                    # An XML separator may itself have only whitespace tail; process
                    # non-whitespace below as a possible legacy suffix/anomaly.
                    tail_siglum, tail_kind, tail_residual = tail_parts(child.tail)
                    if tail_siglum:
                        residuals[f"separator-tail-siglum:{tail_siglum}"] += 1
                    if tail_kind:
                        tokens.append({"type": "separator", "kind": tail_kind, "raw": normalized(child.tail)})
                        counts[tail_kind] += 1
                    if tail_residual:
                        residuals[f"tail:{name}:{tail_residual}"] += 1
                    continue

                if name in ENTRY_TAGS:
                    entry = {
                        "type": "entry",
                        "tag": name,
                        "text": normalized("".join(child.itertext())),
                        "nr": normalized(child.get("nr")),
                    }
                    siglum, sep_kind, tail_residual = tail_parts(child.tail)
                    if not entry["nr"] and siglum:
                        entry["nr"] = siglum
                        counts["tail_sigla_attached_to_entry"] += 1
                    elif entry["nr"] and siglum:
                        if entry["nr"] == siglum:
                            counts["redundant_matching_tail_siglum"] += 1
                        else:
                            counts["conflicting_attribute_tail_siglum"] += 1
                    tokens.append(entry)
                    counts[f"entry:{name}"] += 1
                    if sep_kind:
                        tokens.append({"type": "separator", "kind": sep_kind, "raw": normalized(child.tail)})
                        counts[sep_kind] += 1
                    if tail_residual:
                        residuals[f"tail:{name}:{tail_residual}"] += 1
                    continue

                # Non-entry children are outside the proposed relation model, but their
                # tails are still measured so hidden separators cannot disappear.
                _siglum, sep_kind, tail_residual = tail_parts(child.tail)
                if sep_kind:
                    tokens.append({"type": "separator", "kind": sep_kind, "raw": normalized(child.tail)})
                    counts[sep_kind] += 1
                    counts["separator_after_nonentry_child"] += 1
                if tail_residual:
                    residuals[f"tail:{name}:{tail_residual}"] += 1

            for index, token in enumerate(tokens):
                if token.get("type") != "separator":
                    continue
                left = tokens[index - 1] if index else None
                right = tokens[index + 1] if index + 1 < len(tokens) else None
                if left and right and left.get("type") == right.get("type") == "entry":
                    position = "between-entries"
                elif left is None:
                    position = "leading"
                elif right is None:
                    position = "trailing"
                else:
                    position = "non-entry-adjacency"
                key = f"{token['kind']}:{position}"
                separator_positions[key] += 1
                left_tag = left.get("tag", left.get("type")) if left else "<START>"
                right_tag = right.get("tag", right.get("type")) if right else "<END>"
                endpoint_pairs[f"{token['kind']}:{left_tag}->{right_tag}"] += 1
                records.append(
                    {
                        "src_file": rel,
                        "docid": docid,
                        "block": block_index,
                        "kind": token["kind"],
                        "raw": token.get("raw", ""),
                        "position": position,
                        "left": left,
                        "right": right,
                    }
                )

    counts["separators_total"] = sum(
        counts[k]
        for k in ("xml-direct", "xml-indirect", "text-plus", "text-parenthesized-plus")
    )
    counts["residual_text_shapes"] = len(residuals)
    counts["residual_text_occurrences"] = sum(residuals.values())

    payload = {
        "schema": 1,
        "issue": 18,
        "corpus": str(CORPUS.relative_to(ROOT)),
        "summary": dict(sorted(counts.items())),
        "separatorPositions": dict(separator_positions.most_common()),
        "endpointTypePairs": dict(endpoint_pairs.most_common()),
        "residualText": dict(residuals.most_common()),
        "relations": records,
    }
    REPORTS.mkdir(exist_ok=True)
    jp = REPORTS / "joins-legacy-research.json"
    jp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf8")

    lines = [
        "# Legacy textual manuscript-join notation census",
        "",
        "Research-only supplement for issue #18. `text-plus` and",
        "`text-parenthesized-plus` are literal source notations; this report does not",
        "yet equate them semantically with XML `DirectJoin` / `InDirectJoin`.",
        "",
        "## Summary",
        "",
        "| metric | count |",
        "|---|---:|",
    ]
    for key, value in sorted(counts.items()):
        lines.append(f"| `{key}` | {value:,} |")
    lines += ["", "## Separator positions", "", "| shape | count |", "|---|---:|"]
    for key, value in separator_positions.most_common():
        lines.append(f"| `{key}` | {value:,} |")
    lines += ["", "## Endpoint type pairs", "", "| shape | count |", "|---|---:|"]
    for key, value in endpoint_pairs.most_common():
        lines.append(f"| `{key}` | {value:,} |")
    lines += ["", "## Most common residual text", "", "| shape | count |", "|---|---:|"]
    for key, value in residuals.most_common(30):
        safe = key.replace("|", "\\|")
        lines.append(f"| `{safe}` | {value:,} |")
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "This census establishes serialization shapes and adjacency only. It does not",
        "assert direction, symmetry, transitivity, or equivalence between textual and",
        "element-based separators. Those are design decisions only after the evidence",
        "is reviewed.",
        "",
    ]
    mp = REPORTS / "joins-legacy-research.md"
    mp.write_text("\n".join(lines), encoding="utf8")
    print(mp.read_text(encoding="utf8"))
    print(f"machine-readable inventory: {jp} ({len(records):,} separators)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
