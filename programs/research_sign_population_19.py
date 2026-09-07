#!/usr/bin/env python
"""Research-only reconciliation of source-token and TF sign populations for issue #19."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from xml.parsers import expat

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, compact, repair, signs, source
from tlhdig.paths import ENCRYPTED, PATCHES, ROOT, corpus_files, rel


def lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else ""


def token_sign_count(data: bytes, span) -> int:
    inner = source.inner_bytes(data, span)
    return sum(1 for token in signs.tokenise_word(inner) if token.type != "empty")


def main() -> int:
    stats = Counter()
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}

    for path in corpus_files():
        src_file = rel(path)
        if src_file == ENCRYPTED:
            stats["excluded_encrypted"] += 1
            continue
        data = path.read_bytes()
        entry = patches.get(src_file)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError:
                stats["excluded_patch_error"] += 1
                continue
        try:
            spans = source.scan(data)
            root = ET.fromstring(data)
        except (expat.ExpatError, ET.XMLSyntaxError, ValueError):
            stats["excluded_unparseable"] += 1
            continue
        div1 = root.find("body/div1")
        text = div1.find("text") if div1 is not None else None
        if text is None:
            stats["excluded_no_text"] += 1
            continue
        stats["production_documents"] += 1

        text_span = next(
            (sp for sp in spans if sp.tag == "text" and sp.inner_start is not None), None
        )
        w_all = [sp for sp in spans if sp.tag == "w"]
        if text_span is not None:
            w_all = [
                sp for sp in w_all
                if text_span.inner_start <= sp.outer_start < text_span.inner_end
            ]
        w_spans = []
        for sp in w_all:
            if any(
                other is not sp
                and other.outer_start <= sp.outer_start
                and sp.outer_end <= other.outer_end
                for other in w_all
            ):
                continue
            w_spans.append(sp)

        top_words = [
            node for node in text.iter("w")
            if not any(lname(ancestor) == "w" for ancestor in node.iterancestors())
        ]
        if len(top_words) != len(w_spans):
            stats["word_span_pairing_mismatch_docs"] += 1
            continue

        have_line = False
        span_for = {id(node): sp for node, sp in zip(top_words, w_spans)}
        for node in text.iter():
            if not isinstance(node.tag, str):
                continue
            tag = lname(node)
            if tag == "lb":
                have_line = True
                continue
            if tag != "w" or id(node) not in span_for:
                continue
            n = token_sign_count(data, span_for[id(node)])
            if have_line:
                stats["convertible_source_signs"] += n
            else:
                stats["source_signs_before_first_lb"] += n

    tf = ROOT / "tf" / TF_VERSION
    otype = compact.read_values(tf / "otype.tf")
    anchors = compact.read_values(tf / "anchor.tf")
    stats["tf_sign_slots"] = sum(1 for value in otype.values() if value == "sign")
    stats["tf_anchor_sign_slots"] = sum(
        1 for node, value in anchors.items() if value == "1" and otype.get(node) == "sign"
    )
    stats["tf_source_sign_slots"] = stats["tf_sign_slots"] - stats["tf_anchor_sign_slots"]
    stats["delta_tf_source_vs_source_scan"] = (
        stats["tf_source_sign_slots"] - stats["convertible_source_signs"]
    )

    print("ISSUE 19 SIGN POPULATION RECONCILIATION")
    for key in sorted(stats):
        print(f"{key}={stats[key]}")

    # The production converter does not slot words before the first lb. Synthetic
    # anchors are technical TF slots, not source signs. Once both populations are
    # excluded, the source tokenizer and shipped TF must agree exactly.
    return 0 if stats["delta_tf_source_vs_source_scan"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
