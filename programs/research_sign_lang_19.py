#!/usr/bin/env python
"""Corpus-wide research scanner for issue #19 (source-faithful sign language).

Research only: this does not define production semantics. It inventories every source
language declaration and measures candidate effective-language precedence on the strict
production population. The output is deterministic JSON plus a compact stdout summary.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from xml.parsers import expat

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import repair, signs, source
from tlhdig.paths import ENCRYPTED, PATCHES, ROOT, corpus_files, rel

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
OUT = ROOT / "reports" / "research-sign-lang-19.json"


def lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else ""


def clean(value: str | None) -> str:
    return "" if value is None else value.strip()


def language_decls(node) -> list[tuple[str, str]]:
    rows = []
    if XML_LANG in node.attrib:
        rows.append(("xml:lang", node.get(XML_LANG) or ""))
    if "lg" in node.attrib:
        rows.append(("lg", node.get("lg") or ""))
    return rows


def sign_count(data: bytes, span) -> int:
    inner = source.inner_bytes(data, span)
    return sum(1 for token in signs.tokenise_word(inner) if token.type != "empty")


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}
    counts = Counter()
    decls = Counter()
    decl_files: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    samples: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    ancestor_shapes = Counter()
    active_conflicts = Counter()
    effective_signs = Counter()
    effective_words = Counter()
    no_lang_samples: list[str] = []
    inline_word_decl_samples: list[str] = []
    word_override_samples: list[str] = []
    line_no_lang_samples: list[str] = []
    empty_decl_samples: list[str] = []
    excluded: list[tuple[str, str]] = []

    for path in corpus_files():
        src_file = rel(path)
        counts["files"] += 1
        if src_file == ENCRYPTED:
            counts["excluded_encrypted"] += 1
            excluded.append((src_file, "encrypted"))
            continue

        data = path.read_bytes()
        patch_entry = patches.get(src_file)
        if patch_entry:
            try:
                data = repair.apply(data, patch_entry[1], expect_sha=patch_entry[0])
            except repair.PatchError:
                counts["excluded_patch_error"] += 1
                excluded.append((src_file, "patch_error"))
                continue

        try:
            spans = source.scan(data)
            root = ET.fromstring(data)
        except (expat.ExpatError, ET.XMLSyntaxError, ValueError):
            counts["excluded_unparseable"] += 1
            excluded.append((src_file, "unparseable"))
            continue

        div1 = root.find("body/div1")
        text = div1.find("text") if div1 is not None else None
        if text is None:
            counts["excluded_no_text"] += 1
            excluded.append((src_file, "no_text"))
            continue
        counts["production_documents"] += 1

        # Inventory every declaration in the strict source tree, not only the ones the
        # current converter happens to model.
        for node in root.iter():
            if not isinstance(node.tag, str):
                continue
            tag = lname(node)
            for attr, raw in language_decls(node):
                key = (tag, attr, raw)
                decls[key] += 1
                decl_files[key].add(src_file)
                if len(samples[key]) < 3:
                    samples[key].append(src_file)
                counts["declarations"] += 1
                if raw == "":
                    counts["empty_declarations"] += 1
                    if len(empty_decl_samples) < 20:
                        empty_decl_samples.append(f"{src_file}: <{tag}> {attr}=empty")

        # Pair top-level source <w> elements with the same raw byte spans used by the
        # converter, so sign counts reflect actual slot creation rather than XML text
        # length. Nested <w> is consumed by its enclosing word and is excluded here.
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
            if not any(ancestor.tag == "w" for ancestor in node.iterancestors())
        ]
        if len(top_words) != len(w_spans):
            counts["word_span_pairing_mismatch_docs"] += 1
            excluded.append((src_file, f"word_span_pairing:{len(top_words)}!={len(w_spans)}"))
            continue

        span_for = {id(node): sp for node, sp in zip(top_words, w_spans)}

        text_lang_raw = text.get(XML_LANG)
        text_lang = clean(text_lang_raw)
        if text_lang_raw is not None:
            counts["texts_with_xml_lang"] += 1
        else:
            counts["texts_without_xml_lang"] += 1

        active_line_raw: str | None = None
        active_colon_raw: str | None = None
        line_index = 0
        word_index = 0

        for node in text.iter():
            if not isinstance(node.tag, str):
                continue
            tag = lname(node)
            if tag == "lb":
                line_index += 1
                active_line_raw = node.get("lg") if "lg" in node.attrib else None
                # A colon is a structural unit in the current converter and can span
                # lines. Do not reset it here; instead measure disagreements explicitly.
                if active_line_raw is None:
                    counts["lines_without_lg"] += 1
                    if len(line_no_lang_samples) < 20:
                        line_no_lang_samples.append(f"{src_file} line#{line_index}")
                else:
                    counts["lines_with_lg"] += 1
                continue
            if tag == "clb":
                active_colon_raw = node.get("lg") if "lg" in node.attrib else None
                if active_colon_raw is None:
                    counts["colons_without_lg"] += 1
                else:
                    counts["colons_with_lg"] += 1
                continue
            if tag != "w" or id(node) not in span_for:
                continue

            word_index += 1
            nsigns = sign_count(data, span_for[id(node)])
            counts["top_words"] += 1
            counts["readable_signs"] += nsigns
            if nsigns == 0:
                counts["contentless_words"] += 1

            word_raw = node.get("lg") if "lg" in node.attrib else None
            if word_raw is not None:
                counts["words_with_lg"] += 1
                if len(word_override_samples) < 30:
                    word_override_samples.append(
                        f"{src_file} line#{line_index} word#{word_index}: "
                        f"word={word_raw!r} colon={active_colon_raw!r} "
                        f"line={active_line_raw!r} text={text_lang_raw!r}"
                    )
            else:
                counts["words_without_lg"] += 1

            inner_decls = []
            for desc in node.iterdescendants():
                if not isinstance(desc.tag, str):
                    continue
                for attr, raw in language_decls(desc):
                    inner_decls.append((lname(desc), attr, raw))
            if inner_decls:
                counts["words_with_descendant_language_decl"] += 1
                counts["descendant_language_declarations_in_words"] += len(inner_decls)
                if len(inline_word_decl_samples) < 50:
                    inline_word_decl_samples.append(
                        f"{src_file} line#{line_index} word#{word_index}: {inner_decls!r}"
                    )

            # Candidate precedence to measure, not yet a production decision:
            # word > active colon > active line > text. Empty values are declarations
            # of absence and therefore stop inheritance in a second statistic below;
            # the primary candidate treats empty/XXXlang as unresolved, not as a
            # positive language identity.
            levels = [
                ("word", word_raw),
                ("colon", active_colon_raw),
                ("line", active_line_raw),
                ("text", text_lang_raw),
            ]
            positive = [(level, clean(raw)) for level, raw in levels if raw is not None and clean(raw) and clean(raw) != "XXXlang"]
            if positive:
                level, value = positive[0]
                effective_words[(level, value)] += 1
                effective_signs[(level, value)] += nsigns
            else:
                effective_words[("absent", "")] += 1
                effective_signs[("absent", "")] += nsigns
                if nsigns and len(no_lang_samples) < 50:
                    no_lang_samples.append(
                        f"{src_file} line#{line_index} word#{word_index}: "
                        f"word={word_raw!r} colon={active_colon_raw!r} "
                        f"line={active_line_raw!r} text={text_lang_raw!r}"
                    )

            positives = [(level, clean(raw)) for level, raw in levels if raw is not None and clean(raw) and clean(raw) != "XXXlang"]
            if len({value for _level, value in positives}) > 1:
                active_conflicts[tuple(positives)] += nsigns

            nearest_ancestor_decl = []
            for ancestor in node.iterancestors():
                if ancestor is text.getparent():
                    break
                for attr, raw in language_decls(ancestor):
                    nearest_ancestor_decl.append((lname(ancestor), attr, raw))
                if nearest_ancestor_decl:
                    break
            ancestor_shapes[tuple(nearest_ancestor_decl) if nearest_ancestor_decl else (("none", "", ""),)] += nsigns

    payload = {
        "counts": dict(sorted(counts.items())),
        "declarations": [
            {
                "tag": tag,
                "attribute": attr,
                "raw": raw,
                "occurrences": n,
                "files": len(decl_files[(tag, attr, raw)]),
                "samples": samples[(tag, attr, raw)],
            }
            for (tag, attr, raw), n in sorted(decls.items(), key=lambda item: (-item[1], item[0]))
        ],
        "candidate_effective_words": [
            {"level": level, "raw": raw, "count": n}
            for (level, raw), n in sorted(effective_words.items(), key=lambda item: (-item[1], item[0]))
        ],
        "candidate_effective_signs": [
            {"level": level, "raw": raw, "count": n}
            for (level, raw), n in sorted(effective_signs.items(), key=lambda item: (-item[1], item[0]))
        ],
        "active_language_conflicts_by_sign": [
            {"active": list(active), "signs": n}
            for active, n in sorted(active_conflicts.items(), key=lambda item: (-item[1], repr(item[0])))
        ],
        "nearest_ancestor_declarations_by_sign": [
            {"declaration": list(shape), "signs": n}
            for shape, n in sorted(ancestor_shapes.items(), key=lambda item: (-item[1], repr(item[0])))
        ],
        "samples": {
            "no_effective_language": no_lang_samples,
            "word_overrides": word_override_samples,
            "descendant_language_declarations_inside_words": inline_word_decl_samples,
            "lines_without_lg": line_no_lang_samples,
            "empty_declarations": empty_decl_samples,
        },
        "excluded": excluded,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf8")

    print("ISSUE 19 SOURCE LANGUAGE RESEARCH")
    for key in sorted(counts):
        print(f"{key}={counts[key]}")
    print("\nDECLARATIONS")
    for row in payload["declarations"]:
        print(
            f"{row['tag']}.{row['attribute']}={row['raw']!r}: "
            f"{row['occurrences']} occurrences / {row['files']} files"
        )
    print("\nCANDIDATE EFFECTIVE SIGNS (word > colon > line > text)")
    for row in payload["candidate_effective_signs"]:
        print(f"{row['level']} {row['raw']!r}: {row['count']}")
    print("\nDESCENDANT DECLARATIONS INSIDE WORDS")
    for sample in inline_word_decl_samples[:20]:
        print(sample)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
