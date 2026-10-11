"""Source-construct census: count what the XML contains, independently of the converter.

The damage layer only became trustworthy once a gate counted markers in the source and
demanded the graph match. Everything else in Contract B still lacked that, which is how
the build could report "all invariants hold" while shipping 15,434 fewer `line` nodes
than the source it was built from.

Normally this counts structural elements in the historically repaired source
stream. For the four explicitly recovered source-event pilots, that repaired
word nesting is not original lexical reality: count their source-authenticated
literal word and line opening events instead, without altering the census of
any other source or dropping clb/note counts.
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
# not, so the two together must account for every source top-level word. Issue #52
# identified the remaining allowance of 15 as the readable pre-line words dropped by the
# old `self.line is None` early return. Once those words are represented, no known
# top-level word deficit remains; nested <w> elements are deliberately outside this census.
KNOWN_WORD_DEFICIT = 0


def count_document(data: bytes) -> Counter | None:
    """Count structural elements under <text>. None when the document does not convert."""
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


def count_corpus(
    files, patches, encrypted: str, rel_of, *,
    terminal_recovery_paths=(),
) -> tuple[Counter, int]:
    """Count all converted sources, honoring four explicitly reviewed source events.

    The normal corpus uses existing repaired-XML ancestry. Opted-in pilots use
    immutable original opening events for word/line identity: a historically
    patched tree can nest an independent source word under its predecessor.
    Note/colon counts still come from the fully repaired parse and are never
    ignored. An absent pilot, drifted source, or changed patch sequence fails.
    """
    selected = frozenset(terminal_recovery_paths)
    seen = set()
    if selected:
        from . import convert, prepared_source, recovery
        from .paths import CORPUS, PATCHES

        unknown = selected - convert.VERIFIED_RECOVERY_PILOTS
        if unknown:
            raise ValueError(f"unreviewed source-event pilot: {sorted(unknown)}")
        canonical_patches = repair.read_manifest(PATCHES)

    total = Counter()
    docs = 0
    for f in files:
        r = rel_of(f)
        if r == encrypted:
            continue
        is_recovered = r in selected
        if is_recovered:
            if r in seen:
                raise ValueError(f"duplicate source-event pilot file: {r}")
            seen.add(r)
            if r not in patches or patches[r] != canonical_patches.get(r):
                raise ValueError(f"source-event pilot manifest drift: {r}")
            # prepare() checks the original SHA-256, the complete ordered
            # manifest fingerprint and the reviewed mechanical/recovery
            # partition. All lexical opening offsets come from original
            # bytes, not the historically repaired parent/child tree.
            reviewed = prepared_source.prepare(r, corpus=CORPUS, manifest=PATCHES)
            recovery.reviewed_word_payload(reviewed)
            original_words, original_lines = recovery.original_opening_sequences(reviewed)
            witnesses = recovery.lexical_word_witnesses(reviewed)
            if tuple(w.opening_offset for w in witnesses) != original_words:
                raise ValueError(f"source-event pilot lexical opening drift: {r}")

        data = f.read_bytes()
        entry = patches.get(r)
        if entry:
            try:
                data = repair.apply(data, entry[1], expect_sha=entry[0])
            except repair.PatchError:
                if is_recovered:
                    raise ValueError(f"source-event pilot repair failed: {r}")
                continue
        c = count_document(data)
        if c is None:
            if is_recovered:
                raise ValueError(f"source-event pilot no longer parses: {r}")
            continue
        if is_recovered:
            if c["line"] != len(original_lines):
                raise ValueError(
                    f"source-event pilot line census disagrees with literal source: {r}"
                )
            c["word"] = len(original_words)
            c["line"] = len(original_lines)
        docs += 1
        total.update(c)

    missing = selected - seen
    if missing:
        raise ValueError(f"missing selected source-event pilot: {sorted(missing)}")
    return total, docs


def graph_counts(tf_dir: Path) -> Counter:
    """Node counts straight from otype.tf -- no TF load, so the gate costs seconds."""
    from . import compact

    c = Counter()
    _, body = compact._split(tf_dir / "otype.tf")
    for nodes, value in compact._parse(body):
        c[value] += len(nodes)
    return c
