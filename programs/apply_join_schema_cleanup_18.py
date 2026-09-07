#!/usr/bin/env python
"""One-shot assertion-heavy cleanup after the issue #18 full-suite migration RED."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one exact match, found {count}")
    path.write_text(text.replace(old, new), encoding="utf8")


def main() -> None:
    test = ROOT / "programs/tests/test_convert.py"
    replace_once(
        test,
        '''def test_fragments_from_the_manuscript_block(tmp_path):
    api = _build_doc(tmp_path, DOC_B, "frag")
    frags = api.F.otype.s("fragment")
    sigla = {api.F.frag.v(f) for f in frags}
    assert sigla == {"€1", "€2"}
    pub = {api.F.txtpubl.v(f) for f in frags}
    assert pub == {"KBo 1.1", "KBo 1.2"}
''',
        '''def test_fragments_from_the_manuscript_block(tmp_path):
    api = _build_doc(tmp_path, DOC_B, "frag")
    frags = api.F.otype.s("fragment")
    # Every source apparatus entry is an occurrence node. The unsigled InvNr is not
    # discarded merely because line-witness lookup cannot address it.
    assert len(frags) == 3
    rows = {
        (api.F.fragment_kind.v(f), api.F.fragment_label.v(f), api.F.frag.v(f))
        for f in frags
    }
    assert rows == {
        ("txtpubl", "KBo 1.1", "€1"),
        ("txtpubl", "KBo 1.2", "€2"),
        ("invnr", "Bo 1234", None),
    }
''',
    )
    replace_once(
        test,
        '''def test_joins_are_recorded(tmp_path):
    api = _build_doc(tmp_path, DOC_B, "join")
    d = api.F.otype.s("document")[0]
    assert "KBo 1.3" in (api.F.directjoin.v(d) or "")
''',
        '''def test_joins_are_recorded_as_authoritative_statements(tmp_path):
    api = _build_doc(tmp_path, DOC_B, "join")
    statements = api.F.otype.s("joinstmt")
    assert len(statements) == 1
    statement = statements[0]
    assert api.F.join_kind.v(statement) == "direct"
    assert api.F.join_encoding.v(statement) == "xml"
    # This XML operator follows the last entry and therefore has no right endpoint.
    # The old flattened document string invented a relation target from element text;
    # the source-faithful ledger keeps the unresolved statement instead.
    assert api.F.join_resolved.v(statement) == 0
    assert api.E.joinDocument.f(statement) == api.F.otype.s("document")
    assert api.E.joinLeft.f(statement)
    assert not getattr(api.E, "joined", None) or not api.E.joined.f(api.E.joinLeft.f(statement)[0])
    assert not hasattr(api.F, "directjoin")
    assert not hasattr(api.F, "indirectjoin")
''',
    )
    replace_once(
        test,
        '''    covered = {F.frag.v(f): set(L.d(f, otype="sign")) for f in F.otype.s("fragment")}
    assert set(covered) == {"\\u20ac1", "\\u20ac2"}
    a, b = covered["\\u20ac1"], covered["\\u20ac2"]
''',
        '''    covered = {
        F.frag.v(f): set(L.d(f, otype="sign"))
        for f in F.otype.s("fragment")
        if F.frag.v(f)
    }
    assert set(covered) == {"\\u20ac1", "\\u20ac2"}
    a, b = covered["\\u20ac1"], covered["\\u20ac2"]
''',
    )

    readme = ROOT / "README.md"
    replace_once(
        readme,
        '''Additional structures such as `paragraph` and `colon` coexist with analytical and
relational overlays including `analysis`, `lex`, `cluster`, `fragment`, `note`, `edit` and
`docgroup`.
''',
        '''Additional structures such as `paragraph` and `colon` coexist with analytical and
relational overlays including `analysis`, `lex`, `cluster`, `fragment`, `joinstmt`, `note`,
`edit` and `docgroup`.

Manuscript apparatus is occurrence-based. Each source entry is a `fragment`; every source
join statement is retained as a `joinstmt`, including duplicates and unresolved or
uncertain statements. `joinLeft` / `joinRight` recover endpoints when the source provides
them, while valued `joined=direct|indirect` is only a convenience projection for confident
binary statements. Its orientation is **source apparatus order, not semantic direction**:
no reverse or transitive join is inferred. Lines point to block-scoped fragment occurrences
with `witness`; `witness_resolution=unique|ambiguous` makes duplicate-siglum resolution
explicit.

**0.3.0 migration:** the old document string features `directjoin` and `indirectjoin` are
removed. Queries that need source fidelity should use `joinstmt`; queries that only need
confident adjacent relationships may use the valued `joined` edge.
''',
    )
    replace_once(
        readme,
        '''- [`reports/contract_a_graph.md`](reports/contract_a_graph.md) — graph-to-source span
  verification;
''',
        '''- [`reports/contract_a_graph.md`](reports/contract_a_graph.md) — graph-to-source span
  verification;
- [`reports/manuscript-joins.md`](reports/manuscript-joins.md) — independent repaired-source
  to shipped-graph conservation for fragment occurrences, join statements, witnesses and
  the non-inferred `joined` projection;
''',
    )

    known = ROOT / "KNOWN-ISSUES.md"
    replace_once(
        known,
        '''The remaining declared model gaps include:

- manuscript `joins` edges: direct/indirect join information is still flattened rather
  than represented as fragment-to-fragment graph edges;
- `sign.lang`: language exists at document/line/colon level, not on every sign;
''',
        '''The remaining declared model gaps include:

- `sign.lang`: language exists at document/line/colon level, not on every sign;
''',
    )
    replace_once(
        known,
        '''- `note`, `fragment`, `docgroup`, `lex`, `witness`, `edition`, `noteref` and `lexeme`
  layers now exist in the shipped graph;
''',
        '''- `note`, `fragment`, `joinstmt`, `docgroup`, `lex`, `witness`, `edition`, `noteref`
  and `lexeme` layers now exist in the shipped graph; manuscript joins preserve source
  statement multiplicity and unresolved evidence, with a separately checked non-inferred
  `joined` convenience projection;
''',
    )

    print("join schema migration tests/docs patched")


if __name__ == "__main__":
    main()
