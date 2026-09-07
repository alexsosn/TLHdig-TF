#!/usr/bin/env python
"""Corpus-wide research scanner for issue #19 (source-faithful sign language).

Research only: this does not define production semantics. It inventories every source
language declaration, measures competing sequential scope models, and separates genuine
word overrides from language-bearing boundaries swallowed by malformed ``w`` trees.
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


def positive(value: str | None) -> str:
    """Return a positive source language token, not a normalized language identity."""
    value = clean(value)
    return "" if not value or value == "XXXlang" else value


def language_decls(node) -> list[tuple[str, str]]:
    rows = []
    if XML_LANG in node.attrib:
        rows.append(("xml:lang", node.get(XML_LANG) or ""))
    if "lg" in node.attrib:
        rows.append(("lg", node.get("lg") or ""))
    return rows


def token_sign_count(data: bytes, span) -> int:
    inner = source.inner_bytes(data, span)
    return sum(1 for token in signs.tokenise_word(inner) if token.type != "empty")


def choose(levels: list[tuple[str, str | None]]) -> tuple[str, str]:
    for level, raw in levels:
        value = positive(raw)
        if value:
            return level, value
    return "absent", ""


def add_sample(bucket: dict, key, value: str, limit: int = 5) -> None:
    rows = bucket.setdefault(key, [])
    if len(rows) < limit:
        rows.append(value)


def main() -> int:
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}
    counts = Counter()
    decls = Counter()
    decl_files: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    samples: dict[tuple[str, str, str], list[str]] = defaultdict(list)

    model_signs: dict[str, Counter] = {
        "word_colon_line_text": Counter(),
        "word_line_text": Counter(),
        "word_line_colon_text": Counter(),
    }
    model_disagreements = Counter()
    active_conflicts = Counter()
    conflict_samples: dict[tuple, list[str]] = {}
    colon_line_pairs = Counter()
    colon_line_pair_samples: dict[tuple, list[str]] = {}
    word_override_pairs = Counter()
    word_override_pair_samples: dict[tuple, list[str]] = {}
    empty_scope = Counter()
    empty_samples: list[str] = []
    malformed_boundary_samples: list[str] = []
    no_lang_samples: list[str] = []
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

                # A language-bearing lb/clb nested in a word is a structural anomaly,
                # not evidence that the source grammar supports sign-inline language.
                if tag in {"lb", "clb"} and any(lname(a) == "w" for a in node.iterancestors()):
                    counts["language_boundaries_nested_in_word"] += 1
                    if len(malformed_boundary_samples) < 50:
                        malformed_boundary_samples.append(
                            f"{src_file}: <{tag} {attr}={raw!r}> nested in <w>"
                        )

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
            excluded.append((src_file, f"word_span_pairing:{len(top_words)}!={len(w_spans)}"))
            continue
        span_for = {id(node): sp for node, sp in zip(top_words, w_spans)}

        text_lang_raw = text.get(XML_LANG)
        if text_lang_raw is not None:
            counts["texts_with_xml_lang"] += 1
        else:
            counts["texts_without_xml_lang"] += 1

        active_line_raw: str | None = None
        active_colon_raw: str | None = None
        line_index = 0
        word_index = 0
        have_line = False

        for node in text.iter():
            if not isinstance(node.tag, str):
                continue
            tag = lname(node)

            if tag == "lb":
                line_index += 1
                have_line = True
                active_line_raw = node.get("lg") if "lg" in node.attrib else None
                if active_line_raw is None:
                    counts["lines_without_lg"] += 1
                else:
                    counts["lines_with_lg"] += 1
                    if clean(active_line_raw) == "":
                        counts["lines_with_empty_lg"] += 1
                continue

            if tag == "clb":
                active_colon_raw = node.get("lg") if "lg" in node.attrib else None
                if active_colon_raw is None:
                    counts["colons_without_lg"] += 1
                else:
                    counts["colons_with_lg"] += 1
                    if clean(active_colon_raw) == "":
                        counts["colons_with_empty_lg"] += 1
                continue

            if tag != "w" or id(node) not in span_for:
                continue

            word_index += 1
            nsigns = token_sign_count(data, span_for[id(node)])
            counts["top_words"] += 1
            counts["source_token_signs"] += nsigns
            if not have_line:
                counts["words_before_first_lb"] += 1
                counts["signs_before_first_lb"] += nsigns
                continue
            counts["convertible_words"] += 1
            counts["convertible_source_signs"] += nsigns
            if nsigns == 0:
                counts["contentless_words_after_lb"] += 1

            word_raw = node.get("lg") if "lg" in node.attrib else None
            if word_raw is None:
                counts["words_without_lg"] += 1
            else:
                counts["words_with_lg"] += 1
                if clean(word_raw) == "":
                    counts["words_with_empty_lg"] += 1

            levels_all = [
                ("word", word_raw),
                ("colon", active_colon_raw),
                ("line", active_line_raw),
                ("text", text_lang_raw),
            ]
            choices = {
                "word_colon_line_text": choose(levels_all),
                "word_line_text": choose([
                    ("word", word_raw), ("line", active_line_raw), ("text", text_lang_raw)
                ]),
                "word_line_colon_text": choose([
                    ("word", word_raw), ("line", active_line_raw),
                    ("colon", active_colon_raw), ("text", text_lang_raw)
                ]),
            }
            for model, choice in choices.items():
                model_signs[model][choice] += nsigns
            if len(set(choices.values())) > 1:
                model_disagreements[tuple(sorted(choices.items()))] += nsigns

            positives = tuple(
                (level, positive(raw)) for level, raw in levels_all if positive(raw)
            )
            if len({value for _level, value in positives}) > 1:
                active_conflicts[positives] += nsigns
                add_sample(
                    conflict_samples,
                    positives,
                    f"{src_file} line#{line_index} word#{word_index}: "
                    f"word={word_raw!r} colon={active_colon_raw!r} "
                    f"line={active_line_raw!r} text={text_lang_raw!r}",
                )

            colon_value = positive(active_colon_raw)
            line_value = positive(active_line_raw)
            if colon_value:
                pair = (colon_value, line_value or "<none>")
                colon_line_pairs[pair] += nsigns
                add_sample(
                    colon_line_pair_samples,
                    pair,
                    f"{src_file} line#{line_index} word#{word_index}",
                )

            word_value = positive(word_raw)
            inherited_without_word = choose([
                ("colon", active_colon_raw), ("line", active_line_raw), ("text", text_lang_raw)
            ])[1]
            if word_raw is not None:
                pair = (clean(word_raw) or "<empty>", inherited_without_word or "<none>")
                word_override_pairs[pair] += nsigns
                add_sample(
                    word_override_pair_samples,
                    pair,
                    f"{src_file} line#{line_index} word#{word_index}",
                )

            # Empty attributes are separately counted because they may mean "no override"
            # rather than an explicit scope barrier. We do not decide that here.
            for level, raw in levels_all[:-1]:
                if raw is not None and clean(raw) == "":
                    empty_scope[(level, choose(levels_all)[0], choose(levels_all)[1])] += nsigns
                    if nsigns and len(empty_samples) < 50:
                        empty_samples.append(
                            f"{src_file} line#{line_index} word#{word_index}: empty {level}; "
                            f"word={word_raw!r} colon={active_colon_raw!r} "
                            f"line={active_line_raw!r} text={text_lang_raw!r}"
                        )

            if choices["word_colon_line_text"] == ("absent", "") and nsigns:
                counts["convertible_signs_without_positive_language"] += nsigns
                if len(no_lang_samples) < 50:
                    no_lang_samples.append(
                        f"{src_file} line#{line_index} word#{word_index}: "
                        f"word={word_raw!r} colon={active_colon_raw!r} "
                        f"line={active_line_raw!r} text={text_lang_raw!r}"
                    )

            # There is no genuine child-level language grammar in the measured corpus
            # unless a non-structural descendant (not nested w/lb/clb) carries one.
            genuine_desc = []
            for desc in node.iterdescendants():
                if not isinstance(desc.tag, str):
                    continue
                dtag = lname(desc)
                if dtag in {"w", "lb", "clb"}:
                    continue
                for attr, raw in language_decls(desc):
                    genuine_desc.append((dtag, attr, raw))
            if genuine_desc:
                counts["words_with_genuine_descendant_language_decl"] += 1
                counts["genuine_descendant_language_declarations"] += len(genuine_desc)

    def counter_rows(counter: Counter, key_name: str, *, samples_from=None):
        rows = []
        for key, n in sorted(counter.items(), key=lambda item: (-item[1], repr(item[0]))):
            row = {key_name: key, "signs": n}
            if samples_from is not None:
                row["samples"] = samples_from.get(key, [])
            rows.append(row)
        return rows

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
        "candidate_models": {
            model: [
                {"level": level, "raw": raw, "signs": n}
                for (level, raw), n in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
            ]
            for model, counter in model_signs.items()
        },
        "model_disagreements": [
            {"choices": [[model, list(choice)] for model, choice in choices], "signs": n}
            for choices, n in sorted(model_disagreements.items(), key=lambda item: (-item[1], repr(item[0])))
        ],
        "active_language_conflicts": [
            {"active": list(active), "signs": n, "samples": conflict_samples.get(active, [])}
            for active, n in sorted(active_conflicts.items(), key=lambda item: (-item[1], repr(item[0])))
        ],
        "colon_line_pairs": [
            {"colon": key[0], "line": key[1], "signs": n, "samples": colon_line_pair_samples.get(key, [])}
            for key, n in sorted(colon_line_pairs.items(), key=lambda item: (-item[1], item[0]))
        ],
        "word_override_pairs": [
            {"word": key[0], "inherited": key[1], "signs": n, "samples": word_override_pair_samples.get(key, [])}
            for key, n in sorted(word_override_pairs.items(), key=lambda item: (-item[1], item[0]))
        ],
        "empty_scope_cases": [
            {"empty_level": key[0], "fallback_level": key[1], "fallback_raw": key[2], "signs": n}
            for key, n in sorted(empty_scope.items(), key=lambda item: (-item[1], item[0]))
        ],
        "samples": {
            "without_positive_language": no_lang_samples,
            "empty_scope": empty_samples,
            "language_boundaries_nested_in_word": malformed_boundary_samples,
        },
        "excluded": excluded,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf8")

    print("ISSUE 19 SOURCE LANGUAGE RESEARCH v2")
    for key in sorted(counts):
        print(f"{key}={counts[key]}")
    print("\nTOP DECLARATIONS")
    for row in payload["declarations"][:50]:
        print(
            f"{row['tag']}.{row['attribute']}={row['raw']!r}: "
            f"{row['occurrences']} occurrences / {row['files']} files"
        )
    print("\nTOP COLON/LINE PAIRS BY SOURCE SIGN")
    for row in payload["colon_line_pairs"][:30]:
        print(f"colon={row['colon']!r} line={row['line']!r}: {row['signs']}")
    print("\nTOP WORD OVERRIDES BY SOURCE SIGN")
    for row in payload["word_override_pairs"][:30]:
        print(f"word={row['word']!r} inherited={row['inherited']!r}: {row['signs']}")
    print("\nMODEL DISAGREEMENTS")
    for row in payload["model_disagreements"][:20]:
        print(f"{row['signs']}: {row['choices']}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
