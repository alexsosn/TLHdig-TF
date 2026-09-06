# Research: manuscript join relationships

Issue: #18

This document freezes the research gate before any production graph changes. The question is not merely how to turn `AO:DirectJoin` and `AO:InDirectJoin` into edges; TLHdig 0.3 contains multiple serialization families for the same manuscript apparatus, plus malformed/recovered cases that must remain auditable.

## Scope and method

The initial research used three independent recovery-oriented corpus passes over all 23,937 source XML files:

- `programs/research_joins.py` inventories explicit `AO:DirectJoin` / `AO:InDirectJoin` elements and the current flattened TF representation;
- `programs/research_joins_mixed.py` reconstructs mixed-content manuscript entries that precede an XML join operator as plain text rather than a child element;
- `programs/research_joins_textual.py` measures older textual `+`, `(+)`, `++`, and uncertainty notation in `AO:Manuscripts` tails and block text.

The corpus has 224 strict XML parse failures before repository repairs. Recovery yields a tree for 223; one source is unrecoverable/encrypted. Those recovery counts remain useful for discovering grammar, but **production conservation is defined on the repaired/strict tree used by the converter**, not on lxml recovery.

A second research round therefore measured that exact production scope with `research_manuscript_reachability.py`, `research_manuscript_block_scope.py`, `research_manuscript_sigla.py`, `research_manuscript_embedded_chains.py`, and `research_manuscript_after_line.py`. Section 11 is authoritative where its results supersede the earlier recovery-oriented counts below.

## 1. `AO:Manuscripts` is an ordered mixed-content grammar

The recovery census sees 24,402 `Manuscripts` blocks. The normal entry elements are:

- `AO:TxtPubl` — 24,060 occurrences in the recovery census;
- `AO:InvNr` — 2,871;
- rare `AO:TextPubl` — 16.

Two blocks begin with a manuscript entry encoded directly as mixed text, e.g. `KBo 10.47c {€1}`, followed by an explicit join element. Once these two entries are recognized, all 1,242 explicit XML join operators in the recovery census occur between two manuscript entries; there are no true leading/trailing XML-operator anomalies there.

This invalidates the original simplifying assumption that a join element itself contains a target identifier. The elements are empty binary separators in an ordered entry sequence.

## 2. Explicit XML join family

Recovery-oriented corpus counts:

| operator | count |
|---|---:|
| `AO:DirectJoin` | 1,067 |
| `AO:InDirectJoin` | 175 |
| **total** | **1,242** |

Every operator is empty and has no attributes. Immediate endpoint kinds after mixed-content correction include:

| pair | count |
|---|---:|
| direct `TxtPubl -> TxtPubl` | 956 |
| indirect `TxtPubl -> TxtPubl` | 154 |
| direct `TxtPubl -> InvNr` | 45 |
| direct `InvNr -> InvNr` | 35 |
| direct `InvNr -> TxtPubl` | 19 |
| indirect `TxtPubl -> InvNr` | 7 |
| direct `TextPubl -> TextPubl` | 7 |
| indirect `TextPubl -> TextPubl` | 6 |
| indirect `InvNr -> InvNr` | 4 |
| direct `TextPubl -> InvNr` | 3 |
| indirect `InvNr -> TxtPubl` | 2 |
| direct `PlainText -> TxtPubl` | 1 |
| indirect `PlainText -> TxtPubl` | 1 |
| indirect `InvNr -> TextPubl` | 1 |
| direct `TxtPubl -> TextPubl` | 1 |

The source therefore joins **apparatus entries**, not documents as wholes and not only publication-labelled fragments.

No exact self-relation was found in the simple identity census. No oriented pair had an explicit reverse statement elsewhere, and no unordered pair appeared once as direct and once as indirect in the XML-operator family. These negative observations are sanity checks; they are **not** evidence that the philological relation is directed or asymmetric.

## 3. Older textual join family

Mixed-content tails and block text also encode joins without `DirectJoin` / `InDirectJoin` elements. A typical source shape is:

```xml
<AO:Manuscripts>
  <AO:InvNr>1198/u</AO:InvNr>{€1} +
  <AO:InvNr>1436/u</AO:InvNr>{€2} +
  <AO:TxtPubl>KUB 8.82</AO:TxtPubl>{€3} +
  <AO:InvNr>Bo 69/821</AO:InvNr>{€4}
</AO:Manuscripts>
```

The initial textual census found:

- 1,138 textual markers in total in block text/tails;
- 1,115 safely extractable binary relations;
- 30 unresolved textual statements/contexts retained separately;
- 549 blocks with at least one extracted textual relation;
- 583 blocks using explicit XML operators only;
- 562 blocks using textual notation only;
- 15 blocks mixing both serialization families;
- 687 fragment sigla stored only in tail text rather than `@nr`;
- 1,903 sigla stored in `@nr` in that pass.

Literal marker counts in that pass:

| research class | count |
|---|---:|
| direct `+` | 854 |
| indirect `(+)` | 282 |
| direct-multi `++` | 2 |

These counts **exclude join syntax embedded inside the text of a `TxtPubl`, `TextPubl`, or `InvNr` element**. Section 11 measures that large additional family.

Uncertainty-shaped markers such as `+?` / `(+) ?`, malformed punctuation, target-less status suffixes, comments, and ambiguous adjacency are not promoted to confident binary relations by the parser.

### Semantic cross-check

The punctuation mapping is supported by TLHdig's own online rendering rather than inferred from typography alone:

- TLHdig renders `IBoT 4.41+` as `IBoT 4.41 {Frg. 2} (+) KUB 8.23 {Frg. 1}`: https://www.hethport.uni-wuerzburg.de/TLHdig/tlh_xtx.php?d=IBoT+4.41
- TLHdig renders a direct composite such as `IBoT 4.229+` with plain `+`: https://www.hethport.uni-wuerzburg.de/TLHdig/tlh_xtx.php?d=IBoT+4.229
- TLHdig's rendered note for `KBo 57.113` explicitly calls an uncertain `(+)` relationship an “indirect join”: https://www.hethport.uni-wuerzburg.de/TLHdig/tlh_xtx.php?d=KBo+57.113&o=CTH+526

Therefore production may normalize canonical `+` as `direct` and canonical `(+)` as `indirect`. `++`, `+?`, `(+) ?`, incomplete punctuation, and target-less status remain distinct source states unless separate evidence justifies a stronger interpretation.

## 4. Fragment sigla are not uniformly stored

The first child-only census found 1,903 entry `@nr` values, of which 1,680 occur in line references and 223 do not. That is incomplete as a corpus model because additional sigla are encoded in tails, entry text, and non-`€n` forms.

Two manuscript blocks also contain duplicate `@nr` assignments (`TxtPubl+TxtPubl` in one block, `InvNr+TxtPubl` in another). A converter must not use a bare siglum as a globally or even blindly block-unique identity without detecting these cases.

Consequences:

1. every apparatus entry needs its own stable internal node identity independent of whether it has a line siglum;
2. source siglum is a feature/lookup key, not the node identity;
3. duplicate or conflicting sigla must remain explicit and must not overwrite an earlier node;
4. line-to-fragment resolution must be tested separately from join-edge construction.

## 5. Current TF model loses the relation

The old converter appended the text content of `DirectJoin` and `InDirectJoin` elements to document-level arrays. Because the operators are empty, the resulting document features are mostly empty strings or separator-only values such as `" | "`.

The old `fragment`/`witness` model was also line-driven and dictionary-keyed by siglum. That cannot represent every apparatus occurrence and can overwrite duplicate sigla. The first #18 implementation fixed occurrence identity for one selected apparatus block, but the second research round showed that **single-block selection is itself lossy**; details are in Section 11.

## 6. AOHeader edit-history joins are a different source layer

The source also contains AOHeader/meta events such as:

- `join`: 309
- `merge`: 73
- `merged`: 75
- plus `aufheb`, `aufloes`, `mDocID`, and related edit-history records.

These are change-history statements, not the ordered manuscript apparatus. They must **not** be merged into the manuscript join graph under this ticket without separate evidence and design.

## 7. Direction, symmetry, and transitivity

The source serialization gives a left/right order because it is an ordered manuscript list. Research does **not** establish that the philological join relation itself is directed.

Production therefore distinguishes:

- **source orientation**: left entry followed by a separator followed by right entry; mechanically recoverable and useful for exact provenance/conservation;
- **semantic relation**: `direct`, `indirect`, or unresolved/other source state; no inverse edge or transitive closure is inferred automatically.

A stored `left -> right` convenience edge is acceptable only when documentation explicitly says the orientation preserves source order and does not assert a directional physical relation.

## 8. Required conservation contract

The implementation must account for every safely recognized manuscript join statement by one of:

1. a graph relation between two explicit apparatus-entry nodes; or
2. an unresolved source statement with its raw marker/context and reason it could not be resolved.

The authoritative ledger is **source-occurrence preserving**. If two encodings or repeated blocks state the same-looking relation twice, both source statement occurrences remain two `joinstmt` nodes. A derived convenience edge may collapse duplicate same-kind evidence only for the **same endpoint occurrence pair inside the same apparatus block**. There is no cross-block deduplication.

Uncertainty and malformed notation may not be converted into a confident `direct` or `indirect` edge solely to improve resolution counts.

## 9. Design constraints established by the first research round

The plan may rely on these constraints:

- joins belong to manuscript/apparatus entries, not document strings;
- `TxtPubl`, `TextPubl`, `InvNr`, and plain mixed-text entries occur;
- source sigla can be encoded in multiple places;
- all entries, including those not referenced by lines, need representation if they participate in a relation;
- `+` and `(+)` can be normalized to direct/indirect with TLHdig online evidence;
- uncertainty/multi/status punctuation is preserved separately;
- source order is not semantic direction;
- no symmetry or transitivity is inferred;
- AOHeader edit-history join/merge events are out of scope;
- source-statement conservation is mandatory and exposes unresolved cases rather than hiding them.

## 10. Research artifacts

The research branch keeps the scripts that generated the measurements while the issue is active. The final implementation should replace the overlapping exploratory scanners with focused parser/unit tests plus a deterministic repaired-source-to-graph conservation gate; exploratory workflow machinery is not part of the production deliverable.

## 11. Production-scope follow-up — authoritative for implementation

This section supersedes any earlier assumption that one `text/Manuscripts` block, `€n` alone, or block text/tails alone describe the production grammar.

### 11.1 Repaired/strict block reachability

The converter's actual repaired/strict scope contains:

| metric | count |
|---|---:|
| source files | 23,937 |
| encrypted exclusion | 1 |
| strict unparseable exclusions after repairs | 52 |
| patch failures | 0 |
| repaired/strict `Manuscripts` blocks | **24,294** |
| documents containing at least one block | **23,877** |
| documents containing multiple blocks | **412** |

The first #18 emitter selected only `text_el.find(AO:Manuscripts)`. That reaches 23,541 blocks and misses **753** repaired/strict blocks in 748 files. The missed locations are:

- 417 additional `body/div1/text/Manuscripts` blocks;
- 336 `body/div1/Manuscripts` sibling blocks immediately outside `<text>`.

Under the parser grammar that existed at the time of this measurement, the repaired/strict tree contained 2,361 recognized statements; **89 of those were already outside the single selected block** (57 in `div1/Manuscripts`, 32 in additional `text/Manuscripts`). Thus the single-block implementation fails conservation even before the grammar expansion below.

All 24,294 repaired/strict blocks belong to the production source ledger. Recovery-only blocks in the 52 excluded malformed files remain research evidence but cannot be attached to a converted document node under this ticket.

### 11.2 Block order determines witness scope

Across the repaired/strict tree:

- 24,292 of 24,294 blocks occur before the first line in their document;
- exactly 2 occur after at least one line;
- among 1,698 documents with line fragment references, whenever the then-current parser could identify a best matching block, the **last block before the line region was also the last best matching block**: 1,630 cases, with zero contradictory cases.

The two post-line cases were inspected individually:

1. `CTH 585_XML_HDivT/KBo 52.108+.xml` has a third `Manuscripts` block after `rev. III 9′`, before a later line `1′`; the block introduces `KUB 56.11 {€3}`. It is a real mid-stream apparatus/witness switch.
2. `CTH 820_XML_TLH/KBo 64.205.xml` has a trailing block after the final line, parsed as inventory-like `Rs. 2`; no later line exists, so it must be ledgered but owns no witness lines.

Therefore line witness resolution is **stateful in source order**: a line resolves against the most recent preceding `Manuscripts` block under `body/div1`. A later block does not retroactively change earlier lines, and multiple blocks are never unioned for witness lookup.

### 11.3 Siglum grammar is broader than `€n`

The repaired/strict source census found braced siglum-like tokens in these families:

| family | source occurrences |
|---|---:|
| `€n` | 3,246 |
| letter+number (`A1`, `B2`, …) | 82 |
| other | 5 |

Line references contain 127,450 `€n` occurrences, 2,623 letter+number occurrences, 130 numeric occurrences, and 442 other fragment-token occurrences. Source tokens that are demonstrably used by line references include `A1`…`A6`, `B1`…`B3`, bare `1`/`2`, and a spaced euro form such as `{€ 2}` whose line reference is normalized to `{€2}`.

The parser must therefore preserve the raw spelling and normalize only the measured lookup distinctions needed by line references, including internal whitespace in euro-number sigla. Hard-coding braces to `€\d+` loses real witnesses.

### 11.4 Entire join chains occur inside one entry element

A major source form was absent from all earlier statement totals. **664** `TxtPubl`/`TextPubl`/`InvNr` elements contain canonical whitespace-delimited `+` / `(+)` operators inside the element's own text. They contain **1,232 marker occurrences**:

| marker | count |
|---|---:|
| direct `+` | **994** |
| indirect `(+)` | **238** |
| total | **1,232** |

Of those, 1,146 markers have non-empty text segments on both sides within the same element. Sixty elements contain at least one empty segment, so leading/trailing/continuation cases must remain token-stream evidence rather than being forced into an internal binary pair. The embedded elements contain 1,755 braced tokens; **1,360 source siglum occurrences in these chains are used on lines**.

Concrete examples include:

```xml
<AO:TxtPubl>KBo 3.45 {€1} + UBT 34 {€2}</AO:TxtPubl>
<AO:InvNr>Bo 3074 + Bo 8530</AO:InvNr>
```

and mixed direct/indirect chains such as:

```xml
<AO:TxtPubl>KBo 3.53 {€1} + KBo 19.90 {€2} (+) KBo 3.54 {€3}</AO:TxtPubl>
```

The 2,361 repaired/strict statement count from the pre-expansion parser is therefore **only a lower bound**. The 1,232 embedded canonical markers alone raise the known source-marker floor to 3,593 before accounting for any element-internal status/malformed forms that the revised parser will conservatively preserve. The release baseline must be generated **after** the revised parser is GREEN; the old 2,361 value must never be frozen as a production conservation expectation.

### 11.5 Revised implementation boundary

The production model must consequently satisfy all of the following:

- parse every repaired/strict `Manuscripts` block under `body/div1`, in document order;
- tokenize canonical join syntax both between child elements and inside entry element text;
- let leading/trailing element-internal markers participate in the same ordered token stream rather than inventing endpoints;
- preserve every source statement occurrence separately, including repeated serializations in separate blocks;
- give every fragment and statement a 1-based `manuscript_block` ordinal, with entry/statement order local to that block;
- resolve each line only against the most recent preceding block;
- preserve raw siglum spelling while normalizing measured lookup forms (`€ 2` → `€2`, plus observed letter/number identifiers);
- never infer reverse edges, transitive closure, or semantic direction from source order;
- replace exploratory counts with an exact repaired-source-to-graph gate after the parser/model expansion.
