"""Repair of syntactically corrupt source files (plan §7.2).

211 of 23,937 files do not parse.  They are not random corruption: they fall into a
small number of mechanical classes, catalogued in research §9.1.

Repairs are **declarative**.  A detector proposes exact `old` -> `new` byte
replacements; the manifest records them alongside the file's SHA-256; application
asserts that the hash still matches and that each `old` occurs exactly once.  A regex
that "matches exactly once" is not a sufficient guard on its own -- a wrong pattern can
match once and still corrupt the wrong bytes -- so the hash pins the input and the
manifest makes every change reviewable.

Scope is deliberately narrow: **syntactic corruption only**.  Old Assyrian's
`fixes.yaml` mixes parser repairs with philological normalisation (leading-zero
removal); this converter must not become an uncredited critical edition.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from xml.parsers import expat


class PatchError(RuntimeError):
    pass


@dataclass(slots=True)
class Patch:
    old: bytes
    new: bytes
    reason: str


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parses(data: bytes) -> bool:
    try:
        expat.ParserCreate().Parse(data, True)
        return True
    except expat.ExpatError:
        return False


# --------------------------------------------------------------------- detectors
#
# Each detector returns a list of Patch.  They look for the corruption itself, not for
# wherever expat happened to stop -- the parser usually halts well after the damage.

# A find-replace accident: '<gap c="Text bricht ab"/>' became '<kap c-"Te%t pricḫt ap"'.
# The substitution damaged g->k, x->%, b->p and ch->ḫ inside the tag name, the '=' and
# the caption alike, so the caption is rebuilt rather than salvaged character by
# character.
_CORRUPT_TAG = re.compile(rb'<(kap|clp)\s+(c|it)-"([^"]*)"')

# The accident mapped x->%, h->ḫ, b->p and g->k.  Reversing 'ḫ' to the digraph 'ch'
# would yield "briccht": the 'c' of "bricht" was never damaged.
_UNDAMAGE = [
    (b"%", b"x"),
    (b"\xe1\xb8\xab", b"h"),   # ḫ -> h
    (b"p", b"b"),
    (b"k", b"g"),
]


def _restore_caption(raw: bytes) -> bytes:
    """Best-effort reversal of the character damage in a corrupted caption."""
    s = raw
    for bad, good in _UNDAMAGE:
        s = s.replace(bad, good)
    return s


def detect_corrupt_gap(data: bytes) -> list[Patch]:
    out = []
    for m in _CORRUPT_TAG.finditer(data):
        caption = _restore_caption(m.group(3))
        out.append(
            Patch(
                old=m.group(0),
                new=b'<gap c="' + caption + b'"/>',
                reason="corrupted find-replace of a <gap> tag",
            )
        )
    return out


_ODF_LINEBREAK = re.compile(rb"<text:line-break(?!\s*/?>)")


def detect_unclosed_odf(data: bytes) -> list[Patch]:
    out = [
        Patch(old=m.group(0), new=b"<text:line-break/>", reason="unclosed ODF line-break")
        for m in _ODF_LINEBREAK.finditer(data)
    ]
    # the matching stray close tag, if present
    if out and b"</text:line-break>" in data:
        out.append(
            Patch(old=b"</text:line-break>", new=b"", reason="stray ODF line-break close")
        )
    return out


_PARSER_ERROR = re.compile(rb"<parser_error>(.*?)</parser_error>", re.S)


def detect_parser_error_element(data: bytes) -> list[Patch]:
    return [
        Patch(
            old=m.group(0),
            new=m.group(1),
            reason="<parser_error> wrapper inside an attribute value; reading kept",
        )
        for m in _PARSER_ERROR.finditer(data)
    ]


# An attribute value that closes and then continues: lnr=" ... 4"/1′" or trans="x"'
# An attribute value that closes and then continues:  lnr=" ... 4"/1′"  or  trans="x"y"
# The continuation may start with '/', so that character is allowed -- but not the
# sequence '/>', which would be the element closing normally.
_STRAY_QUOTE = re.compile(rb'(\s[-\w:.]+=")([^"]*)"(?!>)(/(?!>)|[^\s/>=])([^">]*)"')


def detect_unescaped_quote(data: bytes) -> list[Patch]:
    out = []
    for m in _STRAY_QUOTE.finditer(data):
        merged = m.group(2) + b"&quot;" + m.group(3) + m.group(4)
        out.append(
            Patch(
                old=m.group(0),
                new=m.group(1) + merged + b'"',
                reason="unescaped quote inside an attribute value",
            )
        )
    return out


_TRAILING_QUOTE = re.compile(rb'(="[^"]*")(\')(\s)')


def detect_trailing_quote(data: bytes) -> list[Patch]:
    return [
        Patch(old=m.group(0), new=m.group(1) + m.group(3), reason="stray quote after attribute")
        for m in _TRAILING_QUOTE.finditer(data)
    ]


_TAG = re.compile(rb"<([A-Za-z_][-\w.:]*)((?:[^<>\"']|\"[^\"]*\"|'[^']*')*)>")
_ATTR = re.compile(rb'([-\w.:]+)\s*=\s*"([^"]*)"')


def detect_duplicate_attribute(data: bytes) -> list[Patch]:
    out = []
    for m in _TAG.finditer(data):
        seen: dict[bytes, bytes] = {}
        dup = False
        for a in _ATTR.finditer(m.group(2)):
            k, v = a.group(1), a.group(2)
            if k in seen:
                dup = True
                if seen[k] != v:
                    dup = False   # differing values: not safe to drop, leave it
                    break
            seen[k] = v
        if not dup:
            continue
        rebuilt = b"<" + m.group(1)
        for k, v in seen.items():
            rebuilt += b" " + k + b'="' + v + b'"'
        rebuilt += b"/>" if m.group(2).rstrip().endswith(b"/") else b">"
        out.append(Patch(old=m.group(0), new=rebuilt, reason="duplicate identical attribute"))
    return out


# Order matters: the more specific detector runs first so that its proposal wins the
# overlap check below.  A stray trailing quote and an unescaped inner quote both match
# `trans="x"' `, but only the trailing-quote reading is correct -- the other would
# swallow the following attribute.
# A start tag that is never terminated, immediately followed by another tag:
#   <w <w trans="na~" ...>        a duplicated <w
#   <w \n<lb lnr="4"/>            a stray <w before an unrelated element
# 81 of the 149 otherwise-undiagnosed files carry one.  The leading fragment holds no
# attributes and no content, so it is dropped rather than terminated -- terminating it
# would invent an empty <w> element that is not in the source.
_STRAY_OPEN = re.compile(rb"<w([ \t\r\n]+)(?=<)")


def detect_stray_unterminated_tag(data: bytes) -> list[Patch]:
    """Drop an unterminated `<w` fragment.

    `<w ` occurs thousands of times per file, so the patch carries following context
    until it identifies exactly one site; `apply` refuses an ambiguous target.
    """
    out = []
    for m in _STRAY_OPEN.finditer(data):
        start = m.start()
        for extra in (40, 80, 160, 320, 640):
            old = data[start : m.end() + extra]
            if data.count(old) == 1:
                out.append(
                    Patch(
                        old=old,
                        new=old[m.end() - start :],
                        reason="stray unterminated <w fragment",
                    )
                )
                break
    return out


# A bare '<' inside an attribute value: trans="pan- <parse"
_LT_IN_ATTR = re.compile(rb'(\s[-\w:.]+=")([^"<]*)<([^"<]*)(")')


def detect_lt_in_attribute(data: bytes) -> list[Patch]:
    return [
        Patch(
            old=m.group(0),
            new=m.group(1) + m.group(2) + b"&lt;" + m.group(3) + m.group(4),
            reason="unescaped '<' inside an attribute value",
        )
        for m in _LT_IN_ATTR.finditer(data)
    ]


_ANY_TAG = re.compile(rb"<(/?)([A-Za-z_][-\w.:]*)((?:[^<>\"']|\"[^\"]*\"|'[^']*')*?)(/?)>")

# Elements whose content model is empty; they never appear on the open stack.
_VOID = frozenset(
    b"lb clb parsep parsep_dbl tabsep gap space del_in del_fin laes_in laes_fin "
    b"ras_in ras_fin ras_X add_in add_fin corr note subscr materlect surpl wsep "
    b"creation-date AOxml-creation annot".split()
)


def _unique_patch(data: bytes, start: int, end: int, new_mid: bytes, reason: str) -> Patch:
    """Build a patch whose `old` identifies exactly one site.

    A bare `</w>` or `</AO:K>` occurs many times per file, and repairing one crossing
    can create a second copy of the very tag we then need to remove.  So the target is
    widened with following context until it is unique; `apply` still refuses anything
    ambiguous.
    """
    for extra in (0, 40, 80, 160, 320, 640, 1280):
        old = data[start : end + extra]
        if data.count(old) == 1:
            return Patch(old=old, new=new_mid + data[end : end + extra], reason=reason)
    return Patch(old=data[start:end], new=new_mid, reason=reason)


def detect_crossing_tags(data: bytes) -> list[Patch]:
    """Repair improperly nested elements.

    Two shapes dominate the structurally-broken files:

    * crossing -- `<w><AO:K>...</w>...</AO:K>`, where an element opened inside <w> is
      closed outside it.  The inner element is closed before the outer one.
    * a stray close whose element is not open at all, which is dropped.

    Only the first fault in a file is repaired per round; `propose_iteratively` runs
    the detectors again on the result, so layered damage still converges.
    """
    stack: list[bytes] = []
    for m in _ANY_TAG.finditer(data):
        closing, name, selfc = m.group(1), m.group(2), m.group(4)
        if selfc or name in _VOID:
            continue
        if not closing:
            stack.append(name)
            continue
        if stack and stack[-1] == name:
            stack.pop()
            continue
        if name in stack:
            # crossing: close everything opened after `name`, innermost first
            inner = []
            while stack and stack[-1] != name:
                inner.append(stack.pop())
            fix = b"".join(b"</" + t + b">" for t in inner)
            return [
                _unique_patch(
                    data,
                    m.start(),
                    m.end(),
                    fix + m.group(0),
                    "crossing tags: inner element closed before its parent",
                )
            ]
        # a close with nothing matching open
        return [
            _unique_patch(
                data, m.start(), m.end(), b"", "stray close tag, nothing open"
            )
        ]
    return []


DETECTORS = (
    detect_stray_unterminated_tag,
    detect_lt_in_attribute,
    detect_corrupt_gap,
    detect_unclosed_odf,
    detect_parser_error_element,
    detect_duplicate_attribute,
    detect_trailing_quote,
    detect_unescaped_quote,
)

# Run only when no lexical detector fired.  Its tag scan is confused by lexical damage
# -- an unbalanced quote hides a start tag, making a valid close look stray -- so it
# must see bytes the other detectors have already cleaned.  `propose_iteratively`
# gives it that chance on a later round.
LAST_RESORT = (detect_crossing_tags,)


def propose(data: bytes) -> list[Patch]:
    """Every patch the detectors suggest, de-duplicated and non-overlapping.

    Two detectors may legitimately fire on the same bytes.  Applying both would leave
    the second looking for a target the first already rewrote, so overlapping
    proposals are dropped in detector order rather than allowed to collide at apply
    time.
    """
    out: list[Patch] = []
    seen: set[bytes] = set()
    claimed: list[tuple[int, int]] = []
    for det in DETECTORS:
        for p in det(data):
            if p.old in seen:
                continue
            start = data.find(p.old)
            if start < 0:
                continue
            end = start + len(p.old)
            if any(start < c_end and c_start < end for c_start, c_end in claimed):
                continue
            claimed.append((start, end))
            seen.add(p.old)
            out.append(p)
    if not out:
        for det in LAST_RESORT:
            out.extend(det(data))
    return out


# ----------------------------------------------------------------- application

def propose_iteratively(data: bytes, max_rounds: int = 8) -> list[Patch]:
    """Propose patches until the file parses or nothing new is found.

    Damaged files usually carry several independent corruptions, and fixing one can
    reveal the next -- a stray `<w` fragment hides the mismatched tag behind it.  Each
    round re-runs the detectors against the partially repaired bytes, so the returned
    list is ordered and must be applied in sequence.
    """
    out: list[Patch] = []
    cur = data
    for _ in range(max_rounds):
        if parses(cur):
            break
        found = propose(cur)
        if not found:
            break
        progressed = False
        for p in found:
            if cur.count(p.old) != 1:
                continue
            cur = cur.replace(p.old, p.new, 1)
            out.append(p)
            progressed = True
        if not progressed:
            break
    return out


def apply(data: bytes, patches: list[Patch], expect_sha: str | None = None) -> bytes:
    if expect_sha is not None and sha256(data) != expect_sha:
        raise PatchError(f"sha256 mismatch: refusing to patch")
    out = data
    for p in patches:
        n = out.count(p.old)
        if n == 0:
            raise PatchError(f"patch target not found: {p.old[:60]!r}")
        if n > 1:
            raise PatchError(f"patch target ambiguous, occurs {n} times: {p.old[:60]!r}")
        out = out.replace(p.old, p.new, 1)
    return out


# ------------------------------------------------ original <-> repaired coordinates


class OffsetMap:
    """Translate a byte offset in the repaired stream back to the original file.

    Repairs are applied in memory, but `document.src_file` names the file on disk, so
    a span recorded against the repaired stream would slice the wrong bytes from it.
    166 of the 173 repaired files change length, so this is not a corner case.

    The map records, for each patch, where it landed in each stream and how the length
    changed; translation is then a lookup of the cumulative delta up to that point.
    """

    __slots__ = ("_edits",)

    def __init__(self, data: bytes, patches: list[Patch]):
        # (repaired_start, repaired_end, original_start, original_end)
        self._edits: list[tuple[int, int, int, int]] = []
        cur = data
        shift = 0                       # repaired offset - original offset, so far
        for p in patches:
            i = cur.find(p.old)
            if i < 0:
                continue
            self._edits.append(
                (i, i + len(p.new), i - shift, i - shift + len(p.old))
            )
            cur = cur[:i] + p.new + cur[i + len(p.old) :]
            shift += len(p.new) - len(p.old)
        self._edits.sort()

    def to_original(self, offset: int) -> int:
        """Map a repaired-stream offset to the nearest original-stream offset.

        Offsets inside a patched region collapse to the start of that region in the
        original -- the bytes there do not correspond one to one by construction.
        """
        delta = 0
        for r_start, r_end, o_start, o_end in self._edits:
            if offset < r_start:
                break
            if offset < r_end:
                return o_start
            delta += (r_end - r_start) - (o_end - o_start)
        return offset - delta

    def span_to_original(self, start: int, end: int) -> tuple[int, int]:
        a = self.to_original(start)
        b = self.to_original(end)
        return (a, b if b >= a else a)

    @property
    def changed(self) -> bool:
        return any(
            (r_end - r_start) != (o_end - o_start)
            for r_start, r_end, o_start, o_end in self._edits
        )


# -------------------------------------------------------------------- manifest

def write_manifest(path: Path, entries: dict[str, tuple[str, list[Patch]]]) -> None:
    import yaml

    doc = {
        rel: {
            "sha256": sha,
            "patches": [
                {
                    "old": p.old.decode("utf8", "surrogateescape"),
                    "new": p.new.decode("utf8", "surrogateescape"),
                    "reason": p.reason,
                }
                for p in patches
            ],
        }
        for rel, (sha, patches) in sorted(entries.items())
    }
    path.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=10_000),
        encoding="utf8",
    )


def read_manifest(path: Path) -> dict[str, tuple[str, list[Patch]]]:
    import yaml

    doc = yaml.safe_load(path.read_text(encoding="utf8")) or {}
    return {
        rel: (
            entry["sha256"],
            [
                Patch(
                    old=p["old"].encode("utf8", "surrogateescape"),
                    new=p["new"].encode("utf8", "surrogateescape"),
                    reason=p["reason"],
                )
                for p in entry.get("patches", [])
            ],
        )
        for rel, entry in doc.items()
    }
