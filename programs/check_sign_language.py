#!/usr/bin/env python
"""Independently verify source-declared effective language on every shipped sign.

The source-side scope reconstruction deliberately does not import converter language
state or a propagation helper.  It reparses the pinned repaired corpus, reconstructs
word/colon/line/text precedence, and compares the exact per-document ordered non-anchor
sign sequence with the shipped Text-Fabric graph.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys
from xml.parsers import expat

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, lineref, repair, signs, source, sourcepath
from tlhdig.paths import CORPUS, ENCRYPTED, PATCHES, REPORTS, ROOT, corpus_files, rel

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
TARGET_DOCUMENTS = 23_884
TARGET_SOURCE_SIGNS = 3_365_129
TARGET_WITH_LANG = 3_364_981
TARGET_ANCHORS = 21_215
TARGET_LEVELS = {
    "line": 3_259_913,
    "colon": 64_686,
    "word": 40_187,
    "text": 195,
    "absent": 148,
}
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

        text_raw = text.get(XML_LANG)
        line_raw: str | None = None
        colon_raw: str | None = None
        collabel: str | None = None
        have_line = False
        rows: list[SourceRow] = []

        for node in text.iter():
            if not isinstance(node.tag, str):
                continue
            tag = _lname(node)
            if tag == "lb":
                ref = lineref.parse(node.get("lnr"))
                if ref.collabel != collabel:
                    # Production closes an active colon when the parsed column changes.
                    colon_raw = None
                    collabel = ref.collabel
                line_raw = node.get("lg") if "lg" in node.attrib else None
                have_line = True
                continue
            if tag == "clb":
                colon_raw = node.get("lg") if "lg" in node.attrib else None
                continue
            if tag != "w" or id(node) not in span_for:
                continue

            # #52 owns readable words before the first line; #19 must compare exactly
            # the source-sign population that the current converter emits.
            if not have_line:
                stats["words_before_first_line"] += 1
                inner = source.inner_bytes(data, span_for[id(node)])
                stats["signs_before_first_line"] += sum(
                    1 for token in signs.tokenise_word(inner) if token.type != "empty"
                )
                continue

            word_raw = node.get("lg") if "lg" in node.attrib else None
            level, lang = _choose(word_raw, colon_raw, line_raw, text_raw)
            inner = source.inner_bytes(data, span_for[id(node)])
            for token in signs.tokenise_word(inner):
                if token.type == "empty":
                    continue
                rows.append(SourceRow(token.sym, lang, level))
                stats["source_signs"] += 1
                stats[f"level_{level}"] += 1
                if lang is not None:
                    stats["with_lang"] += 1
                    raw_values[(level, lang)] += 1

        if src_file in expected:
            problems.append(f"{src_file}: duplicate source document key")
            continue
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
    expected_levels = Counter({f"level_{k}": v for k, v in TARGET_LEVELS.items()})
    if source_stats["documents"] != TARGET_DOCUMENTS:
        problems.append(
            f"source documents {source_stats['documents']} != frozen {TARGET_DOCUMENTS}"
        )
    if source_stats["source_signs"] != TARGET_SOURCE_SIGNS:
        problems.append(
            f"source signs {source_stats['source_signs']} != frozen {TARGET_SOURCE_SIGNS}"
        )
    if source_stats["with_lang"] != TARGET_WITH_LANG:
        problems.append(
            f"source signs with lang {source_stats['with_lang']} != frozen {TARGET_WITH_LANG}"
        )
    for key, target in expected_levels.items():
        if source_stats[key] != target:
            problems.append(f"source {key} {source_stats[key]} != frozen {target}")
    if graph_stats["documents"] != TARGET_DOCUMENTS:
        problems.append(
            f"TF documents {graph_stats['documents']} != frozen {TARGET_DOCUMENTS}"
        )
    if graph_stats["source_signs"] != TARGET_SOURCE_SIGNS:
        problems.append(
            f"TF non-anchor signs {graph_stats['source_signs']} != frozen {TARGET_SOURCE_SIGNS}"
        )
    if graph_stats["with_lang"] != TARGET_WITH_LANG:
        problems.append(
            f"TF signs with lang {graph_stats['with_lang']} != frozen {TARGET_WITH_LANG}"
        )
    if graph_stats["anchors"] != TARGET_ANCHORS:
        problems.append(f"TF anchors {graph_stats['anchors']} != frozen {TARGET_ANCHORS}")
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
        f"- signs with effective source language: **{source_stats['with_lang']:,}**",
        f"- genuinely absent: **{source_stats['level_absent']:,}**",
        f"- synthetic anchors: **{graph_stats['anchors']:,}** (language-free required)",
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

    problems.extend(_target_problems(source_stats, graph_stats))
    _write_report(source_stats, graph_stats, raw_values, problems)

    print("SIGN LANGUAGE CONSERVATION")
    print(f"documents={source_stats['documents']:,}")
    print(f"source_signs={source_stats['source_signs']:,}")
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
