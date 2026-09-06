# Research: manuscript join relationships

Issue: #18

This document freezes the research gate before any production graph changes. The question is not merely how to turn `AO:DirectJoin` and `AO:InDirectJoin` into edges; TLHdig 0.3 contains two serialization families for the same manuscript apparatus, plus malformed/recovered cases that must remain auditable.

## Scope and method

Three independent corpus passes were run over all 23,937 source XML files:

- `programs/research_joins.py` inventories explicit `AO:DirectJoin` / `AO:InDirectJoin` elements and the current flattened TF representation;
- `programs/research_joins_mixed.py` reconstructs the two mixed-content manuscript entries that precede an XML join operator as plain text rather than a child element;
- `programs/research_joins_textual.py` measures the older textual `+`, `(+)`, `++`, and uncertainty notation in `AO:Manuscripts` tails and text.

The corpus has 224 strict XML parse failures. Recovery yields a tree for 223; one source is unrecoverable/encrypted. Counts from recovered XML are research evidence only; production conversion still follows the repository's normal repair/exclusion contract.

## 1. `AO:Manuscripts` is an ordered mixed-content grammar

There are 24,402 `Manuscripts` blocks. The normal entry elements are:

- `AO:TxtPubl` — 24,060 occurrences in the recovery census;
- `AO:InvNr` — 2,871;
- rare `AO:TextPubl` — 16.

Two blocks begin with a manuscript entry encoded directly as mixed text, e.g. `KBo 10.47c {€1}`, followed by an explicit join element. Both plain-text entries are referenced by line sigla and both labels equal the document id. Once these two entries are recognized, **all 1,242 explicit XML join operators occur between two manuscript entries**; there are no true leading/trailing operator anomalies.

This invalidates the original simplifying assumption that a join element itself contains a target identifier. The elements are empty binary separators in an ordered entry sequence.

## 2. Explicit XML join family

Corpus-wide counts:

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

No exact self-relation was found in the simple identity census. No oriented pair had an explicit reverse statement elsewhere, and no unordered pair appeared once as direct and once as indirect in the XML-operator family. These negative observations are useful sanity checks; they are **not** evidence that the relation is directed or asymmetric.

## 3. Older textual join family

Mixed-content tails also encode joins without `DirectJoin` / `InDirectJoin` elements. A typical source shape is:

```xml
<AO:Manuscripts>
  <AO:InvNr>1198/u</AO:InvNr>{€1} +
  <AO:InvNr>1436/u</AO:InvNr>{€2} +
  <AO:TxtPubl>KUB 8.82</AO:TxtPubl>{€3} +
  <AO:InvNr>Bo 69/821</AO:InvNr>{€4}
</AO:Manuscripts>
```

The textual census found:

- 1,138 textual markers in total;
- 1,115 safely extractable binary relations;
- 30 unresolved textual statements/contexts retained separately;
- 549 blocks with at least one extracted textual relation;
- 583 blocks using explicit XML operators only;
- 562 blocks using textual notation only;
- 15 blocks mixing both serialization families;
- 687 fragment sigla stored only in tail text rather than `@nr`;
- 1,903 sigla stored in `@nr` only in this census.

Literal marker counts:

| research class | count |
|---|---:|
| direct `+` | 854 |
| indirect `(+)` | 282 |
| direct-multi `++` | 2 |

Uncertainty-shaped markers such as `+?` / `(+) ?`, malformed punctuation, target-less status suffixes, comments, and ambiguous adjacency are **not** promoted to binary relations by the research parser.

The extracted textual endpoints again include `TxtPubl`, `InvNr`, and plain-text labels; they are not reducible to a publication-only model.

### Semantic cross-check

The punctuation mapping is supported by TLHdig's own online rendering rather than inferred from typography alone:

- TLHdig renders `IBoT 4.41+` as `IBoT 4.41 {Frg. 2} (+) KUB 8.23 {Frg. 1}`: https://www.hethport.uni-wuerzburg.de/TLHdig/tlh_xtx.php?d=IBoT+4.41
- TLHdig renders a direct composite such as `IBoT 4.229+` with plain `+`: https://www.hethport.uni-wuerzburg.de/TLHdig/tlh_xtx.php?d=IBoT+4.229
- TLHdig's rendered note for `KBo 57.113` explicitly calls an uncertain `(+)` relationship an “indirect join”: https://www.hethport.uni-wuerzburg.de/TLHdig/tlh_xtx.php?d=KBo+57.113&o=CTH+526

Therefore production may normalize canonical `+` as `direct` and canonical `(+)` as `indirect`. `++`, `+?`, `(+) ?`, incomplete punctuation, and target-less status remain distinct source states unless separate evidence justifies a stronger interpretation.

## 4. Fragment sigla are not uniformly stored

The first child-only census found 1,903 entry `@nr` values, of which 1,680 occur in line references and 223 do not. That is incomplete as a corpus model because an additional **687 sigla are encoded in tail text** such as `{€1}` rather than the entry attribute.

Two manuscript blocks also contain duplicate `@nr` assignments (`TxtPubl+TxtPubl` in one block, `InvNr+TxtPubl` in another). A converter must not use a bare siglum as a globally or even blindly block-unique identity without detecting these cases.

Consequences:

1. every apparatus entry needs its own stable internal node identity independent of whether it has a line siglum;
2. source siglum is a feature/lookup key, not the node identity;
3. duplicate or conflicting sigla must remain explicit and must not overwrite an earlier node;
4. line-to-fragment resolution must be tested separately from join-edge construction.

## 5. Current TF model loses the relation

The converter currently appends the text content of `DirectJoin` and `InDirectJoin` elements to document-level arrays. Because the operators are empty, the resulting document features are mostly empty strings or separator-only values such as `" | "`.

The current `fragment`/`witness` model is also line-driven: it is sufficient for many line references but not for representing every apparatus entry, including entries with no line-bearing siglum. A join graph cannot be made source-complete by connecting only the fragment nodes that happen to exist today.

## 6. AOHeader edit-history joins are a different source layer

The source also contains AOHeader/meta events such as:

- `join`: 309
- `merge`: 73
- `merged`: 75
- plus `aufheb`, `aufloes`, `mDocID`, and related edit-history records.

These are change-history statements, not the ordered manuscript apparatus. They must **not** be merged into the manuscript join graph under this ticket without separate evidence and design.

## 7. Direction, symmetry, and transitivity

The source serialization gives a left/right order because it is an ordered manuscript list. Research does **not** establish that the philological join relation itself is directed.

Production therefore must distinguish:

- **source orientation**: left entry followed by a separator followed by right entry; this is mechanically recoverable and useful for exact provenance/conservation;
- **semantic relation**: `direct`, `indirect`, or unresolved/other source state; no inverse edge or transitive closure may be inferred automatically.

A single stored `left -> right` edge is acceptable only if documentation explicitly says the orientation preserves source order and does not assert a directional physical relation. Query helpers may treat it as undirected if appropriate, but the persisted graph should not manufacture symmetric duplicates unless Text-Fabric ergonomics require them and conservation still counts one source statement once.

## 8. Required conservation contract

The implementation must account for every safely recognized manuscript join statement by one of:

1. a graph relation between two explicit apparatus-entry nodes; or
2. an unresolved source statement with its raw marker/context and reason it could not be resolved.

The conservation ledger must cover **both** explicit XML operators and canonical textual notation. Mixed blocks must be checked for duplicate serialization of the same boundary before counting; the converter must not emit two semantic relations for one source statement merely because two encodings coexist.

Uncertainty and malformed notation may not be converted into a confident `direct` or `indirect` edge solely to improve resolution counts.

## 9. Design constraints established by research

The plan may now rely on these constraints:

- joins belong to manuscript/apparatus entries, not document strings;
- the parser must support `TxtPubl`, `TextPubl`, `InvNr`, and the two observed plain-text entries;
- sigla can come from `@nr` or textual tails;
- all entries, including those not referenced by lines, need representation if they participate in a relation;
- `+` and `(+)` can be normalized to direct/indirect with TLHdig online evidence;
- uncertainty/multi/status punctuation is preserved separately;
- source order is not semantic direction;
- no symmetry or transitivity is inferred;
- AOHeader edit-history join/merge events are out of scope;
- source-statement conservation is mandatory and must expose unresolved cases rather than hide them.

## 10. Research artifacts

The research branch keeps the scripts that generated the measurements. The bulky row-level JSON/TSV output remains a workflow artifact rather than a permanent hand-maintained corpus baseline. The final implementation should replace these exploratory scripts with focused parser/unit tests plus a deterministic corpus validation gate rather than ship several overlapping research scanners as production machinery.
