#!/usr/bin/env python
"""Research-only barrier audit for issue #19 sign-level language propagation.

This deliberately contrasts two source-derived policies after the broader scope scan:
(1) skip empty/XXXlang declarations and inherit an outer positive label, versus
(2) treat the nearest explicit empty/XXXlang declaration as a scope barrier.
No production semantics are changed here.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
from xml.parsers import expat

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import repair, signs, source
from tlhdig.paths import ENCRYPTED, PATCHES, ROOT, corpus_files, rel

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
OUT = ROOT / "reports" / "research-sign-lang-barriers-19.json"


def lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else ""


def clean(value: str | None) -> str:
    return "" if value is None else value.strip()


def sign_count(data: bytes, span) -> int:
    inner = source.inner_bytes(data, span)
    return sum(1 for token in signs.tokenise_word(inner) if token.type != "empty")


def skip_unknown(levels: list[tuple[str, str | None]]) -> tuple[str, str]:
    """Existing research model: inherit past empty and XXXlang declarations."""
    for level, raw in levels:
        value = clean(raw)
        if value and value != "XXXlang":
            return level, value
    return "absent", ""


def barrier(levels: list[tuple[str, str | None]]) -> tuple[str, str, str]:
    """Nearest explicit declaration wins; empty/XXXlang stop inheritance."""
    for level, raw in levels:
        if raw is None:
            continue
        value = clean(raw)
        if value == "":
            return "empty", level, ""
        if value == "XXXlang":
            return "unknown", level, value
        return "positive", level, value
    return "absent", "absent", ""


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}
    counts = Counter()
    outcomes = Counter()
    differences = Counter()
    samples: dict[str, list[str]] = {
        "empty_barrier": [],
        "unknown_barrier": [],
        "absent": [],
        "suppressed_outer_positive": [],
    }

    for path in corpus_files():
        src_file = rel(path)
        counts["files"] += 1
        if src_file == ENCRYPTED:
            counts["excluded_encrypted"] += 1
            continue

        data = path.read_bytes()
        patch_entry = patches.get(src_file)
        if patch_entry:
            try:
                data = repair.apply(data, patch_entry[1], expect_sha=patch_entry[0])
            except repair.PatchError:
                counts["excluded_patch_error"] += 1
                continue

        try:
            spans = source.scan(data)
            root = ET.fromstring(data)
        except (expat.ExpatError, ET.XMLSyntaxError, ValueError):
            counts["excluded_unparseable"] += 1
            continue

        div1 = root.find("body/div1")
        text = div1.find("text") if div1 is not None else None
        if text is None:
            counts["excluded_no_text"] += 1
            continue
        counts["production_documents"] += 1

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
            counts["word_span_pairing_mismatch_docs"] += 1
            continue
        span_for = {id(node): sp for node, sp in zip(top_words, w_spans)}

        text_raw = text.get(XML_LANG)
        active_line: str | None = None
        active_colon: str | None = None
        have_line = False
        line_no = 0
        word_no = 0

        for node in text.iter():
            if not isinstance(node.tag, str):
                continue
            tag = lname(node)
            if tag == "lb":
                have_line = True
                line_no += 1
                active_line = node.get("lg") if "lg" in node.attrib else None
                continue
            if tag == "clb":
                active_colon = node.get("lg") if "lg" in node.attrib else None
                continue
            if tag != "w" or id(node) not in span_for:
                continue

            word_no += 1
            nsigns = sign_count(data, span_for[id(node)])
            if not have_line:
                counts["signs_before_first_lb"] += nsigns
                continue

            counts["convertible_source_signs"] += nsigns
            levels = [
                ("word", node.get("lg") if "lg" in node.attrib else None),
                ("colon", active_colon),
                ("line", active_line),
                ("text", text_raw),
            ]
            status, level, raw = barrier(levels)
            outcomes[(status, level, raw)] += nsigns

            fallback_level, fallback_raw = skip_unknown(levels)
            barrier_choice = (level, raw) if status == "positive" else ("absent", "")
            fallback_choice = (fallback_level, fallback_raw)
            if barrier_choice != fallback_choice:
                differences[(status, level, raw, fallback_level, fallback_raw)] += nsigns
                if fallback_raw:
                    counts["signs_where_barrier_suppresses_outer_positive"] += nsigns
                    bucket = samples["suppressed_outer_positive"]
                    if len(bucket) < 50:
                        bucket.append(
                            f"{src_file} line#{line_no} word#{word_no}: "
                            f"barrier={status}@{level}:{raw!r}; "
                            f"fallback={fallback_level}:{fallback_raw!r}"
                        )

            if status == "positive":
                counts["positive_signs"] += nsigns
            elif status == "empty":
                counts["empty_barrier_signs"] += nsigns
                if nsigns and len(samples["empty_barrier"]) < 50:
                    samples["empty_barrier"].append(
                        f"{src_file} line#{line_no} word#{word_no}: empty@{level}; "
                        f"outer={fallback_level}:{fallback_raw!r}"
                    )
            elif status == "unknown":
                counts["unknown_barrier_signs"] += nsigns
                if nsigns and len(samples["unknown_barrier"]) < 50:
                    samples["unknown_barrier"].append(
                        f"{src_file} line#{line_no} word#{word_no}: XXXlang@{level}"
                    )
            else:
                counts["absent_signs"] += nsigns
                if nsigns and len(samples["absent"]) < 50:
                    samples["absent"].append(
                        f"{src_file} line#{line_no} word#{word_no}: no declaration"
                    )

    payload = {
        "counts": dict(sorted(counts.items())),
        "barrier_outcomes": [
            {"status": s, "level": level, "raw": raw, "signs": n}
            for (s, level, raw), n in sorted(
                outcomes.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "differences_from_skip_unknown": [
            {
                "barrier_status": s,
                "barrier_level": level,
                "barrier_raw": raw,
                "fallback_level": fl,
                "fallback_raw": fr,
                "signs": n,
            }
            for (s, level, raw, fl, fr), n in sorted(
                differences.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "samples": samples,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf8")

    print("ISSUE 19 EMPTY/UNKNOWN BARRIER RESEARCH")
    for key in sorted(counts):
        print(f"{key}={counts[key]}")
    print("\nTOP BARRIER OUTCOMES")
    for row in payload["barrier_outcomes"][:30]:
        print(f"{row['status']} {row['level']} {row['raw']!r}: {row['signs']}")
    print("\nDIFFERENCES FROM SKIP-UNKNOWN MODEL")
    for row in payload["differences_from_skip_unknown"][:30]:
        print(
            f"{row['barrier_status']}@{row['barrier_level']} -> "
            f"{row['fallback_level']}:{row['fallback_raw']!r}: {row['signs']}"
        )
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
