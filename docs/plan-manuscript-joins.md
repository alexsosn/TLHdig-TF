# Plan: source-faithful manuscript join graph

Issue: #18

Research: `docs/research-manuscript-joins.md`

No production converter change starts before this plan. The implementation must preserve the ordered source apparatus, provide fragment-to-fragment query edges, and retain unresolved/ambiguous source statements without guessing.

## 1. Compatibility and release boundary

This changes graph semantics and therefore requires a **new immutable TF artifact version**. Do not rewrite `tf/0.2.0` or any artifact already published by #10/PR #11. Before production integration, rebase on the then-current `main` and allocate the next TF version from that state.

The current document features `directjoin` / `indirectjoin` are not reliable relations: empty XML operators collapse to empty/separator-only strings. In the new artifact they are removed rather than preserved as misleading compatibility data. Migration documentation points consumers to the new join graph.

Research/parser work may proceed in parallel with #10 because it is isolated. The production conversion/version commit must rebase after any merged PR that changes `TF_VERSION` or the same `_manuscripts` / document code.

## 2. Pure source parser first

Add a small pure module, `tlhdig/manuscripts.py`, that converts one `AO:Manuscripts` mixed-content element into typed records without calling Text-Fabric.

Suggested immutable records:

```python
ManuscriptEntry(
    order: int,
    kind: str,          # txtpubl | invnr | plain
    label: str,         # normalized visible source label
    siglum: str,        # normalized €n when recoverable, else ""
    siglum_raw: str,    # exact @nr / {€n} spelling used for recovery
    siglum_source: str, # attr | element-text | tail | plain-text | none
)

JoinStatement(
    order: int,
    kind: str,          # direct | indirect | direct-multi | uncertain | unknown
    encoding: str,      # xml | textual
    raw: str,           # DirectJoin / InDirectJoin / + / (+) / ...
    left: int | None,   # entry order, not siglum
    right: int | None,
    resolved: bool,
    reason: str,
)
```

The parser must be deterministic and operate on the same repaired/strict XML tree the converter uses. It must **not** use lxml recovery as a production repair mechanism.

### Entry grammar

Recognize every observed apparatus-entry family:

- `AO:TxtPubl`;
- rare `AO:TextPubl` as the same publication-entry class, while retaining the raw kind if useful for provenance;
- `AO:InvNr`;
- the two observed plain mixed-text `label {€n}` entries.

Normalize the source siglum to `€n` for lookup while preserving its original spelling. Recover it from, in precedence order only when unambiguous:

1. `@nr`;
2. a trailing `{€n}` / equivalent siglum token carried in the entry's own text;
3. the entry tail before a textual join marker;
4. the plain-text entry itself.

If two sources disagree, do not choose silently: mark the entry's siglum unresolved/conflicting and preserve both raw forms in the parser diagnostic. A source label must not be used as an identity substitute for a missing siglum.

### Join grammar

Recognize:

- `AO:DirectJoin` between adjacent entries → `kind=direct`, `encoding=xml`;
- `AO:InDirectJoin` → `kind=indirect`, `encoding=xml`;
- canonical textual `+` between entries → `kind=direct`, `encoding=textual`;
- canonical textual `(+)` → `kind=indirect`, `encoding=textual`.

TLHdig's own online rendering is the semantic evidence for the punctuation mapping; this is not inferred from glyph shape alone.

Do **not** promote these to a confident binary edge without separate evidence:

- `++` (`direct-multi` source state);
- `+?`, `(+) ?`, or other uncertainty forms;
- target-less `+` / `(+)` status suffixes;
- malformed/incomplete punctuation;
- text separated from the next entry by an unmodelled/corrupt child.

They become `JoinStatement` records with `resolved=False` or a non-confident kind and their raw context intact.

### Mixed serialization

A block may switch from textual to XML operators. Treat the ordered token stream as one apparatus; do not classify the whole block as one encoding.

If two source statements ever occupy the same entry boundary:

- same semantic kind: keep **both statement records**; the derived convenience edge may still be one edge;
- conflicting kinds: do not emit a confident derived edge for that pair; preserve both statements and flag the conflict.

Research currently found mixed blocks using the two families on different successive boundaries, but this rule prevents a future source update from collapsing duplicate/conflicting evidence.

## 3. Represent every apparatus entry as a fragment node

Keep node type `fragment`, but stop making its existence depend on a line reference. Create one fragment node for **every parsed manuscript entry occurrence**, including `InvNr`, entries without sigla, and entries that carry no text line.

Node features:

| feature | meaning |
|---|---|
| `fragment_order` | source order inside `AO:Manuscripts`, 1-based |
| `fragment_kind` | `txtpubl` / `invnr` / `plain` |
| `fragment_label` | visible source label, normalized only for whitespace |
| `frag` | normalized `€n` siglum when source provides one |
| `frag_raw` | raw source spelling of the siglum when it differs/is useful |
| `siglum_source` | `attr` / `element-text` / `tail` / `plain-text` |
| `siglum_ambiguous` | 1 when the same normalized siglum names >1 entry in this block |
| `txtpubl` | publication label for publication entries (compatibility/query convenience) |
| `invnr` | inventory number for inventory entries |

Do not use a dictionary keyed by siglum or label as the primary collection; it currently overwrites duplicates. Primary identity is the **entry occurrence node**.

### Fragment slots

- If a uniquely resolved siglum is cited by lines, use the union of those line extents as the fragment node's slots, preserving the useful current containment behavior.
- An entry with no cited line remains anchored to the document's first slot, because TF 13.1.0 deletes/crashes on unlinked edge-bearing nodes. Document this as an anchor, not a claimed textual extent.
- If a line siglum maps to multiple fragment entries, do not choose one. Give all candidates the relevant line extent and mark the ambiguity. Emit `witness` edges to all candidates only with an accompanying valued `witness_resolution=ambiguous`; unique resolutions carry `witness_resolution=unique`. This avoids the current silent dictionary overwrite while keeping the existing `witness` edge usable.

Composite line sigla such as `€1+2` continue to split into their component sigla before resolution.

## 4. Preserve every source join statement as an overlay node

Add node type `joinstmt` for exact statement accounting. This is deliberately small (~a few thousand nodes) and solves three problems that a single valued edge cannot: unresolved targets, multiple source statements on one pair, and relation-specific provenance.

Features:

| feature | meaning |
|---|---|
| `join_kind` | `direct` / `indirect` / `direct-multi` / `uncertain` / `unknown` |
| `join_encoding` | `xml` / `textual` |
| `join_raw` | literal operator/marker |
| `join_order` | statement order in the manuscript block |
| `join_resolved` | 1 only when both endpoint occurrences are known and semantic kind is confident |
| `join_reason` | diagnostic reason for an unresolved statement |

Edges:

- `joinLeft`: `joinstmt -> fragment` when the left endpoint is known;
- `joinRight`: `joinstmt -> fragment` when the right endpoint is known;
- `joinDocument`: `joinstmt -> document` for provenance and unresolved target-less statements.

Anchor the node to a left endpoint slot when available, otherwise the document anchor/first slot. Its `oslots` is an implementation anchor, not relation extent.

This node layer is the authoritative source-statement ledger.

## 5. Derived fragment-to-fragment edge

Add valued edge feature:

```text
joined: fragment -> fragment = direct | indirect
```

Orientation is **source order** (`left -> right`), not a claim that a physical join is directional. Document this explicitly in feature metadata.

Emit `joined` only when:

- both entry occurrence endpoints are resolved; and
- the statement is confidently `direct` or `indirect`; and
- all confident statements for that exact occurrence pair agree on the same kind.

Do not synthesize the reverse edge and do not compute transitive closure.

`joinstmt` nodes preserve multiplicity/provenance; `joined` is the ergonomic query edge. If two same-kind source statements support one pair, one `joined` edge is correct while both `joinstmt` nodes remain countable.

## 6. Source conservation ledger

Add a deterministic corpus gate, e.g. `programs/check_manuscript_joins.py`, that works against the same repaired source inputs and generated graph.

It must report and enforce:

```text
source statements
  = resolved joinstmt nodes
  + unresolved joinstmt nodes
```

separately by:

- semantic/source state;
- XML vs textual encoding;
- endpoint kind pair;
- repaired vs unrepaired source file if useful for diagnostics.

Also assert:

- every confident resolved `joinstmt` has exactly one left and one right fragment endpoint;
- every `joined` edge is supported by >=1 resolved statement of the same kind;
- no conflicting statement pair produces a confident `joined` edge;
- no fragment entry occurrence is overwritten because another entry reused its siglum;
- source-order values are unique within each manuscript block;
- AOHeader edit-history `join` / `merge` events are absent from this ledger.

No baseline inflation: new unresolved statements discovered by a parser regression fail the gate unless the source itself changed and the change is researched.

## 7. RED sequence

Before production implementation, add failing tests for the pure parser and graph contract.

### Parser RED

1. XML `TxtPubl <DirectJoin/> TxtPubl` → two entries + one direct statement.
2. XML indirect join.
3. `InvNr` on either/both endpoints.
4. plain mixed-text `label {€1} <DirectJoin/> ...` entry.
5. legacy tail `{€1} +` / `{€2} (+)` syntax with sigla recovered from tails.
6. siglum embedded in entry text rather than `@nr`.
7. multiple joins in one chain preserve source order.
8. mixed textual then XML operators in one block.
9. `++`, `+?`, `(+) ?`, malformed punctuation, and target-less suffix remain unresolved/non-confident.
10. intervening unknown child prevents guessed textual adjacency.
11. duplicate siglum creates two distinct entries rather than overwrite.
12. conflicting siglum sources are explicit diagnostics, not precedence guesses.
13. same boundary duplicated with same kind preserves two statement records.
14. same boundary conflicting direct/indirect suppresses confident derived relation.

### Graph RED

15. every apparatus entry produces a fragment node, even without line coverage.
16. unique line siglum resolves one `witness` edge with `witness_resolution=unique`.
17. duplicate line siglum keeps both fragment nodes and marks ambiguous witness resolution.
18. confident direct/indirect statement emits `joinstmt` endpoint edges plus `joined`.
19. unresolved target-less statement emits `joinstmt` + document edge but no `joined`.
20. source orientation is preserved without reverse/transitive edges.
21. two same-kind statements on one pair produce two `joinstmt` nodes but one `joined` edge.

RED must be demonstrated in CI before converter production code is added.

## 8. Implementation sequence

1. add `tlhdig/manuscripts.py` pure parser until parser RED is GREEN;
2. replace `_manuscripts` string collection with parsed entry/statement records in `_State`;
3. refactor fragment emission to occurrence-based nodes and multimap siglum resolution;
4. emit `joinstmt` nodes and provenance edges;
5. emit derived `joined` edges under the confidence rules;
6. remove misleading document `directjoin` / `indirectjoin` emission and update feature metadata;
7. add corpus conservation gate/report;
8. allocate/build the next immutable TF version after rebasing current `main`;
9. run all existing release gates plus the new join conservation gate;
10. regenerate census/tag/feature documentation and migration notes.

## 9. Full test gate

A candidate PR is not ready for review until:

- all unit tests pass;
- corpus identity and repair manifest pass;
- sign round-trip, morphology, structure and Contract A pass;
- marker/tag/provenance/alignment/app/census gates pass;
- manuscript join source-conservation gate passes with exact statement accounting;
- existing line/witness counts are explained before/after, especially the two duplicate-siglum blocks;
- full release certification passes for the new artifact under the then-current release policy;
- no previous immutable TF version is modified.

## 10. Independent adversarial review

A logically independent reviewer must try to falsify at least these claims:

- `+` / `(+)` semantics were not guessed and uncertainty punctuation was not upgraded;
- mixed serialization does not duplicate or omit boundaries;
- `InvNr`, rare `TextPubl`, and plain-text entries survive;
- duplicate sigla cannot overwrite fragment nodes or misdirect joins;
- source order is not documented as semantic direction;
- no implicit symmetry/transitivity is added;
- every source statement is represented exactly once in the authoritative `joinstmt` ledger;
- every convenience `joined` edge has supporting source evidence and conflicting evidence suppresses it;
- unresolved statements remain queryable with raw provenance;
- AOHeader edit-history joins were not accidentally folded into witness joins;
- fragment anchor slots are not misdocumented as textual extent;
- old `directjoin`/`indirectjoin` migration is documented;
- the PR uses a new immutable TF artifact and passes the full release certifier.

Any blocking finding returns to implementation → tests → fresh review before merge.
