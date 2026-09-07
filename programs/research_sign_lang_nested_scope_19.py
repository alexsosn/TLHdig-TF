#!/usr/bin/env python
"""Research-only comparison of malformed nested language boundaries for issue #19.

The production converter walks every descendant of <text>, so an <lb>/<clb> nested
inside malformed <w> markup currently mutates structural line/colon state.  This audit
compares that behavior with a source-grammar model in which only boundaries outside
<w> are structural, while reproducing the converter's colon lifetime at column changes.
It does not change production behavior.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from xml.parsers import expat

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import lineref, repair, signs, source
from tlhdig.paths import ENCRYPTED, PATCHES, ROOT, corpus_files, rel

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
OUT = ROOT / "reports" / "research-sign-lang-nested-scope-19.json"


def lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else ""


def positive(raw: str | None) -> str:
    if raw is None:
        return ""
    value = raw.strip()
    return value if value and value != "XXXlang" else ""


def choose(word_raw: str | None, state: "Scope", text_raw: str | None) -> tuple[str, str]:
    for level, raw in (
        ("word", word_raw),
        ("colon", state.colon_raw),
        ("line", state.line_raw),
        ("text", text_raw),
    ):
        value = positive(raw)
        if value:
            return level, value
    return "absent", ""


def token_sign_count(data: bytes, span) -> int:
    inner = source.inner_bytes(data, span)
    return sum(1 for token in signs.tokenise_word(inner) if token.type != "empty")


@dataclass
class Scope:
    line_raw: str | None = None
    colon_raw: str | None = None
    collabel: str | None = None
    have_line: bool = False

    def line_event(self, node) -> None:
        ref = lineref.parse(node.get("lnr"))
        if ref.collabel != self.collabel:
            # Mirrors _State.start_line(): changing column closes the active colon.
            self.colon_raw = None
            self.collabel = ref.collabel
        self.line_raw = node.get("lg") if "lg" in node.attrib else None
        self.have_line = True

    def colon_event(self, node) -> None:
        # Mirrors _State.start_colon(): every new clb closes/replaces the previous one,
        # including a clb with no positive lg.
        self.colon_raw = node.get("lg") if "lg" in node.attrib else None


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}
    counts = Counter()
    diff = Counter()
    source_levels = Counter()
    production_levels = Counter()
    samples: list[str] = []
    prod_only_line_samples: list[str] = []

    for path in corpus_files():
        src_file = rel(path)
        counts["files"] += 1
        if src_file == ENCRYPTED:
            counts["excluded_encrypted"] += 1
            continue
        data = path.read_bytes()
        entry = patches.get(src_file)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
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
        text_raw = text.get(XML_LANG)

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
            if not any(lname(a) == "w" for a in node.iterancestors())
        ]
        if len(top_words) != len(w_spans):
            counts["word_span_pairing_mismatch_docs"] += 1
            continue
        span_for = {id(node): sp for node, sp in zip(top_words, w_spans)}

        prod = Scope()
        faithful = Scope()
        word_index = 0

        for node in text.iter():
            if not isinstance(node.tag, str):
                continue
            tag = lname(node)
            nested_in_word = any(lname(a) == "w" for a in node.iterancestors())

            if tag == "lb":
                prod.line_event(node)
                counts["all_lb_events"] += 1
                if nested_in_word:
                    counts["nested_lb_events"] += 1
                else:
                    faithful.line_event(node)
                    counts["structural_lb_events"] += 1
                continue

            if tag == "clb":
                prod.colon_event(node)
                counts["all_clb_events"] += 1
                if nested_in_word:
                    counts["nested_clb_events"] += 1
                else:
                    faithful.colon_event(node)
                    counts["structural_clb_events"] += 1
                continue

            if tag != "w" or id(node) not in span_for:
                continue

            word_index += 1
            nsigns = token_sign_count(data, span_for[id(node)])
            if not prod.have_line:
                counts["source_signs_before_production_line"] += nsigns
                continue

            counts["tf_source_sign_population"] += nsigns
            if not faithful.have_line:
                counts["signs_after_nested_only_line_before_structural_line"] += nsigns
                if nsigns and len(prod_only_line_samples) < 50:
                    prod_only_line_samples.append(f"{src_file} word#{word_index}: {nsigns} signs")

            word_raw = node.get("lg") if "lg" in node.attrib else None
            pchoice = choose(word_raw, prod, text_raw)
            fchoice = choose(word_raw, faithful, text_raw)
            production_levels[pchoice] += nsigns
            source_levels[fchoice] += nsigns
            if pchoice != fchoice:
                diff[(pchoice, fchoice)] += nsigns
                counts["signs_with_language_choice_difference"] += nsigns
                if nsigns and len(samples) < 100:
                    samples.append(
                        f"{src_file} word#{word_index}: prod={pchoice!r} faithful={fchoice!r}; "
                        f"prod(line={prod.line_raw!r}, colon={prod.colon_raw!r}, col={prod.collabel!r}); "
                        f"faithful(line={faithful.line_raw!r}, colon={faithful.colon_raw!r}, col={faithful.collabel!r})"
                    )

    payload = {
        "counts": dict(sorted(counts.items())),
        "production_like_effective_signs": [
            {"level": level, "raw": raw, "signs": n}
            for (level, raw), n in sorted(production_levels.items(), key=lambda x: (-x[1], x[0]))
        ],
        "source_grammar_effective_signs": [
            {"level": level, "raw": raw, "signs": n}
            for (level, raw), n in sorted(source_levels.items(), key=lambda x: (-x[1], x[0]))
        ],
        "differences": [
            {
                "production": list(prod_choice),
                "source_grammar": list(faithful_choice),
                "signs": n,
            }
            for (prod_choice, faithful_choice), n in sorted(diff.items(), key=lambda x: (-x[1], x[0]))
        ],
        "samples": samples,
        "nested_only_line_samples": prod_only_line_samples,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf8")

    print("ISSUE 19 NESTED-BOUNDARY / COLUMN-SCOPE RESEARCH")
    for key in sorted(counts):
        print(f"{key}={counts[key]}")
    print("\nSOURCE-GRAMMAR LEVEL TOTALS")
    levels = Counter()
    for (level, _raw), n in source_levels.items():
        levels[level] += n
    for level, n in levels.most_common():
        print(f"{level}={n}")
    print("\nTOP DIFFERENCES")
    for row in payload["differences"][:30]:
        print(f"prod={row['production']} source={row['source_grammar']} signs={row['signs']}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
