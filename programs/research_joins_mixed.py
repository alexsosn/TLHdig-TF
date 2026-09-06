#!/usr/bin/env python
"""Supplement issue #18 research with mixed-content AO:Manuscripts entries.

The first census treated only child elements as manuscript entries. Manual inspection of
its two apparent leading operators showed that AO:Manuscripts can begin with a plain-text
entry such as ``KBo 10.47c {€1}``. This research-only pass measures those text entries and
recomputes operator adjacency without changing conversion behavior.
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

OPERATORS = {"DirectJoin": "direct", "InDirectJoin": "indirect"}
ENTRY = re.compile(r"(?P<label>[^{}<>\n]+?)\s*\{\s*(?P<nr>€\d+)\s*\}")
EURO = re.compile(r"€\d+")


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


def text_tokens(raw: str | None) -> tuple[list[dict], list[str]]:
    raw = raw or ""
    tokens = []
    spans = []
    for match in ENTRY.finditer(raw):
        label = " ".join(match.group("label").split())
        nr = match.group("nr")
        if label:
            tokens.append({"tag": "PlainText", "nr": nr, "text": label})
            spans.append((match.start(), match.end()))
    remainder = raw
    for start, end in reversed(spans):
        remainder = remainder[:start] + " " + remainder[end:]
    leftovers = [" ".join(remainder.split())] if remainder.strip() else []
    return tokens, leftovers


def element_token(element) -> dict:
    return {
        "tag": lname(element),
        "nr": (element.get("nr") or "").strip(),
        "text": "".join(element.itertext()).strip(),
    }


def main() -> int:
    counts = Counter()
    endpoint_pairs = Counter()
    positions = Counter()
    plain_labels_equal_docid = 0
    plain_entries = []
    leftovers = []
    anomalies = []

    for path in sorted(CORPUS.rglob("*.xml")):
        rel = path.relative_to(CORPUS).as_posix()
        counts["files"] += 1
        root, strict = parse(path.read_bytes())
        if root is None:
            counts["unrecoverable"] += 1
            continue
        if not strict:
            counts["recovered_files"] += 1
        docids = root.xpath("//*[local-name()='AOHeader']/*[local-name()='docID']/text()")
        docid = str(docids[0]).strip() if docids else Path(rel).stem
        used_sigla = {
            siglum
            for lb in root.xpath("//*[local-name()='lb']")
            for siglum in EURO.findall(lb.get("lnr") or "")
        }

        for block_index, block in enumerate(root.xpath("//*[local-name()='Manuscripts']")):
            counts["blocks"] += 1
            tokens: list[dict] = []

            initial, initial_leftovers = text_tokens(block.text)
            for token in initial:
                token["lineReferenced"] = token["nr"] in used_sigla
                tokens.append(token)
                plain_entries.append({"src_file": rel, "docid": docid, **token})
                counts["plain_entries"] += 1
                if token["text"] == docid.rstrip("+") or token["text"] == docid:
                    plain_labels_equal_docid += 1
            for value in initial_leftovers:
                leftovers.append({"src_file": rel, "block": block_index, "where": "block.text", "text": value})

            for child in block:
                if not isinstance(child.tag, str):
                    continue
                name = lname(child)
                if name in OPERATORS:
                    tokens.append({"tag": name, "kind": OPERATORS[name]})
                else:
                    token = element_token(child)
                    token["lineReferenced"] = bool(token["nr"] and token["nr"] in used_sigla)
                    tokens.append(token)

                tail, tail_leftovers = text_tokens(child.tail)
                for token in tail:
                    token["lineReferenced"] = token["nr"] in used_sigla
                    tokens.append(token)
                    plain_entries.append({"src_file": rel, "docid": docid, **token})
                    counts["plain_entries"] += 1
                    if token["text"] == docid.rstrip("+") or token["text"] == docid:
                        plain_labels_equal_docid += 1
                for value in tail_leftovers:
                    leftovers.append({"src_file": rel, "block": block_index, "where": f"tail:{name}", "text": value})

            for index, token in enumerate(tokens):
                if token.get("kind") not in {"direct", "indirect"}:
                    continue
                counts[f"{token['kind']}_operators"] += 1
                left = tokens[index - 1] if index else None
                right = tokens[index + 1] if index + 1 < len(tokens) else None
                left_is_op = bool(left and left.get("kind"))
                right_is_op = bool(right and right.get("kind"))
                if left is None:
                    position = "leading"
                elif right is None:
                    position = "trailing"
                elif left_is_op or right_is_op:
                    position = "consecutive-operator"
                else:
                    position = "between-entries"
                positions[f"{token['kind']}:{position}"] += 1
                left_tag = left.get("tag", "") if left else "<START>"
                right_tag = right.get("tag", "") if right else "<END>"
                endpoint_pairs[f"{token['kind']}:{left_tag}->{right_tag}"] += 1
                if position != "between-entries":
                    anomalies.append(
                        {
                            "src_file": rel,
                            "docid": docid,
                            "block": block_index,
                            "kind": token["kind"],
                            "position": position,
                            "left": left,
                            "right": right,
                        }
                    )

    counts["operators_total"] = counts["direct_operators"] + counts["indirect_operators"]
    counts["plain_labels_equal_docid"] = plain_labels_equal_docid
    counts["plain_entries_line_referenced"] = sum(bool(row.get("lineReferenced")) for row in plain_entries)
    counts["nonwhitespace_unparsed_text_chunks"] = len(leftovers)
    counts["adjacency_anomalies"] = len(anomalies)

    payload = {
        "schema": 1,
        "issue": 18,
        "corpus": str(CORPUS.relative_to(ROOT)),
        "summary": dict(sorted(counts.items())),
        "operatorPositions": dict(positions.most_common()),
        "endpointTypePairs": dict(endpoint_pairs.most_common()),
        "plainEntries": plain_entries,
        "unparsedTextChunks": leftovers,
        "adjacencyAnomalies": anomalies,
    }
    REPORTS.mkdir(exist_ok=True)
    json_path = REPORTS / "joins-mixed-research.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf8")

    lines = [
        "# Mixed-content manuscript join census",
        "",
        "Research-only supplement for issue #18. It treats `label {€n}` text inside",
        "`AO:Manuscripts` as an explicit manuscript entry and recomputes join adjacency.",
        "",
        "## Summary",
        "",
        "| metric | count |",
        "|---|---:|",
    ]
    for key, value in sorted(counts.items()):
        lines.append(f"| `{key}` | {value:,} |")
    lines += ["", "## Operator positions", "", "| shape | count |", "|---|---:|"]
    for key, value in positions.most_common():
        lines.append(f"| `{key}` | {value:,} |")
    lines += ["", "## Endpoint type pairs", "", "| shape | count |", "|---|---:|"]
    for key, value in endpoint_pairs.most_common():
        lines.append(f"| `{key}` | {value:,} |")
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "This pass only identifies the mixed-content grammar. It does not assert that",
        "direct/indirect joins are directed, symmetric or transitive, and it does not",
        "resolve inventory/publication labels across documents.",
        "",
    ]
    md_path = REPORTS / "joins-mixed-research.md"
    md_path.write_text("\n".join(lines), encoding="utf8")
    print(md_path.read_text(encoding="utf8"))
    print(f"machine-readable inventory: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
