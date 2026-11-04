#!/usr/bin/env python
"""Independent conservation gate for readable words before the first real line.

The converter used to drop readable top-level ``<w>`` elements while no ``<lb>`` was
open. This checker derives expected source identities from repaired XML and compares
them with the shipped graph by ``(document.src_file, word.src_span)``. It does not import
the converter or learn acceptance from its output.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from xml.parsers import expat

from lxml import etree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import PROVENANCE_DIR, TF_VERSION, repair, signs, source, sourcepath
from tlhdig.paths import ENCRYPTED, PATCHES, REPORTS, ROOT, corpus_files, rel

EXPECTED_PRELINE_WORDS = 36
EXPECTED_READABLE_WORDS = 15
EXPECTED_READABLE_SIGNS = 22
EXPECTED_NON_ANCHOR_SIGNS = 3_365_151


def _lname(node) -> str:
    return ET.QName(node).localname if isinstance(node.tag, str) else ""


def _pair_top_words(data: bytes, text, spans):
    """Pair direct/top-level source words with their byte spans independently."""
    text_span = next(
        (sp for sp in spans if sp.tag == "text" and sp.inner_start is not None), None
    )
    word_spans = [sp for sp in spans if sp.tag == "w"]
    if text_span is not None:
        word_spans = [
            sp
            for sp in word_spans
            if text_span.inner_start <= sp.outer_start < text_span.inner_end
        ]
    word_spans = [
        sp
        for sp in word_spans
        if not any(
            other is not sp
            and other.outer_start <= sp.outer_start
            and sp.outer_end <= other.outer_end
            for other in word_spans
        )
    ]
    words = [
        node
        for node in text.iter()
        if _lname(node) == "w"
        and not any(_lname(ancestor) == "w" for ancestor in node.iterancestors())
    ]
    if len(words) != len(word_spans):
        raise ValueError(
            f"top-level word/span pairing {len(words)} != {len(word_spans)}"
        )
    return list(zip(words, word_spans))


def source_inventory():
    """Return exact readable pre-line word identities and source census."""
    patches = repair.read_manifest(PATCHES) if PATCHES.is_file() else {}
    expected: dict[tuple[str, str], tuple[str, ...]] = {}
    stats = Counter()

    for path in corpus_files():
        src_file = rel(path)
        if src_file == ENCRYPTED:
            continue
        parsed_path = sourcepath.parse(src_file)
        if not parsed_path.parse_ok or not parsed_path.project:
            raise ValueError(f"invalid production source path: {src_file}")

        original = path.read_bytes()
        data = original
        omap = None
        entry = patches.get(src_file)
        if entry:
            omap = repair.OffsetMap(original, entry[1])
            data = repair.apply(original, entry[1], expect_sha=entry[0])

        try:
            spans = source.scan(data)
            root = ET.fromstring(data)
        except (expat.ExpatError, ET.XMLSyntaxError, ValueError):
            # Same malformed-source eligibility boundary as the production corpus.
            continue

        div1 = root.find("body/div1")
        text = div1.find("text") if div1 is not None else None
        if text is None:
            continue

        pairs = _pair_top_words(data, text, spans)
        by_id = {id(node): sp for node, sp in pairs}
        for node in text.iter():
            tag = _lname(node)
            if tag == "lb":
                break
            if tag != "w" or id(node) not in by_id:
                continue

            stats["preline_words"] += 1
            sp = by_id[id(node)]
            toks = signs.tokenise_word(source.inner_bytes(data, sp))
            readable = [t for t in toks if t.type != "empty"]
            if not readable:
                continue

            stats["readable_words"] += 1
            stats["readable_signs"] += len(readable)
            start, end = sp.outer_start, sp.outer_end
            if omap is not None:
                start, end = omap.span_to_original(start, end)
            key = (src_file, f"{start}-{end}")
            if key in expected:
                raise ValueError(f"duplicate source identity: {key}")
            expected[key] = tuple(t.sym for t in readable)

    return expected, stats


def graph_inventory(tf_dir: Path, provenance_dir: Path):
    """Return graph identities for document-owned words that have no line ancestor."""
    from tf.fabric import Fabric

    # src_span intentionally lives in the optional provenance module. This validation
    # gate needs source identity, so it loads that module explicitly; ordinary users do
    # not pay this cost merely to load the corpus.
    locations = [str(tf_dir)]
    if provenance_dir.is_dir():
        locations.append(str(provenance_dir))
    TF = Fabric(locations=locations, silent="deep")
    api = TF.load("otype src_file src_span sym anchor", silent="deep")
    if api is False or api is None:
        raise RuntimeError(f"cannot load current corpus + provenance from {locations}")
    if api is True:
        api = getattr(TF, "api", None)
    if api is None:
        raise RuntimeError(f"Text-Fabric returned no API for {locations}")

    F, L = api.F, api.L
    actual: dict[tuple[str, str], tuple[str, ...]] = {}
    problems: list[str] = []

    for word in F.otype.s("word"):
        if L.u(word, otype="line"):
            continue
        span = F.src_span.v(word)
        if not span:
            continue
        docs = L.u(word, otype="document")
        if len(docs) != 1:
            problems.append(f"line-less word {word} has {len(docs)} document owners")
            continue
        src_file = F.src_file.v(docs[0])
        slots = tuple(L.d(word, otype="sign"))
        if not slots:
            problems.append(f"line-less word {word} has no sign slots")
            continue
        if any(F.anchor.v(slot) for slot in slots):
            problems.append(f"line-less word {word} contains a technical anchor slot")
        if any(L.u(slot, otype="line") for slot in slots):
            problems.append(f"line-less word {word} sign unexpectedly belongs to a line")
        key = (src_file, span)
        if key in actual:
            problems.append(f"duplicate graph source identity: {key}")
        actual[key] = tuple(F.sym.v(slot) or "" for slot in slots)

    non_anchor = sum(1 for slot in F.otype.s("sign") if not F.anchor.v(slot))
    return actual, non_anchor, problems


def main() -> int:
    expected, src = source_inventory()
    tf_dir = ROOT / "tf" / TF_VERSION
    provenance_dir = ROOT / PROVENANCE_DIR / TF_VERSION
    if not (tf_dir / "otype.tf").is_file():
        print(f"no dataset at {tf_dir}; build it first")
        return 1
    if not provenance_dir.is_dir():
        print(f"no provenance module at {provenance_dir}; build it first")
        return 1

    actual, non_anchor, problems = graph_inventory(tf_dir, provenance_dir)

    if src["preline_words"] != EXPECTED_PRELINE_WORDS:
        problems.append(
            f"source pre-line words {src['preline_words']} != {EXPECTED_PRELINE_WORDS}"
        )
    if src["readable_words"] != EXPECTED_READABLE_WORDS:
        problems.append(
            f"source readable pre-line words {src['readable_words']} != {EXPECTED_READABLE_WORDS}"
        )
    if src["readable_signs"] != EXPECTED_READABLE_SIGNS:
        problems.append(
            f"source readable pre-line signs {src['readable_signs']} != {EXPECTED_READABLE_SIGNS}"
        )

    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    changed = sorted(
        key for key in set(expected) & set(actual) if expected[key] != actual[key]
    )
    if missing:
        problems.append(f"{len(missing)} readable pre-line source word(s) missing from graph")
    if unexpected:
        problems.append(f"{len(unexpected)} unexpected line-less source word(s) in graph")
    if changed:
        problems.append(f"{len(changed)} pre-line word(s) have different sign sequences")
    if non_anchor != EXPECTED_NON_ANCHOR_SIGNS:
        problems.append(
            f"non-anchor signs {non_anchor:,} != {EXPECTED_NON_ANCHOR_SIGNS:,}"
        )

    lines = [
        "# Pre-line source-to-graph conservation",
        "",
        f"- source pre-line words: **{src['preline_words']:,}**",
        f"- readable pre-line words: **{src['readable_words']:,}**",
        f"- readable pre-line signs: **{src['readable_signs']:,}**",
        f"- graph line-less readable words matched by source identity: **{len(actual):,}**",
        f"- total non-anchor graph signs: **{non_anchor:,}**",
        f"- missing identities: **{len(missing):,}**",
        f"- unexpected identities: **{len(unexpected):,}**",
        f"- changed sign sequences: **{len(changed):,}**",
        "",
        "PASS" if not problems else "FAIL",
    ]
    if problems:
        lines.extend(f"- {problem}" for problem in problems)
        for label, keys in (
            ("missing", missing),
            ("unexpected", unexpected),
            ("changed", changed),
        ):
            for key in keys[:20]:
                lines.append(f"  - {label}: `{key[0]}` `{key[1]}`")

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "preline-words.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print("\n".join(lines))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
