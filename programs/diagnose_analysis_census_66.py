#!/usr/bin/env python
"""Diagnose analysis-node census drift between immutable TF releases.

Temporary release-debugging aid for #57/#58.  It compares the already-certified 0.4.0
artifact with a freshly materialized 0.5.0 tree and reports the exact source document and
word source spans whose analysis cardinality changed.  It never mutates either artifact.
"""
from __future__ import annotations

import sys
from pathlib import Path

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]


def _load(version: str):
    locations = [
        str(ROOT / "tf" / version),
        str(ROOT / "tf-provenance" / version),
    ]
    tf = Fabric(locations=locations, silent="deep")
    api = tf.load(
        "otype oslots src_file src_span trans nanalyses analyses index lemma gloss morph",
        silent="deep",
    )
    if api is False or api is None:
        raise SystemExit(f"could not load TF {version}")
    return api


def _document_counts(api):
    F, L = api.F, api.L
    out = {}
    for doc in F.otype.s("document"):
        rel = F.src_file.v(doc)
        if not rel:
            raise SystemExit(f"document {doc} has no src_file")
        if rel in out:
            raise SystemExit(f"duplicate src_file document identity: {rel}")
        out[rel] = (len(L.d(doc, otype="word")), len(L.d(doc, otype="analysis")), doc)
    return out


def _word_rows(api, doc):
    F, L, E = api.F, api.L, api.E
    rows = {}
    for word in L.d(doc, otype="word"):
        span = F.src_span.v(word)
        if not span:
            # Word provenance is a release invariant, but keep the diagnostic useful if
            # the broken record itself violates it.
            span = f"node:{word}"
        analyses = tuple(E.analyses.f(word))
        rows[span] = {
            "word": word,
            "trans": F.trans.v(word),
            "declared": F.nanalyses.v(word),
            "analyses": tuple(
                (
                    F.index.v(a),
                    F.lemma.v(a),
                    F.gloss.v(a),
                    F.morph.v(a),
                    a,
                )
                for a in analyses
            ),
        }
    return rows


def main() -> int:
    old = _load("0.4.0")
    new = _load("0.5.0")
    old_docs = _document_counts(old)
    new_docs = _document_counts(new)

    all_rels = sorted(set(old_docs) | set(new_docs))
    changed = []
    for rel in all_rels:
        before = old_docs.get(rel)
        after = new_docs.get(rel)
        before_counts = None if before is None else before[:2]
        after_counts = None if after is None else after[:2]
        if before_counts != after_counts:
            changed.append((rel, before, after))

    print(f"documents 0.4.0={len(old_docs):,} 0.5.0={len(new_docs):,}")
    print(f"documents with word/analysis-count drift: {len(changed)}")
    for rel, before, after in changed:
        print(f"\n{rel}")
        print(f"  0.4.0: {None if before is None else before[:2]}  (words, analyses)")
        print(f"  0.5.0: {None if after is None else after[:2]}  (words, analyses)")
        if before is None or after is None:
            continue
        old_words = _word_rows(old, before[2])
        new_words = _word_rows(new, after[2])
        for span in sorted(set(old_words) | set(new_words)):
            a = old_words.get(span)
            b = new_words.get(span)
            comparable_a = None if a is None else (a["trans"], a["declared"], a["analyses"])
            comparable_b = None if b is None else (b["trans"], b["declared"], b["analyses"])
            if comparable_a != comparable_b:
                print(f"  word {span}")
                print(f"    0.4.0: {a}")
                print(f"    0.5.0: {b}")

    if not changed:
        print("No per-document analysis drift found; investigate unlinked analysis nodes.")
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
