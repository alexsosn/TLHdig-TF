"""The `mrp` morphological annotation (plan §7.5, research §4).

An `mrpN` value is a base morph record, optionally followed by one clitic record.
Fields are `@`-delimited and the determinative is always the *last* field of the whole
string:

    base    lemma @ gloss @ morphtag @ stemclass            [@ det]
    clitic                  lemma @ morphtag @ stemclass    [@ det]

Two traps, both measured against the corpus and documented in the plan:

* The separator has four surface forms -- ' += ', '@+= ', ' +@', '@+@'.  Splitting on
  '+=' alone mishandles 5,655 values.
* `rstrip("@")` on the base destroys 794,637 values: a no-clitic analysis legitimately
  ends in '@' because its determinative field is empty, and rstrip deletes the field.

Index handling matters too.  The attribute index space starts at **0** (`mrp0` is a real
analysis slot on 201 words, and `mrp0sel="??? 0a"` resolves against it), numbering has
gaps on 292 words, and 19,081 words do not start at `mrp1`.  Indices are therefore read
from the attribute name, never assigned by enumeration order.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

MRP_ATTR = re.compile(r"^mrp(\d+)$")

# Captures an optional '@' *terminator* before the separator, so we can tell the
# '@+= ' form (where the '@' ends the base's last field) from ' += ' (where it
# does not).  Only the first separator is consumed.
#
# The bare-'+' variants are anchored on a following '@'.  A '+' is otherwise an
# ordinary character in this corpus: lemmas such as '+n' (the numeral "n") start with
# one, and morph tags such as 'Anrufung:GEN.SG+Herr:NOM.SG' contain one.  An
# unanchored r"\+=?" splits both, which silently mangled 1,383 analyses.
SEPARATOR = re.compile(r"(@?)[ \t]*(?:\+=|\+(?=@))[ \t]*")

# Lettered alternative sets: "{ a → NOM.SG(UNM)} { b → ACC.SG(UNM)}"
ALT = re.compile(r"\{\s*(\w+)\s*→\s*([^}]*)\}")

# Field 4 holds a paradigm number, a part of speech, or logographic morphology.
# The closed vocabulary is the primary discriminator; leading whitespace is only a
# consistency signal (65 values occur both with and without it).
KNOWN_POS = frozenset(
    """ADV POSP PREV CNJ NEG INTJ INDCL QUANcar QUANmul QUANord
       DEMadv INTadv INDadv""".split()
)
PARADIGM = re.compile(r"^[IVX]+(\.\d+)*$|^\d+(\.\d+)*$")


@dataclass(slots=True)
class Record:
    """One morph record -- either the base or its clitic."""

    lemma: str = ""
    gloss: str = ""
    morph: str = ""
    stemclass: str = ""
    det: str = ""
    alts: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class Analysis:
    """One `mrpN` attribute, parsed."""

    index: int
    raw: str
    sep: str = ""            # which separator form, "" when there is no clitic
    base: Record = field(default_factory=Record)
    clitic: Record | None = None
    field4_kind: str = ""    # stemclass | pos | morph | empty
    pos: str = ""
    ok: bool = True
    note: str = ""

    def alt_map_json(self) -> str:
        return json.dumps(
            {"base": self.base.alts, "clitic": (self.clitic.alts if self.clitic else {})},
            ensure_ascii=False,
            sort_keys=True,
        )


def classify_field4(value: str) -> tuple[str, str]:
    """Return (kind, pos) for the stem-class slot."""
    t = value.strip()
    if not t:
        return "empty", ""
    if t in KNOWN_POS:
        return "pos", t
    if PARADIGM.match(t):
        return "stemclass", ""
    # compounds such as "ADV, POSP, PREV"
    parts = [p.strip() for p in re.split(r"[,/|]| \|\| ", t) if p.strip()]
    if parts and all(p in KNOWN_POS for p in parts):
        return "pos", " ".join(parts)
    return "morph", ""


def _alts(morph: str) -> dict[str, str]:
    return {k: v.strip() for k, v in ALT.findall(morph)}


def parse(index: int, raw: str) -> Analysis:
    """Parse one `mrpN` value.  Never raises; failures set ``ok=False``."""
    a = Analysis(index=index, raw=raw)

    m = SEPARATOR.search(raw)
    if m and "+" in m.group(0):
        base_s = raw[: m.start()]
        clit_s = raw[m.end() :]
        a.sep = m.group(0)
    else:
        base_s, clit_s = raw, None

    bf = base_s.split("@")           # never rstrip: the empty det field is meaningful

    # A value may consist of a clitic alone -- " += ma@CNJctr@@ m" -- where the word is
    # nothing but an enclitic.  That is a real encoding pattern, not an anomaly.
    if clit_s is not None and not base_s.strip():
        cf = clit_s.split("@")
        c = Record(lemma=cf[0])
        c.morph = cf[1] if len(cf) > 1 else ""
        c.stemclass = cf[2] if len(cf) > 2 else ""
        c.det = cf[3] if len(cf) > 3 else ""
        c.alts = _alts(c.morph)
        a.clitic = c
        a.field4_kind = "empty"
        a.note = "clitic-only"
        return a

    if len(bf) < 3:
        a.ok = False
        a.note = f"base has {len(bf)} field(s)"
        a.base.lemma = bf[0] if bf else ""
        if len(bf) > 1:
            a.base.gloss = bf[1]
        return a

    a.base.lemma, a.base.gloss, a.base.morph = bf[0], bf[1], bf[2]
    a.base.stemclass = bf[3] if len(bf) > 3 else ""
    a.base.alts = _alts(a.base.morph)

    if clit_s is None:
        a.base.det = bf[4] if len(bf) > 4 else ""
        if len(bf) > 5:
            a.ok = False
            a.note = f"base has {len(bf)} fields"
    else:
        cf = clit_s.split("@")
        c = Record(lemma=cf[0])
        c.morph = cf[1] if len(cf) > 1 else ""
        c.stemclass = cf[2] if len(cf) > 2 else ""
        c.det = cf[3] if len(cf) > 3 else ""
        c.alts = _alts(c.morph)
        a.clitic = c
        if len(cf) > 4:
            a.ok = False
            a.note = f"clitic has {len(cf)} fields"

    a.field4_kind, a.pos = classify_field4(a.base.stemclass)
    return a


def analyses(attrib: dict[str, str]) -> list[Analysis]:
    """Every `mrpN` on a <w>, in index order.  `mrp0sel` is not an analysis."""
    out = []
    for k, v in attrib.items():
        m = MRP_ATTR.match(k)
        if m:
            out.append(parse(int(m.group(1)), v))
    out.sort(key=lambda a: a.index)
    return out


# --------------------------------------------------------------------------- mrp0sel

SEL_TOKEN = re.compile(r"^(\d+)([A-Za-z]*)$")
SEL_KINDS = {"DEL", "AKK", "HURR", "HAT", "SUM", "LUW"}
GROUPS = {"all", "sg", "pl"}


@dataclass(slots=True)
class Selector:
    """One selector token, e.g. `1bR` -> index 1, base `b`, clitic `R`."""

    index: int
    base_alt: str = ""
    clitic_alt: str = ""
    group: str = ""
    raw: str = ""


@dataclass(slots=True)
class Selection:
    kind: str = "none"       # analysis | none | unknown | DEL | AKK | HURR | HAT | SUM | LUW
    index: int | None = None
    base_alt: str = ""       # lower-case letters, base alternatives
    clitic_alt: str = ""     # upper-case letters, clitic alternatives
    group: str = ""          # all | sg | pl
    raw: str = ""
    multiple: bool = False   # several selectors given, e.g. " 1a 1b "
    # Every numeric selector, in source order.  20,907 words name more than one:
    # 7,290 select several *analyses* (`1 2a`), 13,617 several alternatives of one
    # (`1bR 1bS`).  Reading only the first silently discarded the editor's other
    # choices, and the scalar fields below are the first selector for compatibility.
    selectors: list = field(default_factory=list)


def parse_selection(value: str | None) -> Selection:
    """Parse `mrp0sel`.  Padding is not significant."""
    s = Selection(raw=value or "")
    if value is None:
        return s
    toks = value.split()
    if not toks:
        return s
    s.multiple = len(toks) > 1

    # A marker such as "???" or "AKK" sets the kind, but a numeric token may still
    # follow it ("??? 0a" = unresolved, with mrp0/a as the editor's fallback hint).
    # Returning early there would discard the index, so keep parsing.
    for t in toks:
        if t in SEL_KINDS:
            s.kind = t
        elif t == "???":
            s.kind = "unknown"

    for t in toks:
        m = SEL_TOKEN.match(t)
        if m:
            s.selectors.append(_selector(m, t))
    if not s.selectors:
        if s.kind == "none":
            s.kind = "unknown"
        return s

    if s.kind == "none":
        s.kind = "analysis"
    # The scalar fields keep their old meaning -- the first selector -- so existing
    # callers are unaffected; `selectors` carries the rest.
    first = s.selectors[0]
    s.index = first.index
    s.base_alt = first.base_alt
    s.clitic_alt = first.clitic_alt
    s.group = first.group
    return s


def _selector(m, raw: str) -> Selector:
    sel = Selector(index=int(m.group(1)), raw=raw)
    letters = m.group(2)
    if letters in GROUPS:
        sel.group = letters
        return sel
    sel.base_alt = "".join(c for c in letters if c.islower())
    sel.clitic_alt = "".join(c for c in letters if c.isupper())
    # 'sg'/'pl' can trail a letter run; split them off if present
    for g in ("sg", "pl"):
        if sel.base_alt.endswith(g):
            sel.base_alt = sel.base_alt[: -len(g)]
            sel.group = g
    return sel
