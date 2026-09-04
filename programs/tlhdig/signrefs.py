"""External sign lists, read so that they can judge our alignment.

The whole cuneiform layer was measured against `programs/signmap.tsv`, which is learned
from this corpus by the same reasoning it is meant to check. That was noted as a
weakness and then demonstrated to be one: the learned table gives `MEŠ` -> 𒈨 at 0.57
confidence over 197 observations, and those 197 are precisely the lines where the
alignment had shifted (research §9). A witness assembled from the defendant's testimony
acquits every time.

These five lists were made elsewhere, for other reasons, by people who never saw
TLHdig:

    osl          oracc/ogsl `00lib/osl.asl`   CC0           2,568 signs, 12,147 readings
    potnia       AncientNLP/potnia            Apache-2.0    Hittite, 352 readings
    tfFromAtf    Nino-cunei/tfFromAtf         MIT           ATF -> Unicode, 1,123
    enmerkar     eggrobin/Enmerkar            CC BY-SA 3.0  OGSL-derived, 1,896 signs
    wiktionary   Module:hit-translit          CC BY-SA      HZL-based, 1,254 readings
    nuolenna     tosaja/Nuolenna              AGPL-3.0+     12,612 readings

They are read at build time and never redistributed: `refs/` is git-ignored, and what
this produces is agreement counts and a list of disagreements, which are facts about
our data rather than copies of theirs.

They disagree with each other, and that is the point: one list would be another
authority to defer to, five vote, and a split says the sign is contested rather than
that we are wrong.

They also disagree with us for a reason that is not disagreement at all. Unicode encodes
some signs twice, so `ku` is 𒂉 in HPM's font and 𒆪 in every list -- the same sign, both
numbered 206 in the Zeichenlexikon, rendering alike. Comparing codepoints instead of
signs made 32,890 false accusations, half of everything the lists seemed to object to.
`equivalents` folds those together, from the numbers the source carries for the purpose.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# Homophone indices. A sign value's index is written three ways depending on its size,
# and each list picks one: 1 unmarked, 2 an acute, 3 a grave, 4 and up a subscript.
# ATF writes them all as ASCII digits, so `sze3` and `ŠÈ` are one reading, and a
# comparison that misses that reports a disagreement where there is agreement.
ACUTE = "́"
GRAVE = "̀"
SUBSCRIPT = {str(d): chr(0x2080 + d) for d in range(10)}
VOWELS = "aeiouAEIOU"

# ATF writes what Assyriology prints with diacritics.
DIGRAPHS = (("sz", "š"), ("SZ", "Š"), ("s,", "ṣ"), ("S,", "Ṣ"), ("t,", "ṭ"), ("T,", "Ṭ"))

_INDEX = re.compile(r"^(.*?[A-Za-zŠšṢṣṬṭḪḫ])([0-9]+)$")


def normalise(reading: str, atf: bool = False) -> str:
    """One house's spelling of a reading, rewritten as TLHdig spells it.

    `atf=True` additionally reads `h` as `ḫ`, which is right for the ATF lists -- ATF
    has no plain `h` -- and wrong for the lists that already write `ḫ` themselves.
    """
    if not reading:
        return reading
    out = reading
    for a, b in DIGRAPHS:
        out = out.replace(a, b)
    if atf:
        out = out.replace("h", "ḫ").replace("H", "Ḫ")

    m = _INDEX.match(out)
    if not m:
        return unicodedata.normalize("NFC", out)
    stem, digits = m.group(1), m.group(2)
    if digits == "2" or digits == "3":
        mark = ACUTE if digits == "2" else GRAVE
        # The mark lands on the *last* vowel: `ezen2` is `ezén`, not `ézen`.
        for i in range(len(stem) - 1, -1, -1):
            if stem[i] in VOWELS:
                return unicodedata.normalize("NFC", stem[: i + 1] + mark + stem[i + 1 :])
        return unicodedata.normalize("NFC", stem + digits)
    return unicodedata.normalize("NFC", stem + "".join(SUBSCRIPT[d] for d in digits))


@dataclass(slots=True)
class Verdict:
    """What the lists say about one (reading, glyph) pair."""

    support: int = 0        # lists that attest this glyph for this reading
    against: int = 0        # lists that know the reading and attest something else
    unknown: bool = False   # no list knows the reading at all
    alternatives: set = field(default_factory=set)


class References:
    """reading -> {source: {glyphs}}, with codepoints that are one sign folded together.

    `equivalents` maps a codepoint to every codepoint that is the same sign. Without it
    the commonest "disagreement" in the corpus is a false accusation: 𒂉 and 𒆪 render
    alike and the Zeichenlexikon numbers them both 206, but Unicode encodes them apart
    and the lists file `ku` under one while HPM's font writes the other -- 32,890 signs
    of nothing.
    """

    def __init__(self, table: dict, equivalents: dict | None = None):
        self.table = table
        self.equiv = equivalents or {}

    def _same(self, glyph: str) -> set:
        return self.equiv.get(glyph, {glyph})

    def __len__(self) -> int:
        return len(self.table)

    def sources(self, reading: str) -> set:
        return set(self.table.get(reading, {}))

    def lineages(self, reading: str) -> set:
        """The distinct scholarly traditions behind the sources that know this reading.

        Fewer than `sources`, whenever two lists descend from one sign list.
        """
        return {LINEAGE.get(s, s) for s in self.table.get(reading, {})}

    def contested(self, reading: str) -> bool:
        """Do the lists disagree among themselves about this reading?"""
        seen = self.table.get(reading)
        if not seen:
            return False
        glyphs = set()
        for g in seen.values():
            glyphs |= g
        return len(glyphs) > 1

    def verdict(self, reading: str, glyph: str) -> Verdict:
        seen = self.table.get(reading)
        if not seen:
            return Verdict(unknown=True)
        v = Verdict()
        same = self._same(glyph)
        for src, glyphs in seen.items():
            if glyphs & same:
                v.support += 1
            else:
                v.against += 1
                v.alternatives |= glyphs
        return v


# ------------------------------------------------------------------- loaders
#
# Each list is read in its own shape and every reading passes through `normalise`, so
# what comes out is comparable with `sym`.

def _add(table, reading, glyph, source):
    if not reading or not glyph:
        return
    table.setdefault(reading, {}).setdefault(source, set()).add(glyph)


def _potnia(path: Path, table):
    row = re.compile(r'\s*"([^"]+)"\s*:\s*"?([^\s"#]+)"?')
    for line in path.read_text(encoding="utf8").splitlines():
        m = row.match(line)
        if m and m.group(2) != "??":
            _add(table, normalise(m.group(1)), m.group(2), "potnia")


def _nuolenna(path: Path, table):
    for line in path.read_text(encoding="utf8").splitlines():
        if "\t" not in line:
            continue
        reading, glyph = line.split("\t", 1)
        # Nuolenna also lists sign *names* as compositions -- `(4×za)×kur` -- which are
        # descriptions of a shape, not readings anyone transliterates.
        if "×" in reading or "&" in reading or "@" in reading:
            continue
        _add(table, normalise(reading), glyph, "nuolenna")


def _tffromatf(path: Path, table):
    for line in path.read_text(encoding="utf8").splitlines():
        if "\t" not in line:
            continue
        reading, glyph = line.split("\t", 1)
        if "(" in reading:          # `1(asz)`: a number with its metrological unit
            continue
        _add(table, normalise(reading, atf=True), glyph, "tffromatf")


def _balanced(text: str) -> str:
    """The first parenthesised group, matched to its own closing bracket.

    Enmerkar nests: `(1, ANA3, AŠ (MesZL: see also U.DAR (nos. 670+183)), AŠA, ...)`.
    Stopping at the first `)` -- which is what a `[^)]*` pattern does -- truncated the
    reading list on 1,089 of the 1,889 sign rows and dropped some 4,970 readings, so
    Enmerkar abstained wherever its evidence sat after an annotation.
    """
    i = text.find("(")
    if i < 0:
        return ""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[i + 1 : j]
    return text[i + 1 :]


def _unnest(text: str) -> str:
    """Drop the nested annotations, so a comma split cannot cut one in half."""
    out, depth = [], 0
    for c in text:
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(c)
    return "".join(out)


def _enmerkar(path: Path, table):
    with path.open(encoding="utf8", newline="") as fh:
        for row in csv.reader(fh):
            if len(row) < 3 or not row[0]:
                continue
            glyph, names = row[0], row[2].replace("\n", " ")
            head = names.split("(")[0].strip()
            candidates = [head] + _unnest(_balanced(names)).split(",")
            for name in candidates:
                # OGSL annotates freely: `AŠ (MesZL: see also ...)`. Only the bare name.
                name = re.sub(r"\s*[:(].*", "", name).strip()
                if name and len(name) < 20 and " " not in name and ")" not in name:
                    _add(table, normalise(name), glyph, "enmerkar")


_OSL_TAG = re.compile(r"^@(\w+)\s+(.*?)\s*$")


def _osl_blocks(path: Path):
    """Walk `osl.asl`, yielding one dict per `@sign`.

    Fields are tab-separated. `@form` opens a subblock for a graphic variant with its
    own `@ucun`, and letting one of those displace the sign's own codepoint moved
    measured agreement with OSL from 78.5% to 96.2% -- so only the first, outside any
    form, counts.
    """
    cur = None
    in_form = False
    for raw in path.read_text(encoding="utf8").splitlines():
        m = _OSL_TAG.match(raw)
        if not m:
            continue
        tag, val = m.group(1), m.group(2)
        if tag == "sign":
            if cur:
                yield cur
            cur = {"name": val, "ucun": None, "v": set(), "hzl": set()}
            in_form = False
        elif tag == "form":
            in_form = True
        elif tag == "end":
            if cur:
                yield cur
            cur, in_form = None, False
        elif cur is None:
            continue
        elif tag == "ucun" and not in_form and cur["ucun"] is None:
            cur["ucun"] = val
        elif tag == "v":
            # `@v` may carry qualifiers: `%akk`, `aš/dil`, a trailing `?`, or a leading
            # `-` for a value that is not the sign's own.
            v = (val.split() or [""])[0].lstrip("%*").split("/")[0].rstrip("?")
            if v and not v.startswith("-"):
                cur["v"].add(v)
        elif tag == "list" and val.startswith("HZL"):
            n = re.match(r"HZL0*(\d+)", val)
            if n:
                cur["hzl"].add(n.group(1))
    if cur:
        yield cur


def _osl(path: Path, table):
    for sign in _osl_blocks(path):
        if not sign["ucun"]:
            continue
        for v in sign["v"] | {sign["name"]}:
            _add(table, normalise(v), sign["ucun"], "osl")


def osl_equivalents(path: Path) -> dict:
    """Codepoints sharing a Zeichenlexikon number, read from OSL's cross-references.

    OSL is a general Mesopotamian list but files HZL numbers alongside its own, which
    makes it the widest source of these classes: 31 against the 9 the Hittite module
    alone gives. The new ones matter -- HZL 20 holds 𒁇 and 𒈦 together, so `pár` and
    `bar` stop being disagreements.
    """
    by_number: dict = {}
    for sign in _osl_blocks(path):
        if not sign["ucun"]:
            continue
        for h in sign["hzl"]:
            by_number.setdefault(h, set()).add(sign["ucun"])
    out: dict = {}
    for glyphs in by_number.values():
        if len(glyphs) < 2:
            continue
        for g in glyphs:
            out.setdefault(g, set()).update(glyphs)
    return out


def _wiktionary(path: Path, table):
    txt = path.read_text(encoding="utf8")
    body = txt[txt.index("export.sign_list = {"):]
    entry = re.compile(r'\["([^"]+)"\]\s*=\s*\{(.*?)\},\s*(?:--[^\n]*)?\n', re.S)
    group = re.compile(r"\{([^{}]*)\}")
    quoted = re.compile(r'"([^"]*)"')
    html = re.compile(r"<[^>]+>")
    for m in entry.finditer(body):
        glyph, val = m.group(1), m.group(2)
        head = re.split(r"\b(?:hurr|hatt|luw|pal)\s*=", val)[0]
        # Fields 3, 4, 5 are the Hittite, Sumerian and Akkadian readings; 1 and 2 are
        # the Zeichenlexikon and Borger numbers and may themselves be braced lists.
        for g in group.findall(head)[-3:]:
            for r in quoted.findall(g):
                _add(table, normalise(html.sub("", r)), glyph, "wiktionary")


# Five lists are not five opinions. Enmerkar's own README says its sign list "is based
# on the Oracc Global Sign List", so it is a careful OGSL consumer rather than a witness
# beside OGSL; tfFromAtf's generated data descends from a Šašková sign list. Counting
# them as independent would inflate agreement, and would double-count outright if OSL
# were ever added here.
#
# Today each lineage happens to be represented once, so the vote is unaffected. The map
# exists so that the next list added is placed rather than simply appended.
LINEAGE = {
    "osl": "OGSL",                 # Oracc Global Sign List, CC0
    "potnia": "potnia",            # own Hittite compilation
    "nuolenna": "nuolenna",        # own compilation, Jauhiainen / Helsinki
    "wiktionary": "HZL",           # Rüster & Neu, Hethitisches Zeichenlexikon
    "enmerkar": "OGSL",            # an OGSL consumer, by its own README
    "tffromatf": "Šašková",        # via Nino-cunei's generated sign list
}


LOADERS = {
    "osl.asl": _osl,
    "potnia-hittite.yaml": _potnia,
    "nuolenna-signlist.tsv": _nuolenna,
    "tffromatf-mapping.tsv": _tffromatf,
    "enmerkar-signlist.csv": _enmerkar,
    "wiktionary-hittite-module.lua": _wiktionary,
}


_HZL_NUMS = re.compile(r"^\s*(\{[^{}]*\}|\d+)\s*,\s*(?:\{[^{}]*\}|\d+)")


def equivalents(path: Path) -> dict:
    """Codepoints that are the same sign, read from the shared Zeichenlexikon number.

    The Zeichenlexikon numbers signs, not codepoints, so two entries carrying one number
    are one sign written twice. This is stated by the source rather than inferred from
    shapes: 𒂉 and 𒆪 are both HZL 206 and both Borger 808, and the module splits them
    only by reading type -- the syllabic values under 𒆪, the logograms under 𒂉.

    Nine such classes exist in the Hittite list. It is a small number and a complete one
    only for signs the list happens to hold twice; a pair where it records just one of
    the two codepoints yields nothing here.
    """
    txt = path.read_text(encoding="utf8")
    body = txt[txt.index("export.sign_list = {"):]
    entry = re.compile(r'\["([^"]+)"\]\s*=\s*\{(.*?)\},\s*(?:--[^\n]*)?\n', re.S)
    by_number: dict = {}
    for m in entry.finditer(body):
        glyph, val = m.group(1), m.group(2)
        nums = _HZL_NUMS.match(val)
        if not nums:
            continue
        for n in re.findall(r"\d+", nums.group(1)):
            by_number.setdefault(n, set()).add(glyph)
    out: dict = {}
    for glyphs in by_number.values():
        if len(glyphs) < 2:
            continue
        for g in glyphs:
            out.setdefault(g, set()).update(glyphs)
    return out


def load(directory: Path) -> References:
    """Read whichever lists are present. A missing list is not an error -- their
    licences differ and a user may hold only some -- but the report says which ran."""
    table: dict = {}
    for name, loader in LOADERS.items():
        path = directory / name
        if path.is_file():
            loader(path, table)
    eq: dict = {}
    wiki = directory / "wiktionary-hittite-module.lua"
    if wiki.is_file():
        eq = equivalents(wiki)
    osl = directory / "osl.asl"
    if osl.is_file():
        for g, same in osl_equivalents(osl).items():
            eq.setdefault(g, set()).update(same)
    # A class is only closed once every member points at every other: OSL and the
    # Hittite module may each contribute part of one.
    for g in list(eq):
        for other in list(eq[g]):
            eq.setdefault(other, set()).update(eq[g])
    return References(table, eq)
