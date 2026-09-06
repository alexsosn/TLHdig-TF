#!/usr/bin/env python
"""One-shot implementation for the raw-siglum RED in issue #18."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARSER = ROOT / "programs" / "tlhdig" / "manuscripts.py"
GRAPH = ROOT / "programs" / "tlhdig" / "manuscript_graph.py"
META = ROOT / "programs" / "tlhdig" / "featuremeta.py"


def replace_once(text: str, old: str, new: str, name: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{name}: expected one match, found {n}")
    return text.replace(old, new, 1)


def patch_parser() -> None:
    text = PARSER.read_text(encoding="utf8")
    text = replace_once(
        text,
        '    siglum_source: str = ""\n    siglum_candidates: tuple[str, ...] = ()\n',
        '    siglum_source: str = ""\n'
        '    siglum_raw: str = ""\n'
        '    siglum_candidates: tuple[str, ...] = ()\n'
        '    siglum_raw_candidates: tuple[str, ...] = ()\n',
        "Entry raw fields",
    )
    old = '''def _candidate(entry: Entry, siglum: str, source: str) -> None:
    """Attach siglum evidence without guessing when sources disagree."""
    if not siglum:
        return
    candidates = list(entry.siglum_candidates)
    if siglum not in candidates:
        candidates.append(siglum)
    entry.siglum_candidates = tuple(candidates)

    if len(candidates) == 1:
        entry.siglum = candidates[0]
        if not entry.siglum_source:
            entry.siglum_source = source
        return

    entry.siglum = ""
    entry.siglum_source = "conflict"
'''
    new = '''def _candidate(entry: Entry, siglum: str, source: str, *, raw: str | None = None) -> None:
    """Attach normalized + raw siglum evidence without guessing on disagreement."""
    if not siglum:
        return
    candidates = list(entry.siglum_candidates)
    if siglum not in candidates:
        candidates.append(siglum)
    entry.siglum_candidates = tuple(candidates)

    raw_value = siglum if raw is None else raw
    raw_candidates = list(entry.siglum_raw_candidates)
    if raw_value and raw_value not in raw_candidates:
        raw_candidates.append(raw_value)
    entry.siglum_raw_candidates = tuple(raw_candidates)

    if len(candidates) == 1:
        entry.siglum = candidates[0]
        if not entry.siglum_source:
            entry.siglum_source = source
            entry.siglum_raw = raw_value
        return

    entry.siglum = ""
    entry.siglum_source = "conflict"
    entry.siglum_raw = ""
'''
    text = replace_once(text, old, new, "candidate function")

    old = '''def _element_entry(element, order: int) -> Entry:
    name = _lname(element)
    raw_label = _normalise("".join(element.itertext()))
    text_match = _SIGLUM_SUFFIX.search(raw_label)
    text_siglum = ""
    if text_match:
        text_siglum = text_match.group(1)
        raw_label = raw_label[: text_match.start()].rstrip()

    result = Entry(order=order, kind=ENTRY_TAGS[name], label=raw_label)
    attr = _normalise(element.get("nr"))
    if attr:
        _candidate(result, attr, "attr")
    if text_siglum:
        _candidate(result, text_siglum, "element-text")
    return result
'''
    new = '''def _element_entry(element, order: int) -> Entry:
    name = _lname(element)
    source_text = "".join(element.itertext())
    text_match = _SIGLUM_SUFFIX.search(source_text)
    text_siglum = ""
    text_siglum_raw = ""
    if text_match:
        text_siglum = text_match.group(1)
        text_siglum_raw = text_match.group(0).strip()
        raw_label = _normalise(source_text[: text_match.start()])
    else:
        raw_label = _normalise(source_text)

    result = Entry(order=order, kind=ENTRY_TAGS[name], label=raw_label)
    attr_raw = element.get("nr") or ""
    attr = _normalise(attr_raw)
    if attr:
        _candidate(result, attr, "attr", raw=attr_raw)
    if text_siglum:
        _candidate(result, text_siglum, "element-text", raw=text_siglum_raw)
    return result
'''
    text = replace_once(text, old, new, "element entry")

    old = '''            entry = Entry(
                order=len(entries) + 1,
                kind="plain",
                label=label,
                siglum=match.group("siglum"),
                siglum_source="plain-text",
                siglum_candidates=(match.group("siglum"),),
            )
'''
    new = '''            raw_siglum_match = _ANY_SIGLUM.search(match.group(0))
            raw_siglum = raw_siglum_match.group(0) if raw_siglum_match else match.group("siglum")
            entry = Entry(
                order=len(entries) + 1,
                kind="plain",
                label=label,
                siglum=match.group("siglum"),
                siglum_source="plain-text",
                siglum_raw=raw_siglum,
                siglum_candidates=(match.group("siglum"),),
                siglum_raw_candidates=(raw_siglum,),
            )
'''
    text = replace_once(text, old, new, "plain entry")
    text = replace_once(
        text,
        '            _candidate(attach_to, match.group(1), "tail")\n',
        '            _candidate(attach_to, match.group(1), "tail", raw=match.group(0).strip())\n',
        "tail siglum",
    )
    PARSER.write_text(text, encoding="utf8")


def patch_graph() -> None:
    text = GRAPH.read_text(encoding="utf8")
    old = '''        if entry.siglum_source:
            features["siglum_source"] = entry.siglum_source
        if entry.siglum and entry.siglum in apparatus.duplicate_sigla:
'''
    new = '''        if entry.siglum_source:
            features["siglum_source"] = entry.siglum_source
        if entry.siglum_raw:
            features["frag_raw"] = entry.siglum_raw
        if len(entry.siglum_raw_candidates) > 1:
            features["siglum_raw_candidates"] = " | ".join(entry.siglum_raw_candidates)
        if entry.siglum and entry.siglum in apparatus.duplicate_sigla:
'''
    text = replace_once(text, old, new, "graph raw features")
    GRAPH.write_text(text, encoding="utf8")


def patch_meta() -> None:
    text = META.read_text(encoding="utf8")
    old = '''    "siglum_source": "where this fragment siglum was recovered: attr | element-text | tail | plain-text | conflict",
    "siglum_ambiguous": "1 when this source siglum names more than one apparatus-entry occurrence in the document",
    "siglum_candidates": "conflicting source siglum candidates, preserved without choosing one",
'''
    new = '''    "siglum_source": "where this fragment siglum was recovered: attr | element-text | tail | plain-text | conflict",
    "frag_raw": "raw source spelling of the siglum evidence selected for this fragment occurrence; `frag` is the normalized lookup value",
    "siglum_ambiguous": "1 when this source siglum names more than one apparatus-entry occurrence in the document",
    "siglum_candidates": "conflicting normalized source siglum candidates, preserved without choosing one",
    "siglum_raw_candidates": "multiple raw source spellings/candidates for this occurrence, preserved in source-evidence order",
'''
    text = replace_once(text, old, new, "feature metadata")
    META.write_text(text, encoding="utf8")


def main() -> int:
    patch_parser()
    patch_graph()
    patch_meta()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
