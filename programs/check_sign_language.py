#!/usr/bin/env python
"""Independently verify source-declared effective language on every shipped sign.

The source-side scope reconstruction deliberately does not import converter language
state or a propagation helper. It reparses the pinned repaired corpus, reconstructs
word/colon/line/text precedence, and compares the exact per-document ordered non-anchor
sign sequence with the shipped Text-Fabric graph.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys
import re
from xml.parsers import expat

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import SOURCE_VERSION, TF_VERSION, lineref, repair, signs, source, sourcepath
from tlhdig.paths import ENCRYPTED, PATCHES, REPORTS, ROOT, corpus_files, rel

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
TARGET_DOCUMENTS = 23_884
# #52 adds the 22 readable signs that source research found before the first <lb>.
TARGET_SOURCE_SIGNS = 3_365_151
TARGET_PRELINE_SIGNS = 22
# The old #19 population is retained as an independent post-line regression baseline.
TARGET_POSTLINE_SIGNS = 3_365_129
TARGET_POSTLINE_WITH_LANG = 3_364_981
TARGET_POSTLINE_LEVELS = {
    "line": 3_259_913,
    "colon": 64_686,
    "word": 40_187,
    "text": 195,
    "absent": 148,
}
# Technical anchors are not linguistic signs. The post-#52 current artifact has fewer
# because real recovered source slots can keep some structures alive; structure and
# pre-line conservation are checked independently.
TARGET_ANCHORS = 21_203
# #159 source-audited KBo 41.49+: relocating fourteen marker-only
# unclosed <w> wrappers restores 83 previously misnested line breaks.
# The complete #160+#159 rebuild independently found 82 *artificial* line
# anchors disappear while all 3,365,257 source-attested signs are conserved.
# Keep the historical anchor baseline and subtract this measured loss; never
# relax the genuine-sign / document / language conservation checks.
RECOVERED_NESTED_ANCHORS = 82
# #159: independently readable source tokens inside 15 literal <w lg="...">
# words that were formerly swallowed by 14 marker-only, unclosed ancestors.
# They retain their original signs and declared languages. The correction moves
# 74 signs from inherited line scope to the more specific word scope.
RECOVERED_NESTED_SOURCE = "CTH 479_XML_BESRIT/KBo 41.49+.xml"
RECOVERED_EXPLICIT_WORDS = {"Hur": 12, "Luw": 3}
RECOVERED_EXPLICIT_SIGNS = {"Hur": 63, "Luw": 11}
REQUIRED_FEATURES = ("otype", "oslots", "src_file", "sym", "lang", "anchor")


@dataclass(frozen=True)
class SourceRow:
    sym: str
    lang: str | None
    level: str


@dataclass(frozen=True)
class GraphRow:
    sym: str
    lang: str | None


def _lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else ""


def _positive(raw: str | None) -> str | None:
    """Independent source-value rule frozen by issue #19 research."""
    if raw is None:
        return None
    value = raw.strip()
    return value if value and value != "XXXlang" else None


def _choose(word, colon, line, text) -> tuple[str, str | None]:
    for level, raw in (
        ("word", word), ("colon", colon), ("line", line), ("text", text)
    ):
        value = _positive(raw)
        if value is not None:
            return level, value
    return "absent", None


def compare_rows(
    src_file: str, expected: list[SourceRow], actual: list[GraphRow], limit: int = 20
) -> list[str]:
    """Return exact sequence mismatches; kept pure so adversarial tests can mutate rows."""
    problems: list[str] = []
    if len(expected) != len(actual):
        problems.append(
            f"{src_file}: source/TF non-anchor sign count {len(expected)} != {len(actual)}"
        )
    for i, (want, got) in enumerate(zip(expected, actual), 1):
        if want.sym != got.sym or want.lang != got.lang:
            problems.append(
                f"{src_file}: sign {i}: source ({want.sym!r}, {want.lang!r}, "
                f"{want.level}) != TF ({got.sym!r}, {got.lang!r})"
            )
            if len(problems) >= limit:
                break
    return problems


def anchor_language_problems(rows: list[tuple[int, str | None]]) -> list[str]:
    return [f"anchor sign {node} carries lang={lang!r}" for node, lang in rows if lang is not None]


# CI #1397's independent source census, bound to corpus.sha256 and
# patches.yaml in its beta04-source-evidence artifact. Includes inferred signs.
BETA04_SOURCE_COUNTS = {
    "files": 24131, "documents": 24128,
    "excluded_encrypted": 1, "excluded_unparseable": 2,
    "source_signs": 3430499, "with_lang": 3430348,
    "preline_signs": 16, "postline_signs": 3430483,
    "postline_with_lang": 3430339, "words_before_first_line": 29,
    "inferred_lines": 10, "inferred_signs": 106,
    "inferred_postline_level_line": 106, "inferred_postline_with_lang": 106,
    "level_line": 3321148, "level_colon": 68481, "level_word": 40485,
    "level_text": 234, "level_absent": 151,
    "postline_level_line": 3321148, "postline_level_colon": 68478,
    "postline_level_word": 40485, "postline_level_text": 228,
    "postline_level_absent": 144,
    "recovered_override_words_Hur": 12, "recovered_override_words_Luw": 3,
    "recovered_override_signs_Hur": 63, "recovered_override_signs_Luw": 11,
}


def source_anchor_count(events, force_first):
    """Count necessary structural placeholders from source boundary events.

    Empty line/colon intervals can share a placeholder; a closed interval cannot
    cover a subsequent one. No TF node IDs, graph counts, or emitter imported.
    """
    seen = 0
    anchors = 0
    active = {}
    column = None

    def close(kind):
        nonlocal seen, anchors
        start = active.pop(kind, None)
        if start is not None and start == seen:
            seen += 1
            anchors += 1

    for kind, value in events:
        if kind == "sign":
            seen += value
        elif kind == "line":
            close("line")
            if column != value:
                close("colon")
                column = value
            active["line"] = seen
            if force_first and not seen:
                seen += 1
                anchors += 1
        elif kind == "colon":
            close("colon")
            active["colon"] = seen
        else:
            raise ValueError(f"unknown source anchor event {kind}")
    if force_first and not seen:
        seen += 1
        anchors += 1
    close("line")
    close("colon")
    return anchors


def beta04_target_problems(source_stats, graph_stats):
    problems = []
    for key, expected in BETA04_SOURCE_COUNTS.items():
        if source_stats[key] != expected:
            problems.append(f"source {key} {source_stats[key]} != frozen Beta 0.4 {expected}")
    for key in ("documents", "source_signs", "with_lang"):
        if graph_stats[key] != source_stats[key]:
            problems.append(f"TF {key} {graph_stats[key]} != source {source_stats[key]}")
    if "expected_anchors" not in source_stats:
        problems.append("independent source anchor census missing")
    elif graph_stats["anchors"] != source_stats["expected_anchors"]:
        problems.append(f"TF anchors {graph_stats['anchors']} != source interval count {source_stats['expected_anchors']}")
    return problems


def _source_documents() -> tuple[dict[str, list[SourceRow]], Counter, Counter, list[str]]:
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}
    expected: dict[str, list[SourceRow]] = {}
    stats = Counter()
    raw_values = Counter()
    problems: list[str] = []

    for path in corpus_files():
        src_file = rel(path)
        stats["files"] += 1
        if src_file == ENCRYPTED:
            stats["excluded_encrypted"] += 1
            continue
        parsed_path = sourcepath.parse(src_file)
        if not parsed_path.parse_ok or not parsed_path.project:
            problems.append(
                f"{src_file}: source path rejected: "
                f"{parsed_path.parse_error or 'missing_project'}"
            )
            continue

        data = path.read_bytes()
        patch_entry = patches.get(src_file)
        if patch_entry:
            try:
                data = repair.apply(data, patch_entry[1], expect_sha=patch_entry[0])
            except repair.PatchError as exc:
                problems.append(f"{src_file}: repair manifest failed: {exc}")
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

        text_span = next(
            (sp for sp in spans if sp.tag == "text" and sp.inner_start is not None), None
        )
        all_word_spans = [sp for sp in spans if sp.tag == "w"]
        if text_span is not None:
            all_word_spans = [
                sp for sp in all_word_spans
                if text_span.inner_start <= sp.outer_start < text_span.inner_end
            ]
        word_spans = []
        for sp in all_word_spans:
            if any(
                other is not sp
                and other.outer_start <= sp.outer_start
                and sp.outer_end <= other.outer_end
                for other in all_word_spans
            ):
                continue
            word_spans.append(sp)

        top_words = [
            node for node in text.iter()
            if _lname(node) == "w"
            and not any(_lname(ancestor) == "w" for ancestor in node.iterancestors())
        ]
        if len(top_words) != len(word_spans):
            problems.append(
                f"{src_file}: top-level word/span pairing "
                f"{len(top_words)} != {len(word_spans)}"
            )
            continue
        span_for = {id(node): sp for node, sp in zip(top_words, word_spans)}

        # Independently source the first unwrapped-reading pilot directly from
        # the original line body. Unlike the converter this does not partition
        # inferred words. It must yield the SAME sign sequence as the generated
        # graph, without trusting any TF src_span or inferred word feature.
        pilot = src_file == "CTH 170_XML_TLH/KBo 31.40.xml"
        pilot_lb = iter(
            sp for sp in spans if sp.tag == "lb"
            and text_span is not None
            and text_span.inner_start <= sp.outer_start < text_span.inner_end
        ) if pilot else None
        pilot_ps = [sp for sp in spans if sp.tag == "P___Standard"] if pilot else []
        if pilot and top_words:
            problems.append(f"{src_file}: unwrapped pilot gained literal source words")
            continue

        text_raw = text.get(XML_LANG)
        line_raw: str | None = None
        colon_raw: str | None = None
        collabel: str | None = None
        have_line = False
        rows: list[SourceRow] = []
        anchor_events = []

        for node in text.iter():
            if not isinstance(node.tag, str):
                continue
            tag = _lname(node)
            if tag == "lb":
                ref = lineref.parse(node.get("lnr"))
                anchor_events.append(("line", ref.collabel))
                if ref.collabel != collabel:
                    # Production closes an active colon when the parsed column changes.
                    colon_raw = None
                    collabel = ref.collabel
                line_raw = node.get("lg") if "lg" in node.attrib else None
                have_line = True
                if pilot:
                    try:
                        lb = next(pilot_lb)
                    except StopIteration:
                        problems.append(f"{src_file}: source line spans exhausted")
                        continue
                    ps = [
                        p for p in pilot_ps
                        if p.inner_start <= lb.outer_start < p.inner_end
                    ]
                    if len(ps) != 1 or lb.attrs.get("lnr") != node.get("lnr"):
                        problems.append(f"{src_file}: ambiguous source line ownership")
                        continue
                    end = min((
                        sp.outer_start for sp in spans
                        if lb.outer_end <= sp.outer_start < ps[0].inner_end
                        and sp.tag in ("lb", "clb", "parsep", "parsep_dbl", "gap")
                    ), default=ps[0].inner_end)
                    # Whole-line source tokenisation is deliberately independent
                    # of the converter's whitespace lexical grouping.
                    tokens = signs.tokenise_word(data[lb.outer_end:end])
                    readable = any(
                        t.type not in ("empty", "ellipsis", "unknown") and t.sym
                        for t in tokens
                    )
                    if readable:
                        anchor_events.append(("sign", sum(t.type != "empty" for t in tokens)))
                        level, lang = _choose(None, colon_raw, line_raw, text_raw)
                        stats["inferred_lines"] += 1
                        for token in tokens:
                            if token.type == "empty":
                                continue
                            rows.append(SourceRow(token.sym, lang, level))
                            stats["source_signs"] += 1
                            stats["inferred_signs"] += 1
                            stats[f"level_{level}"] += 1
                            stats[f"postline_level_{level}"] += 1
                            stats[f"inferred_postline_level_{level}"] += 1
                            stats["postline_signs"] += 1
                            if lang is not None:
                                stats["with_lang"] += 1
                                stats["postline_with_lang"] += 1
                                stats["inferred_postline_with_lang"] += 1
                                raw_values[(level, lang)] += 1
                continue
            if tag == "clb":
                anchor_events.append(("colon", None))
                colon_raw = node.get("lg") if "lg" in node.attrib else None
                continue
            if tag != "w" or id(node) not in span_for:
                continue

            is_preline = not have_line
            if is_preline:
                stats["words_before_first_line"] += 1

            word_raw = node.get("lg") if "lg" in node.attrib else None
            # Independently tally the original explicit-language words recovered
            # from the malformed document. The marker-only source ancestors
            # contained no signs and no lg. These literal words did.
            recovered_explicit = (
                src_file == RECOVERED_NESTED_SOURCE
                and word_raw in RECOVERED_EXPLICIT_WORDS
            )
            if recovered_explicit:
                stats[f"recovered_override_words_{word_raw}"] += 1
            # Before the first <lb>, line_raw is necessarily absent. Any source word,
            # colon, or text declaration that actually precedes the word remains valid;
            # a later line can never leak backwards into this choice.
            level, lang = _choose(word_raw, colon_raw, line_raw, text_raw)
            inner = source.inner_bytes(data, span_for[id(node)])
            tokens = signs.tokenise_word(inner)
            anchor_events.append(("sign", sum(t.type != "empty" for t in tokens)))
            for token in tokens:
                if token.type == "empty":
                    continue
                rows.append(SourceRow(token.sym, lang, level))
                if recovered_explicit:
                    stats[f"recovered_override_signs_{word_raw}"] += 1
                stats["source_signs"] += 1
                stats[f"level_{level}"] += 1
                if is_preline:
                    stats["preline_signs"] += 1
                else:
                    stats["postline_signs"] += 1
                    stats[f"postline_level_{level}"] += 1
                if lang is not None:
                    stats["with_lang"] += 1
                    raw_values[(level, lang)] += 1
                    if not is_preline:
                        stats["postline_with_lang"] += 1

        if src_file in expected:
            problems.append(f"{src_file}: duplicate source document key")
            continue
        # The converter reserves a first slot for documents without any literal
        # reading; source text rather than graph slots determines that condition.
        force_first = not pilot and not any(
            re.sub(rb"<[^>]*>", b"", source.inner_bytes(data, sp))
            .translate(None, b"-. \t\r\n").strip() for sp in word_spans
        )
        stats["expected_anchors"] += source_anchor_count(anchor_events, force_first)
        expected[src_file] = rows
        stats["documents"] += 1

    return expected, stats, raw_values, problems


def _graph_documents():
    from tf.fabric import Fabric

    tf_dir = ROOT / "tf" / TF_VERSION
    missing = [name for name in REQUIRED_FEATURES if not (tf_dir / f"{name}.tf").is_file()]
    if missing:
        return None, Counter(), [
            f"tf/{TF_VERSION}: missing required sign-language features: {', '.join(missing)}"
        ]

    TF = Fabric(locations=str(tf_dir), silent="deep")
    api = TF.load(" ".join(REQUIRED_FEATURES), silent="deep")
    if api is False or api is None:
        return None, Counter(), [f"tf/{TF_VERSION}: dataset does not load"]

    F, L = api.F, api.L
    docs: dict[str, list[GraphRow]] = {}
    stats = Counter()
    problems: list[str] = []

    anchor_rows: list[tuple[int, str | None]] = []
    for sign in F.otype.s("sign"):
        if F.anchor.v(sign):
            stats["anchors"] += 1
            anchor_rows.append((sign, F.lang.v(sign)))
            if F.sym.v(sign):
                problems.append(f"technical anchor {sign} contains reading {F.sym.v(sign)!r}")
        else:
            stats["source_signs"] += 1
            if F.lang.v(sign) is not None:
                stats["with_lang"] += 1
    problems.extend(anchor_language_problems(anchor_rows)[:20])

    for doc in F.otype.s("document"):
        src_file = F.src_file.v(doc)
        if not src_file:
            problems.append(f"document node {doc}: missing src_file")
            continue
        if src_file in docs:
            problems.append(f"{src_file}: duplicate graph document key")
            continue
        rows = [
            GraphRow(F.sym.v(sign) or "", F.lang.v(sign))
            for sign in L.d(doc, otype="sign")
            if not F.anchor.v(sign)
        ]
        docs[src_file] = rows
        stats["documents"] += 1

    return docs, stats, problems


def _target_problems(source_stats: Counter, graph_stats: Counter) -> list[str]:
    problems = []
    expected_postline_levels = Counter(
        {f"postline_level_{k}": v for k, v in TARGET_POSTLINE_LEVELS.items()}
    )
    # Retain the historical frozen baselines, applying only the source-proven
    # reattribution of 15 explicit lg words from this one repaired document.
    # The resulting source/TF rows are still compared sign-by-sign below.
    recovered_signs = sum(RECOVERED_EXPLICIT_SIGNS.values())
    expected_postline_levels["postline_level_line"] -= recovered_signs
    expected_postline_levels["postline_level_word"] += recovered_signs
    for lang, expected in RECOVERED_EXPLICIT_WORDS.items():
        key = f"recovered_override_words_{lang}"
        if source_stats[key] != expected:
            problems.append(
                f"source recovered {key} {source_stats[key]} != pinned {expected}"
            )
    for lang, expected in RECOVERED_EXPLICIT_SIGNS.items():
        key = f"recovered_override_signs_{lang}"
        if source_stats[key] != expected:
            problems.append(
                f"source recovered {key} {source_stats[key]} != pinned {expected}"
            )
    if source_stats["documents"] != TARGET_DOCUMENTS:
        problems.append(
            f"source documents {source_stats['documents']} != frozen {TARGET_DOCUMENTS}"
        )
    if source_stats["source_signs"] - source_stats["inferred_signs"] != TARGET_SOURCE_SIGNS:
        problems.append(
            f"source signs {source_stats['source_signs']} != frozen {TARGET_SOURCE_SIGNS}"
        )
    if source_stats["preline_signs"] != TARGET_PRELINE_SIGNS:
        problems.append(
            f"source pre-line signs {source_stats['preline_signs']} != frozen {TARGET_PRELINE_SIGNS}"
        )
    if source_stats["postline_signs"] - source_stats["inferred_signs"] != TARGET_POSTLINE_SIGNS:
        problems.append(
            f"source post-line signs {source_stats['postline_signs']} != frozen {TARGET_POSTLINE_SIGNS}"
        )
    if (source_stats["postline_with_lang"] - source_stats["inferred_postline_with_lang"] != TARGET_POSTLINE_WITH_LANG):
        problems.append(
            "source post-line signs with lang "
            f"{source_stats['postline_with_lang']} != frozen {TARGET_POSTLINE_WITH_LANG}"
        )
    for key, target in expected_postline_levels.items():
        if source_stats[key] - source_stats[f"inferred_{key}"] != target:
            problems.append(
                f"source {key} {source_stats[key]} - inferred "
                f"{source_stats[f'inferred_{key}']} = "
                f"{source_stats[key] - source_stats[f'inferred_{key}']} "
                f"!= frozen {target}"
            )
    # A change in level attribution must not silently change the number of
    # post-line signs. This is independent of the frozen historical targets.
    observed_levels = sum(
        source_stats[f"postline_level_{level}"]
        for level in TARGET_POSTLINE_LEVELS
    )
    if observed_levels != source_stats["postline_signs"]:
        problems.append(
            f"post-line level partition {observed_levels} != "
            f"post-line sign population {source_stats['postline_signs']}"
        )
    if graph_stats["documents"] != TARGET_DOCUMENTS:
        problems.append(
            f"TF documents {graph_stats['documents']} != frozen {TARGET_DOCUMENTS}"
        )
    if graph_stats["source_signs"] - source_stats["inferred_signs"] != TARGET_SOURCE_SIGNS:
        problems.append(
            f"TF non-anchor signs {graph_stats['source_signs']} != frozen {TARGET_SOURCE_SIGNS}"
        )
    if graph_stats["with_lang"] != source_stats["with_lang"]:
        problems.append(
            f"TF signs with lang {graph_stats['with_lang']} != source {source_stats['with_lang']}"
        )
    expected_anchors = (
        TARGET_ANCHORS - source_stats["inferred_lines"] - RECOVERED_NESTED_ANCHORS
    )
    if graph_stats["anchors"] != expected_anchors:
        problems.append(
            f"TF anchors {graph_stats['anchors']} != independently "
            f"source-backed expected {expected_anchors} "
            f"(baseline {TARGET_ANCHORS}, inferred lines "
            f"{source_stats['inferred_lines']}, nested recovery "
            f"{RECOVERED_NESTED_ANCHORS})"
        )
    return problems


def _write_report(
    source_stats: Counter,
    graph_stats: Counter,
    raw_values: Counter,
    problems: list[str],
) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Sign-language conservation",
        "",
        f"TF version: `{TF_VERSION}`",
        "",
        "## Frozen population",
        "",
        f"- source documents: **{source_stats['documents']:,}**",
        f"- source / non-anchor signs: **{source_stats['source_signs']:,}**",
        f"- recovered pre-line source signs: **{source_stats['preline_signs']:,}**",
        f"- signs with effective source language: **{source_stats['with_lang']:,}**",
        f"- genuinely absent: **{source_stats['level_absent']:,}**",
        f"- synthetic anchors: **{graph_stats['anchors']:,}** (language-free required)",
        f"- source-attested unwrapped signs: **{source_stats['inferred_signs']:,}** "
        f"on {source_stats['inferred_lines']:,} lines",
        "",
        "## Winning source level",
        "",
        "| level | signs |",
        "| --- | ---: |",
    ]
    for level in ("word", "colon", "line", "text", "absent"):
        lines.append(f"| {level} | {source_stats[f'level_{level}']:,} |")
    lines.extend([
        "",
        "## Most frequent winning raw values",
        "",
        "| level | raw value | signs |",
        "| --- | --- | ---: |",
    ])
    for (level, value), count in raw_values.most_common(30):
        safe = value.replace("|", "\\|").replace("\n", "\\n")
        lines.append(f"| {level} | `{safe}` | {count:,} |")
    lines.extend(["", "## Result", ""])
    if problems:
        lines.append(f"**FAIL** — {len(problems):,} problem(s). First findings:")
        lines.append("")
        lines.extend(f"- {problem}" for problem in problems[:50])
    else:
        lines.append(
            "**PASS** — every converted document's ordered non-anchor sign sequence "
            "matches the independently reconstructed source language values exactly."
        )
    (REPORTS / "sign-language.md").write_text("\n".join(lines) + "\n", encoding="utf8")


def main() -> int:
    expected, source_stats, raw_values, problems = _source_documents()
    graph, graph_stats, graph_problems = _graph_documents()
    problems.extend(graph_problems)

    if graph is not None:
        source_keys = set(expected)
        graph_keys = set(graph)
        for src_file in sorted(source_keys - graph_keys)[:50]:
            problems.append(f"{src_file}: source document missing from TF")
        for src_file in sorted(graph_keys - source_keys)[:50]:
            problems.append(f"{src_file}: graph-only document")
        for src_file in sorted(source_keys & graph_keys):
            problems.extend(compare_rows(src_file, expected[src_file], graph[src_file]))
            if len(problems) >= 200:
                break

    problems.extend((beta04_target_problems if SOURCE_VERSION == "0.4" else _target_problems)(source_stats, graph_stats))
    _write_report(source_stats, graph_stats, raw_values, problems)

    print("SIGN LANGUAGE CONSERVATION")
    print(f"documents={source_stats['documents']:,}")
    print(f"source_signs={source_stats['source_signs']:,}")
    print(f"preline_signs={source_stats['preline_signs']:,}")
    print(f"with_lang={source_stats['with_lang']:,}")
    print(
        "levels=" + ", ".join(
            f"{level}:{source_stats[f'level_{level}']:,}"
            for level in ("line", "colon", "word", "text", "absent")
        )
    )
    print(f"anchors={graph_stats['anchors']:,}")
    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        for problem in problems[:20]:
            print("  " + problem)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
