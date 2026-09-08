"""AOxml declaration contracts for body and document header.

Contract B requires every source construct accepted by the converter to have an
explicit disposition. Body markup and AOHeader metadata have different preservation
semantics, so they are declared separately: body ``raw`` survives in provenance,
whereas current header losses are called ``known-unpreserved`` explicitly.
"""

from __future__ import annotations

# Body destination -> what it means.
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
    "text": "structure", "w": "structure", "lb": "structure", "clb": "structure",
    "parsep": "structure", "parsep_dbl": "structure",
    "sGr": "wrapper", "aGr": "wrapper", "d": "wrapper", "num": "wrapper", "c": "wrapper",
    "Sumgram": "wrapper", "Akkgram": "wrapper",
    "del_in": "damage", "del_fin": "damage",
    "laes_in": "damage", "laes_fin": "damage",
    "ras_in": "damage", "ras_fin": "damage",
    "add_in": "damage", "add_fin": "damage",
    "QUOT_HurInHit_in": "damage", "QUOT_HurInHit_fin": "damage",
    "ras_X": "raw",
    "corr": "annotation", "subscr": "annotation",
    "materlect": "annotation", "surpl": "annotation",
    "space": "layout", "gap": "layout", "tab": "layout", "tabsep": "layout",
    "TabSep": "layout", "wsep": "layout",
    "note": "note",
    "Manuscripts": "apparatus", "TxtPubl": "apparatus", "InvNr": "apparatus",
    "DirectJoin": "apparatus", "InDirectJoin": "apparatus",
    "ParagrNr": "raw",
    "HitGLOS": "raw", "AkkGLOS": "raw",
    "CTH-Nr": "raw", "KolonNr": "raw", "Textline-Hit": "raw", "numeral": "raw",
    "par": "raw", "cl": "raw", "h": "raw", "bookmark": "raw",
    "LINE_PREFIX": "raw", "PARAGRAPH_LANGUAGE": "raw", "PARSER_ERROR": "raw",
    "P": "raw", "P___Standard": "raw", "P___Footnote": "raw",
    "SP___Page_20_Number": "raw", "SP___AO_3a_-MarkupDef": "raw",
    "del_iin": "malformed", "_in": "malformed",
}

# Canonical public declaration of the converter's edit contract. The converter's
# private compatibility aliases are regression-tested against these values so a future
# converter change cannot silently drift away from Contract B.
EDIT_KINDS = frozenset({
    "kor", "kor2", "kor1kf", "annot", "uebern", "format", "author", "kolon",
    "val", "trlst", "join", "merge", "aufheb", "aufloes", "korof", "koltaf",
    "kolfot", "kolfot2", "cth", "creation-date", "AOxml-creation",
})
EDIT_ATTRS = (
    "editor", "date", "part", "src", "frgm", "docs", "comment",
    "author", "alt", "neu",
)

HEADER_KINDS = {
    "structure": "AOHeader/container syntax; no claim of byte preservation",
    "document-feature": "consumed directly into a document feature",
    "edit": "edit event is represented; declared attribute retained only when non-empty",
    "known-unpreserved": "known source data currently dropped; follow-up #57/#58",
    "malformed-unpreserved": "known malformed source data currently dropped",
}

HEADER_DESTINATION = {
    "AOHeader": "structure", "meta": "structure", "annotation": "structure", "neu": "structure",
    "docID": "document-feature",
    **{name: "edit" for name in EDIT_KINDS},
    "merged": "known-unpreserved", "doc": "known-unpreserved", "mDocID": "known-unpreserved",
    "mDodID": "malformed-unpreserved", "ann": "malformed-unpreserved",
}

# Exact element-qualified attribute vocabulary observed by the hosted corpus gate on
# TLHdig 0.3: 73 pairs. There is intentionally no wildcard or global attribute
# allowance: a new attribute on an otherwise-known element must fail Contract B.
_EDIT_ATTR_PAIRS = {
    ("AOxml-creation", "date"),
    ("annot", "comment"), ("annot", "date"), ("annot", "editor"), ("annot", "part"),
    ("aufheb", "date"), ("aufheb", "editor"), ("aufheb", "frgm"), ("aufheb", "part"),
    ("aufloes", "date"), ("aufloes", "editor"), ("aufloes", "frgm"), ("aufloes", "part"),
    ("author", "author"), ("author", "date"),
    ("creation-date", "date"),
    ("cth", "alt"), ("cth", "date"), ("cth", "editor"), ("cth", "neu"), ("cth", "part"),
    ("format", "comment"), ("format", "date"), ("format", "editor"), ("format", "part"),
    ("join", "date"), ("join", "editor"), ("join", "frgm"), ("join", "part"),
    ("kolfot", "date"), ("kolfot", "editor"), ("kolfot", "part"),
    ("kolfot2", "comment"), ("kolfot2", "date"), ("kolfot2", "editor"),
    ("kolon", "comment"), ("kolon", "date"), ("kolon", "editor"), ("kolon", "part"),
    ("koltaf", "date"), ("koltaf", "editor"), ("koltaf", "frgm"), ("koltaf", "part"),
    ("kor", "comment"), ("kor", "date"), ("kor", "editor"), ("kor", "part"),
    ("kor1kf", "date"), ("kor1kf", "editor"), ("kor1kf", "part"),
    ("kor2", "date"), ("kor2", "editor"), ("kor2", "part"),
    ("korof", "date"), ("korof", "editor"), ("korof", "part"),
    ("merge", "date"), ("merge", "docs"), ("merge", "editor"),
    ("trlst", "date"), ("trlst", "editor"), ("trlst", "part"),
    ("uebern", "date"), ("uebern", "editor"), ("uebern", "part"), ("uebern", "src"),
    ("val", "date"), ("val", "editor"), ("val", "part"),
}
_MALFORMED_ATTR_PAIRS = {
    ("ann", "date"), ("ann", "editor"), ("ann", "part"),
}
HEADER_ATTR_DESTINATION = {
    **{pair: "edit" for pair in _EDIT_ATTR_PAIRS},
    ("annot", "data"): "known-unpreserved",
    **{pair: "malformed-unpreserved" for pair in _MALFORMED_ATTR_PAIRS},
}

# A path can be lossy even when its tag/attribute vocabulary is otherwise known.
# TLHdig 0.3 has three direct AOHeader/annot siblings in KBo 46.102+. The converter
# only consumes AOHeader/meta//*, so these are tracked explicitly rather than weakening
# the structural contract for every edit kind or every possible placement.
HEADER_PLACEMENT_DESTINATION = {
    ("AOHeader", "annot"): "known-unpreserved",
}
HEADER_PLACEMENT_ATTR_DESTINATION = {
    ("AOHeader", "annot", "editor"): "known-unpreserved",
    ("AOHeader", "annot", "data"): "known-unpreserved",
}


def undeclared(names) -> list[str]:
    return sorted(n for n in names if n not in DESTINATION)


def header_undeclared(names) -> list[str]:
    return sorted(n for n in names if n not in HEADER_DESTINATION)


def header_attrs_undeclared(pairs) -> list[tuple[str, str]]:
    return sorted(p for p in pairs if p not in HEADER_ATTR_DESTINATION)
