"""Source-construct census: count what the XML contains, independently of the converter.

The damage layer only became trustworthy once a gate counted markers in the source and
demanded the graph match.  Everything else in Contract B still lacked that, which is how
the build could report "all invariants hold" while shipping 15,434 fewer `line` nodes
than the source it was built from.

This counts structural elements in the *repaired* stream -- the same bytes the converter
reads -- so a deficit means the graph lost something, not that the gate read a different
file.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import lxml.etree as LE

from . import repair

# source element -> the node type it must become
ELEMENT_TO_TYPE = {
    "lb": "line",
    "clb": "colon",
    "note": "note",
}


# A top-level <w> becomes a `word` when it has readable signs and a `layout` when it does
# not, so the two together are what the source's words must account for.  15 still become
# neither: a nested <w> is skipped as "covered by the enclosing word's bytes", and when
# that enclosing word yields no slots its children are lost with it.  Pinned rather than
# ignored, so the number cannot grow unnoticed.
#
# It was 310 until `<w></w>` -- which tokenises to nothing and so produced neither node --
# started getting a layout node like any other contentless word.
KNOWN_WORD_DEFICIT = 15


def count_document(data: bytes) -> Counter | None:
    """Count structural elements under <text>.  None when the document does not convert."""
    try:
        root = LE.fromstring(data)
    except Exception:
        return None
    text = root.find(".//{*}text")
    if text is None:
        return None
    c = Counter()
    # Only top-level <w>: a nested one is deliberately covered by its parent's bytes.
    c["word"] = sum(
        1 for w in text.findall(".//{*}w")
        if not any(a.tag == "w" for a in w.iterancestors())
    )
    for tag, ntype in ELEMENT_TO_TYPE.items():
        # `{*}` matches the no-namespace case too, so this must not be doubled up with a
        # bare `.//tag` search -- doing that counted every element twice.
        c[ntype] = len(text.findall(f".//{{*}}{tag}"))
    return c


def count_corpus(files, patches, encrypted: str, rel_of) -> tuple[Counter, int]:
    """Total structural elements over every document that converts."""
    total = Counter()
    docs = 0
    for f in files:
        r = rel_of(f)
        if r == encrypted:
            continue
        data = f.read_bytes()
        entry = patches.get(r)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError:
                continue
        c = count_document(data)
        if c is None:
            continue
        docs += 1
        total.update(c)
    return total, docs


def graph_counts(tf_dir: Path) -> Counter:
    """Node counts straight from otype.tf -- no TF load, so the gate costs seconds."""
    from . import compact

    c = Counter()
    _, body = compact._split(tf_dir / "otype.tf")
    for nodes, value in compact._parse(body):
        c[value] += len(nodes)
    return c
