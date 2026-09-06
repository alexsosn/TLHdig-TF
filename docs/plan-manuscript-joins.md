# Plan: source-faithful manuscript join graph

Issue: #18

Research: `docs/research-manuscript-joins.md`

No production converter change starts before this plan. The implementation must preserve the ordered source apparatus, provide fragment-to-fragment query edges, and retain unresolved/ambiguous source statements without guessing.

## 1. Compatibility and release boundary

This changes graph semantics and therefore requires a **new immutable TF artifact version**. Do not rewrite `tf/0.2.0` or any artifact already published. The issue branch has demonstrated the release-version RED and allocated `TF_VERSION = 0.3.0`; historical `0.1.0` and `0.2.0` artifacts remain immutable.

The old document features `directjoin` / `indirectjoin` are not reliable relations: empty XML operators collapse to empty/separator-only strings. In the new artifact they are removed rather than preserved as misleading compatibility data. Migration documentation points consumers to the new join graph.

Before final review, sync non-conflicting current `main` work, rerun the full release gate, and verify that no previous immutable TF directory changed. PR #11 is explicitly out of scope for this loop.

## 2. Pure source parser first

`tlhdig/manuscripts.py` converts one `AO:Manuscripts` mixed-content element into typed records without calling Text-Fabric.

Core records:

```python
ManuscriptEntry(
    order: int,
    kind: str,          # txtpubl | invnr | plain
    label: str,         # normalized visible source label
    siglum: str,        # normalized lookup key when recoverable, else ""
    siglum_raw: str,    # source spelling used for recovery
    siglum_source: str, # attr | element-text | tail | plain-text | none/conflict
)

JoinStatement(
    order: int,
    kind: str,          # direct | indirect | direct-multi | uncertain | malformed | unknown
    encoding: str,      # xml | textual
    raw: str,           # DirectJoin / InDirectJoin / + / (+) / ...
    left: int | None,   # block-local entry order, not siglum
    right: int | None,
    resolved: bool,
)
```

The parser is deterministic and operates on the same repaired/strict XML tree the converter uses. It must **not** use lxml recovery as a production repair mechanism.

### Entry grammar

Recognize every observed apparatus-entry family:

- `AO:TxtPubl`;
- rare `AO:TextPubl` as the publication-entry class;
- `AO:InvNr`;
- plain mixed-text entries proven by source order and marker grammar.

A single entry element may itself contain an ordered chain, e.g. `KBo 3.45 {€1} + UBT 34 {€2}`. Canonical whitespace-delimited operators inside `TxtPubl`/`TextPubl`/`InvNr` split the element into multiple entry **occurrences of the same element kind**, while preserving operator tokens between them. Leading/trailing operators remain in the surrounding block token stream so adjacency can resolve against neighboring source entries; they are not assigned invented internal endpoints.

Normalize source sigla only enough to match measured line-reference grammar while preserving raw spelling. Supported measured families include:

- euro-number tokens with optional internal whitespace (`€ 2` → `€2`);
- letter-number tokens (`A1`…`B3` are attested and line-used);
- bare numeric tokens where source and line references use them.

Recover siglum evidence from `@nr`, trailing braced tokens in entry text, entry tails, and plain-text entries. If sources disagree, do not choose silently: clear the resolved key, mark the conflict, and preserve all raw/normalized candidates. A label is never an identity substitute for a missing siglum.

### Join grammar

Recognize:

- `AO:DirectJoin` between adjacent entries → `kind=direct`, `encoding=xml`;
- `AO:InDirectJoin` → `kind=indirect`, `encoding=xml`;
- canonical textual `+` between entries → `kind=direct`, `encoding=textual`;
- canonical textual `(+)` → `kind=indirect`, `encoding=textual`.

Textual operators are recognized in block text/tails **and inside entry element text** using one ordered token grammar. TLHdig's own online rendering is the semantic evidence for `+` / `(+)`.

Do not promote these to a confident binary edge without separate evidence:

- `++` (`direct-multi` source state);
- `+?`, `(+) ?`, or other uncertainty forms;
- target-less status suffixes;
- malformed/incomplete punctuation;
- a token separated from the next entry by an unmodelled/corrupt child.

They remain source statements with `resolved=False` or a non-confident kind and raw evidence intact.

### Mixed serialization

A block may switch among textual and XML operators. Treat the ordered token stream as one apparatus; do not classify the whole block as one encoding.

If two source statements occupy the same occurrence boundary:

- same semantic kind: keep both statement records; the derived convenience edge may still be one edge;
- conflicting kinds: suppress a confident derived edge for that occurrence pair and preserve both statements.

## 3. Represent every apparatus entry as a fragment node

Keep node type `fragment`, but create one node for **every parsed manuscript entry occurrence** in every repaired/strict manuscript block, including `InvNr`, entries without sigla, and entries carrying no line.

Node features:

| feature | meaning |
|---|---|
| `manuscript_block` | 1-based `Manuscripts` block ordinal in `body/div1` document order |
| `fragment_order` | 1-based entry order inside that block |
| `fragment_kind` | `txtpubl` / `invnr` / `plain` |
| `fragment_label` | visible source label, whitespace-normalized |
| `frag` | normalized source siglum when unambiguous |
| `frag_raw` | raw source spelling of the selected siglum evidence |
| `siglum_raw_candidates` | all raw candidates when source evidence conflicts |
| `siglum_source` | `attr` / `element-text` / `tail` / `plain-text` / `conflict` |
| `siglum_ambiguous` | 1 when the same normalized siglum names >1 entry in this block |
| `txtpubl` | publication label for publication entries |
| `invnr` | inventory label for inventory entries |

Primary identity is `(document occurrence, manuscript_block, fragment_order)`, realized by the TF node itself. Never key the primary collection by siglum or label.

### Fragment slots and witness scope

Witness resolution is block-scoped and stateful:

- enumerate every `Manuscripts` block under `body/div1` in document order;
- each line records the **most recent preceding block ordinal** as its active manuscript apparatus;
- a later block never retroactively applies to earlier lines;
- a trailing block after the final line is ledgered but owns no lines;
- do not union sigla from multiple blocks and do not fall back to an older block when the active block lacks a match.

Within a line's active block:

- a unique normalized siglum maps to one fragment and gets `witness_resolution=unique`;
- duplicate normalized sigla map to all block-local candidates with `witness_resolution=ambiguous`;
- composite line sigla continue to split via `lineref` (`A1+2` → `A1`, `A2`; `€1+2` → `€1`, `€2`);
- no candidate means no witness edge, not a guessed cross-block link.

Use cited line extents as fragment slots when a block-local witness resolves. Otherwise anchor the fragment to the document's first slot; this anchor is implementation connectivity, not textual extent.

The line feature `manuscript_block` records the active block ordinal when one precedes the line, making witness scope independently queryable and testable.

## 4. Preserve every source join statement as an overlay node

Add node type `joinstmt` for exact statement accounting.

Features:

| feature | meaning |
|---|---|
| `manuscript_block` | 1-based source block ordinal |
| `join_kind` | `direct` / `indirect` / `direct-multi` / `uncertain` / `malformed` / `unknown` |
| `join_encoding` | `xml` / `textual` |
| `join_raw` | literal source operator/marker |
| `join_order` | block-local statement order |
| `join_resolved` | 1 only when both endpoint occurrences are known and semantic kind is confident |
| `join_reason` | optional diagnostic reason for an unresolved statement |

Edges:

- `joinLeft`: `joinstmt -> fragment` when the left block-local endpoint is known;
- `joinRight`: `joinstmt -> fragment` when the right endpoint is known;
- `joinDocument`: `joinstmt -> document` for source provenance.

Source statement identity is `(src_file, manuscript_block, join_order)`. Every source occurrence is one ledger node; **never deduplicate across blocks or serializations**.

Anchor a statement to its left endpoint slot when available, otherwise to the document anchor/first slot. `oslots` is an anchor, not relation extent.

## 5. Derived fragment-to-fragment edge

Add valued edge feature:

```text
joined: fragment -> fragment = direct | indirect
```

Orientation is source order (`left -> right`), not a physical directional claim.

Emit `joined` only when:

- both block-local entry occurrence endpoints are resolved;
- the statement is confidently `direct` or `indirect`; and
- all confident statements for that exact occurrence pair **inside that block** agree on the same kind.

Do not synthesize reverse edges and do not compute transitive closure. `joinstmt` is authoritative; `joined` is convenience only.

## 6. Source conservation ledger

Add deterministic production gate `programs/check_manuscript_joins.py` against the same repaired/strict source scope and generated graph.

It must derive its expected counts from the revised parser, not freeze the obsolete pre-expansion value `2,361`. The earlier embedded-chain census already proved 1,232 additional canonical markers, so any gate built around `2,361` is invalid.

Key every source and graph record by release-scoped source identity plus block-local order:

```text
entry      = (src_file, manuscript_block, fragment_order)
statement  = (src_file, manuscript_block, join_order)
```

Enforce:

- every repaired/strict `Manuscripts` block under converted `body/div1` is enumerated;
- every parser entry occurrence has exactly one matching fragment node;
- every parser statement occurrence has exactly one matching `joinstmt`;
- kind, encoding, raw marker, resolution state, block/order and endpoint identities match;
- every `joinstmt` has exactly one `joinDocument` edge to the document with matching `src_file`;
- confident resolved statements have exactly one left and right endpoint;
- unresolved statements remain ledgered and do not emit `joined`;
- every `joined` edge has agreeing same-kind source support for that block-local occurrence pair;
- no reverse or transitive convenience edge exists without its own source statement;
- every line witness target belongs to that line's active source block and normalized siglum;
- duplicate/conflicting sigla cannot overwrite occurrences;
- AOHeader edit-history `join`/`merge` events are absent from this ledger.

Write `reports/manuscript-joins.md` with source→graph totals and anomaly diagnostics. No baseline inflation: parser/conservation disagreement fails.

## 7. Revised RED sequence

The original parser/graph REDs remain required and are already demonstrated. Before the second production integration, add new failing fixtures for the newly measured grammar/scope:

### Parser RED additions

22. `<TxtPubl>A {€1} + B {€2}</TxtPubl>` becomes two `txtpubl` occurrences + one direct statement.
23. embedded mixed direct/indirect chain preserves each marker and local order.
24. `<InvNr>Bo 1 + Bo 2</InvNr>` becomes two inventory occurrences + one direct statement.
25. `A1` / `A2` braced sigla are recovered and `A1+2` can resolve through `lineref`.
26. `{€ 2}` normalizes to `€2` while raw spelling is preserved.
27. leading/trailing embedded operators remain token-stream statements and are not assigned invented endpoints.

### Graph/integration RED additions

28. sibling `body/div1/Manuscripts` before `<text>` emits fragments/statements and owns following line witnesses.
29. two blocks before the first line are both ledgered, but the line resolves only against the later active block.
30. a mid-stream block switch changes witness scope only for later lines.
31. every fragment/joinstmt carries the correct `manuscript_block`; local orders restart at 1 per block.
32. `A1`, `A2`, and composite `A1+2` produce block-local witness edges.
33. spaced euro siglum produces normalized witness lookup while preserving raw fragment provenance.
34. embedded element chains emit their source statement ledger and derived edge without collapsing separate source occurrences.

RED must be demonstrated in hosted CI before revising production conversion for multi-block scope.

## 8. Revised implementation sequence

1. expand `tlhdig/manuscripts.py` to the measured siglum and element-internal token grammar until parser RED additions are GREEN;
2. pre-scan `body/div1` in source order, assigning every `Manuscripts` a 1-based block ordinal and each `lb` the active most-recent preceding block;
3. carry active block ordinal into line state / line feature;
4. emit every block independently through `manuscript_graph`, passing only the lines scoped to that block for witness extent/resolution;
5. keep `fragment_order` / `join_order` block-local and add `manuscript_block` metadata;
6. preserve all source statements; emit block-local `joined` under confidence rules;
7. add exact repaired-source-to-graph conservation checker/report;
8. remove exploratory research workflows/scripts once measurements are frozen and the production checker supersedes them;
9. add the new checker to release certification and bump release policy because the required gate set changes;
10. build/certify immutable `tf/0.3.0` + `tf-provenance/0.3.0`, regenerate census/docs, and verify old artifacts unchanged.

## 9. Full test gate

A candidate PR is not ready for review until:

- all unit tests pass;
- repaired/strict manuscript source conservation passes with exact block/entry/statement accounting;
- block-scoped line witness resolution passes, including the real mid-stream switch pattern;
- corpus identity and repair manifest pass;
- sign round-trip, morphology, structure and Contract A pass;
- marker/tag/provenance/alignment/app/census gates pass;
- full release certification passes for `0.3.0` under the bumped release policy;
- `tf/0.1.0`, `tf/0.2.0` and matching provenance modules are byte-for-byte untouched.

## 10. Independent adversarial review

A logically independent reviewer must try to falsify at least these claims:

- `+` / `(+)` semantics were evidence-based and uncertainty punctuation was not upgraded;
- element-internal chains do not swallow or duplicate markers, including leading/trailing cases;
- sibling, repeated, and mid-stream manuscript blocks are all ledgered in source order;
- line witnesses never leak across the active-block boundary;
- `A*`, `B*`, numeric and spaced-euro sigla normalize only as measured and retain raw provenance;
- `InvNr`, rare `TextPubl`, and plain-text entries survive;
- duplicate sigla cannot overwrite fragment nodes or misdirect joins;
- source order is not documented as semantic direction;
- no implicit symmetry/transitivity is added;
- every source statement is represented exactly once in the authoritative `joinstmt` ledger;
- every convenience `joined` edge has block-local supporting evidence and conflicts suppress it;
- unresolved statements remain queryable with raw provenance;
- AOHeader edit-history joins were not accidentally folded into witness joins;
- fragment anchor slots are not misdocumented as textual extent;
- old `directjoin`/`indirectjoin` migration is documented;
- `0.3.0` is a new immutable artifact and prior releases are unchanged;
- the full release certifier includes and passes the new manuscript-join gate.

Any blocking finding returns to implementation → tests → fresh independent review before merge.

## 11. Plan revision status

The first parser/graph implementation proved the base occurrence-ledger design but failed the later production-scope conservation research because it selected one manuscript block and recognized only the earlier grammar. Sections 2–10 above are the **superseding implementation plan** for the remainder of issue #18. No further production change proceeds until the added REDs in Section 7 are observed failing against the current branch.
