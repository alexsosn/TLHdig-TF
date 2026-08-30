"""Every inline AOxml element, and where it goes.

Contract B says every editorial fact becomes a queryable node, edge or feature rather
than surviving only as an opaque string.  Nothing checked that, so constructs the
converter had never been taught about -- `AO:Sumgram`, `AO:ParagrNr` -- passed through
into `srcxml` and stopped there, bytes preserved and meaning invisible.

Declaring a destination for all 61 element names turns "we did not think about this tag"
into a failing gate.  `raw` is a legitimate destination, but it has to be chosen.
"""

from __future__ import annotations

# destination -> what it means
KINDS = {
    "structure": "becomes a node type",
    "wrapper": "sets a writing-system flag on the signs it encloses",
    "damage": "becomes a cluster boundary",
    "annotation": "becomes a valued feature on its sign",
    "layout": "becomes a layout node or a space/separator on a sign",
    "note": "becomes a note node",
    "apparatus": "becomes fragment/document manuscript metadata",
    "raw": "kept verbatim in srcxml only; no derived feature (deliberate)",
    "malformed": "a typo in the source; kept in srcxml, carries no meaning",
}

DESTINATION = {
    # --- structure
    "text": "structure", "w": "structure", "lb": "structure", "clb": "structure",
    "parsep": "structure", "parsep_dbl": "structure",
    # --- writing-system wrappers
    "sGr": "wrapper", "aGr": "wrapper", "d": "wrapper", "num": "wrapper", "c": "wrapper",
    # long-form spellings of sGr/aGr; 212 signs, and the last thing srcxml held alone
    "Sumgram": "wrapper", "Akkgram": "wrapper",
    # --- damage families
    "del_in": "damage", "del_fin": "damage",
    "laes_in": "damage", "laes_fin": "damage",
    "ras_in": "damage", "ras_fin": "damage",
    "add_in": "damage", "add_fin": "damage",
    "QUOT_HurInHit_in": "damage", "QUOT_HurInHit_fin": "damage",
    # `ras_X` marks an erasure of unread signs; it has no partner and no extent.
    "ras_X": "raw",
    # --- valued sign annotations
    "corr": "annotation", "subscr": "annotation",
    "materlect": "annotation", "surpl": "annotation",
    # --- layout
    "space": "layout", "gap": "layout", "tab": "layout", "tabsep": "layout",
    "TabSep": "layout", "wsep": "layout",
    # --- notes and apparatus
    "note": "note",
    "Manuscripts": "apparatus", "TxtPubl": "apparatus", "InvNr": "apparatus",
    "DirectJoin": "apparatus", "InDirectJoin": "apparatus",
    # --- raw only: real annotation the converter does not yet model.  Each of these is
    # a Contract B gap, recorded rather than overlooked.
    "ParagrNr": "raw",        # 3,177 paragraph numbers
    "HitGLOS": "raw", "AkkGLOS": "raw",
    "CTH-Nr": "raw", "KolonNr": "raw", "Textline-Hit": "raw", "numeral": "raw",
    "par": "raw", "cl": "raw", "h": "raw", "bookmark": "raw",
    "LINE_PREFIX": "raw", "PARAGRAPH_LANGUAGE": "raw", "PARSER_ERROR": "raw",
    # ODF styling leaked into the source by the authoring tool
    "P": "raw", "P___Standard": "raw", "P___Footnote": "raw",
    "SP___Page_20_Number": "raw", "SP___AO_3a_-MarkupDef": "raw",
    # --- malformed
    "del_iin": "malformed",   # a mistyped <del_in/>
    "_in": "malformed",
}


def undeclared(names) -> list[str]:
    return sorted(n for n in names if n not in DESTINATION)
