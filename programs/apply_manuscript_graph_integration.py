#!/usr/bin/env python
"""One-shot, assertion-heavy converter integration for issue #18.

This exists because the graph RED was deliberately committed before production code.
It performs narrow textual edits, refusing to touch a converter that no longer matches
the reviewed pre-integration shape. The workflow removes this file after tests pass.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONVERT = ROOT / "programs" / "tlhdig" / "convert.py"
META = ROOT / "programs" / "tlhdig" / "featuremeta.py"


def replace_once(text: str, old: str, new: str, *, name: str) -> str:
    count = text.count(old)
    if count == 0 and new in text:
        return text
    if count != 1:
        raise SystemExit(f"{name}: expected exactly one pre-integration match, found {count}")
    return text.replace(old, new, 1)


def patch_convert() -> None:
    text = CONVERT.read_text(encoding="utf8")
    text = replace_once(
        text,
        "from . import cuneiform, lineref, morph, repair, signs, source, sourcepath\n",
        "from . import (\n"
        "    cuneiform, lineref, manuscript_graph, manuscripts, morph, repair, signs, source,\n"
        "    sourcepath,\n"
        ")\n",
        name="converter imports",
    )
    text = replace_once(
        text,
        '    "parse_ok", "materlect_anomalous", "srcln", "anchor",\n',
        '    "parse_ok", "materlect_anomalous", "srcln", "anchor",\n'
        '    "fragment_order", "siglum_ambiguous", "join_order", "join_resolved",\n',
        name="integer features",
    )

    start = text.index("def _manuscripts(cv, text_el, doc, state) -> None:\n")
    end = text.index("\n\ndef _has_readable_sign", start)
    replacement = '''def _manuscripts(cv, text_el, doc, state) -> None:
    """Parse the ordered manuscript apparatus for later graph emission.

    Source joins are separators between apparatus-entry occurrences, including legacy
    textual notation in mixed content.  The pure parser owns that grammar; this function
    only records the parsed apparatus on conversion state and keeps the useful document-
    level inventory-number summary for compatibility.
    """
    block = text_el.find(f"{_AO}Manuscripts")
    if block is None:
        return
    state.manuscripts = manuscripts.parse(block)
    invnr = [entry.label for entry in state.manuscripts.entries if entry.kind == "invnr"]
    if invnr:
        cv.feature(doc, invnr=" | ".join(invnr))
'''
    current = text[start:end]
    if "state.manuscripts = manuscripts.parse(block)" not in current:
        text = text[:start] + replacement + text[end:]

    text = replace_once(
        text,
        "    if state.slots:\n        frag_slots: dict[str, set] = {}\n",
        "    if state.slots:\n"
        "        manuscript_graph.emit(\n"
        "            cv, state.manuscripts, doc,\n"
        "            line_frag=state.line_frag, line_extent=state.line_extent,\n"
        "            lines_with_slots=state.lines_with_slots, document_slots=state.slots,\n"
        "        )\n"
        "        frag_slots: dict[str, set] = {}\n",
        name="graph emission",
    )
    text = replace_once(
        text,
        "        self.fragments: dict[str, tuple[str, str]] = {}   # key -> (siglum, txtpubl)\n",
        "        self.manuscripts = None\n"
        "        # Kept empty during the migration commit so the old fragment loop below is a\n"
        "        # no-op; issue #18 graph emission is occurrence-based in manuscript_graph.\n"
        "        self.fragments: dict[str, tuple[str, str]] = {}   # legacy, intentionally empty\n",
        name="state apparatus",
    )
    CONVERT.write_text(text, encoding="utf8")


def patch_meta() -> None:
    text = META.read_text(encoding="utf8")
    text = replace_once(
        text,
        '    "nrecords": "number of document records that claim this manuscript identity",\n'
        '    "txtpubl": "publication siglum of a constituent manuscript",\n'
        '    "invnr": "excavation / inventory numbers recorded for the document",\n'
        '    "directjoin": "manuscripts joined directly to this one",\n'
        '    "indirectjoin": "manuscripts joined indirectly to this one",\n',
        '    "nrecords": "number of document records that claim this manuscript identity",\n'
        '    "fragment_order": "1-based occurrence order in the source AO:Manuscripts apparatus",\n'
        '    "fragment_kind": "source apparatus-entry kind: txtpubl | invnr | plain",\n'
        '    "fragment_label": "visible label of this source manuscript-entry occurrence",\n'
        '    "txtpubl": "publication label of a constituent manuscript occurrence",\n'
        '    "invnr": "inventory number; on fragment nodes this is the source apparatus entry, and on document nodes the compatibility summary",\n'
        '    "siglum_source": "where this fragment siglum was recovered: attr | element-text | tail | plain-text | conflict",\n'
        '    "siglum_ambiguous": "1 when this source siglum names more than one apparatus-entry occurrence in the document",\n'
        '    "siglum_candidates": "conflicting source siglum candidates, preserved without choosing one",\n'
        '    "join_kind": "source manuscript-join state: direct | indirect | direct-multi | indirect-multi | uncertain | malformed | unknown",\n'
        '    "join_encoding": "source serialization of this manuscript join statement: xml | textual",\n'
        '    "join_raw": "literal source join operator or textual marker",\n'
        '    "join_order": "1-based join-statement order inside the source manuscript apparatus",\n'
        '    "join_resolved": "1 when both endpoint occurrences exist and the source state is confidently direct or indirect",\n'
        '    "join_reason": "diagnostic reason a manuscript join statement was not promoted to a confident binary relation",\n',
        name="manuscript node metadata",
    )
    text = replace_once(
        text,
        '    "witness": "line -> the fragment(s) it is attested on; many-to-many, since an lnr "\n'
        '               "siglum may be composite (EUR1+2)",\n',
        '    "witness": "line -> the fragment occurrence(s) it is attested on; many-to-many for composite or ambiguous source sigla",\n'
        '    "witness_resolution": "line -> fragment resolution status: unique | ambiguous; valued companion to witness",\n'
        '    "joinLeft": "joinstmt -> left apparatus-entry occurrence in source order, when recoverable",\n'
        '    "joinRight": "joinstmt -> right apparatus-entry occurrence in source order, when recoverable",\n'
        '    "joinDocument": "joinstmt -> document containing the source manuscript apparatus",\n'
        '    "joined": "fragment -> fragment convenience relation valued direct/indirect; orientation preserves source apparatus order only, with no inferred reverse or transitive edges",\n',
        name="manuscript edge metadata",
    )
    META.write_text(text, encoding="utf8")


def main() -> int:
    patch_convert()
    patch_meta()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
