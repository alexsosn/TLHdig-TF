# Independent Code and Architecture Review — 2026-08-30

**Repository:** `alexsosn/TLHdig-TF`  
**Reviewed head:** `94c8626`  
**Scope:** converter architecture, tokenisation, morphology, repair layer, Text-Fabric graph construction, validation, CI/release workflow, generated `tf/0.1.0`, and conversion-design documents.

## Executive verdict

The repository has improved substantially since the earlier reviews, especially around damage-marker conservation. The low-level parsing machinery is now the strongest part of the project: `source.py`, `signs.py`, `morph.py`, the repair manifest, the ledger, and the independent marker-conservation gate all show careful adversarial testing.

The weakest part is the boundary between those components and the final Text-Fabric ontology. Several code paths preserve bytes while silently losing structured meaning, and several validation gates prove properties of intermediate representations without proving the corresponding property of the shipped graph.

I would **not treat `tf/0.1.0` as research-safe yet**. The largest remaining problems have shifted away from the damage tracker and toward graph completeness, morphology-selection semantics, provenance verification, and publication safety.

## Summary of findings

| Severity | Finding | Status |
|---|---|---|
| **Critical** | Slotless source structures disappear from TF; counts prove substantial loss | New |
| **Critical** | Multiple `mrp0sel` selections are collapsed to one selection | New |
| **Critical** | `BUILD-COMPLETE` can survive a later unverified rebuild | New |
| **High** | `fragment` slot coverage contradicts both code comments and intended ontology | New |
| **High** | Contract B is still false for real AOxml constructs such as `AO:Akkgram` / `AO:Sumgram` | New |
| **High** | Preservation map promises features/edges the implementation does not produce | New |
| **High** | Contract A is not actually tested against the generated TF graph | Partly known, broader than documented |
| **High** | Morph/sign validation skips the repaired documents used by the converter | New |
| **High** | Structural validation promised by the design is mostly absent | New |
| **High** | Broad exception handling can turn software regressions into known corpus exclusions | New |
| Medium | Corpus identity ignores divergent XML-like shadow files | New |
| Medium | Published feature metadata is stale | New |
| Medium | `docid` remains unsuitable as the level-1 section key | Known |
| Medium | 74 structural XML repairs remain philologically ambiguous | Known |
| Medium | `lex` layer is absent | Known |
| Medium | ~5 GB / ~12 min first load and no TF app remain significant usability problems | Acknowledged |

---

## 1. Critical: source structures are still being silently deleted

This is the most important finding.

The design document explicitly treats the counts measured on the already-parseable source corpus as **lower bounds** for the post-repair graph. Among those source-side figures are:

- 407,623 lines
- 95,101 colons
- 11,663 notes

The shipped [`reports/census.md`](../reports/census.md) reports:

| Type | Source lower bound | `tf/0.1.0` | Minimum deficit |
|---|---:|---:|---:|
| `line` | 407,623 | 397,203 | **−10,420** |
| `colon` | 95,101 | 91,206 | **−3,895** |
| `note` | 11,663 | 8,304 | **−3,359** |

These are conservative deficits because repaired documents should add structures rather than reduce the parse-clean baseline.

The mechanism is visible in [`programs/tlhdig/convert.py`](../programs/tlhdig/convert.py). A line node is created when `<lb>` is encountered, but a line containing no surviving sign gets no slots. Text-Fabric then removes the unlinked node. The converter explicitly knows this can happen: witness-edge construction skips lines not present in `lines_with_slots`, with the comment that empty lines are common in damaged documents.

The artificial-slot workaround currently applies only when an **entire document** has no readable sign. It does not preserve an empty/broken line inside an otherwise readable document. The same basic issue can affect colons and other structural nodes.

This violates Contract B at appreciable scale. It also means the census's successful “section addressing” check is weaker than it looks: one hard-coded section probe succeeds while thousands of source lines do not survive as nodes.

### Recommended fix

Introduce an explicitly marked artificial `sign` anchor for every otherwise-slotless line. Such slots can use, for example:

```text
sym=""
type="empty"
anchor=1
```

and be excluded from linguistic statistics/rendering. The slot overhead is negligible relative to the existing ~3.38M signs.

The note deficit deserves its own source-to-graph census. Notes are currently materialised only when `note_attrs` reaches a sign that becomes a slot, so empty-token paths may be losing note structure too.

---

## 2. Critical: multiple morphological selections are represented incorrectly

[`programs/tlhdig/morph.py`](../programs/tlhdig/morph.py) knows that `mrp0sel` may contain several tokens and sets `Selection.multiple = True`. It then selects only the first numerical selector:

```python
numeric = next((t for t in toks if SEL_TOKEN.match(t)), None)
```

The converter subsequently emits a `selected` edge only for that one `sel.index`. `Selection.multiple` itself is not stored in TF.

These inputs occur in the corpus. Examples include:

```xml
mrp0sel="1a 2a"
```

and:

```xml
mrp0sel="1a 1b"
```

Those encode two different cases:

- `1a 2a`: more than one analysis is selected;
- `1a 1b`: more than one alternative within the same analysis is selected.

A single scalar `(index, alternative)` representation cannot preserve both cases. In particular, a single valued `word -> analysis` edge cannot encode several alternative values on the same `(from, to)` pair because Text-Fabric edge features have only one value per pair.

The current morphology gate cannot detect this because it checks only whether the first parsed selector index points at an existing `mrpN`.

### Recommended fix

Parse the selector as a collection rather than a scalar. Two reasonable designs:

1. materialise explicit `selection` nodes; or
2. allow several `selected` edges to distinct analyses and store a multi-valued `selected_alts` feature on the relevant analysis/selection representation.

Preserve `mrp0sel` raw exactly as now.

Add corpus-level invariants that compare every source selector token with the structured representation produced in TF.

---

## 3. Critical: the publication stamp can be stale

The release flow assumes that presence of:

```text
tf/<version>/BUILD-COMPLETE
```

means the current dataset bytes were verified by `census.py`.

That assumption is not safe.

[`programs/census.py`](../programs/census.py) writes `BUILD-COMPLETE` after loading the dataset and passing its invariants. But [`programs/build.py`](../programs/build.py) rebuilds directly into the existing `tf/<version>` directory and does **not delete an old stamp at the beginning of the build**.

[`programs/publish_dataset.sh`](../programs/publish_dataset.sh) checks only that the stamp file exists:

```bash
[ -f "${dir}/BUILD-COMPLETE" ]
```

So this sequence is possible:

1. build A succeeds;
2. census A succeeds and writes `BUILD-COMPLETE`;
3. build B overwrites the dataset;
4. census B is never run, fails, or is interrupted;
5. the old stamp remains;
6. `publish_dataset.sh` accepts build B.

The script's comment that “a dataset straight out of build.py will not have it” is therefore false for an in-place rebuild of a previously verified version.

### Recommended fix

At minimum, remove `BUILD-COMPLETE` before the first write in `build.py`.

A more robust release architecture would:

1. build into a fresh temporary directory;
2. run census and all release gates there;
3. write a content-bound manifest containing hashes of every `.tf` file plus source-manifest hash, patch-manifest hash, converter commit, and Text-Fabric version;
4. atomically replace `tf/<version>` only after verification succeeds.

---

## 4. High: `fragment` nodes have false slot semantics

The converter comments say:

> A fragment covers the slots of the lines that cite it.

The implementation instead creates every fragment with:

```python
anchor = {state.slots[0]}
fn = cv.node("fragment", slots=anchor)
```

So every fragment's `oslots` contains the first sign of the document regardless of which lines belong to that witness.

The separate `line -> fragment` `witness` edge retains some relationship information, but normal TF APIs that use slot coverage will see a semantically false fragment extent.

### Recommended fix

Either:

- construct fragments after collecting their witness lines and give each fragment the union of those line slots; or
- explicitly define fragments as anchor-only relational nodes and ensure documentation/API examples never imply that `oslots` represents their textual extent.

The first option is preferable if fragment-level containment queries are an intended use case.

---

## 5. High: real writing-system markup survives only as opaque XML

[`programs/tlhdig/signs.py`](../programs/tlhdig/signs.py) has structured wrapper handling for:

```text
sGr
aGr
d
num
c
```

But real AOxml also uses namespaced constructs such as:

```xml
<AO:Sumgram>...</AO:Sumgram>
<AO:Akkgram>...</AO:Akkgram>
```

inside words.

Unknown tags remain present in `srcxml`, which is good for source fidelity, but their semantics are not materialised as TF features. In other words, the bytes survive while the annotation remains opaque.

That directly conflicts with Contract B in [`docs/TF-CONVERSION-PLAN.md`](../docs/TF-CONVERSION-PLAN.md), which states that every linguistic/editorial fact should become a queryable node, edge, or feature rather than surviving only as an opaque string.

### Recommended fix

Build an inventory-driven mapping of all inline AOxml element names actually present in the corpus and classify each as:

- writing-system wrapper;
- range/point annotation;
- value-bearing annotation;
- layout;
- note/reference;
- intentionally raw-only, with justification.

Then add a Contract B gate requiring every source tag/attribute class to have a declared destination.

---

## 6. High: the preservation map is ahead of the implementation

Section 12 of [`docs/TF-CONVERSION-PLAN.md`](../docs/TF-CONVERSION-PLAN.md) promises constructs including:

- `joins` edges;
- `sign.lang`;
- `cu_pua_unmapped`;
- `cth_alt` / `cth_neu`;
- repaired-stream provenance such as `repaired_span`.

Several of these are not emitted by the current converter.

For example, manuscript joins are flattened into document string features (`directjoin`, `indirectjoin`) rather than represented as a graph. `repaired_span` does not exist in the emitted schema. Other planned fields similarly remain absent.

This is specification drift rather than ordinary missing polish because the preservation map is written as the schema contract for Contract B.

### Recommended fix

Turn the preservation map into an implementation-status matrix:

| Source construct | Destination | Status | Verification |
|---|---|---|---|
| ... | ... | implemented / partial / raw-only / pending | gate/test |

No row should remain simply aspirational while the document presents it as an existing guarantee.

---

## 7. High: Contract A is not validated against the generated graph

[`programs/check_contract_a.py`](../programs/check_contract_a.py) verifies the source span scanner by:

1. scanning source XML;
2. checking the scanner's spans against those same source bytes.

It never loads the generated TF dataset and never reads a generated `src_span` feature.

Therefore it can establish that `source.py` works, but not that:

- the converter attached the correct span to the correct TF node;
- `OffsetMap` translated repaired coordinates correctly;
- compaction preserved those feature assignments;
- the shipped graph's provenance actually points to the claimed source bytes.

The current `KNOWN-ISSUES.md` now acknowledges part of this, correctly.

### Recommended fix

Create an **independent post-build Contract A gate** that:

1. loads the shipped TF graph;
2. iterates every node carrying `src_span`;
3. opens its `src_file`;
4. slices the original bytes;
5. independently validates that slice against the source construct the TF node claims to represent.

All repaired documents should be checked exhaustively.

---

## 8. High: sign and morphology gates do not run over repaired streams

[`programs/check_signs.py`](../programs/check_signs.py) scans raw corpus files and skips files that fail source parsing.

[`programs/check_morph.py`](../programs/check_morph.py) likewise parses the raw XML and skips unparseable files.

The actual converter, however, applies [`programs/patches.yaml`](../programs/patches.yaml) first and successfully converts many of those files.

[`programs/verify_patches.py`](../programs/verify_patches.py) proves repaired XML becomes syntactically valid, but does not subsequently run the full sign/morphology gates against those repaired bytes.

A tokenisation or morphology defect present only in repaired content is therefore outside the main parser gates.

### Recommended fix

Make corpus-level checks operate on the **same repaired stream that the converter uses**, while retaining separate raw-source checks where source fidelity requires them.

---

## 9. High: structural invariants from the design are mostly not executable

The design specifies checks such as:

- `collabel` unique within a document;
- every line belongs to exactly one column;
- every column belongs to one surface;
- every surface belongs to one document;
- witness membership is valid;
- source counts form lower bounds for post-repair graph counts.

Current [`programs/census.py`](../programs/census.py) checks mainly:

- sign flags vs. cluster coverage;
- source/document arithmetic;
- one section-addressing probe;
- duplicate `docid` as an informational statistic.

This is how the graph can report “all invariants hold” while carrying at least 10,420 fewer line nodes than the documented source lower bound.

### Recommended fix

Implement the full structural checks from the design, especially the source-lower-bound census. That one check would have exposed the line/colon/note losses immediately.

---

## 10. High: broad exception handling can hide software regressions

The conversion loop contains logic equivalent to:

```python
try:
    spans = source.scan(data)
    root = LE.fromstring(data)
except Exception:
    ledger.exclude(rel, "unparseable")
```

This conflates malformed source XML with arbitrary implementation failures.

An `IndexError`, `TypeError`, or regression in `source.scan()` on a file already allowlisted as `unparseable` can therefore be converted into the same expected exclusion reason and accepted by the ledger.

### Recommended fix

Catch parser exceptions narrowly. Any unexpected exception should abort the build with a traceback.

Apply the same rule to corpus gates where broad catches currently mean “skip this source”.

---

## 11. Medium: corpus identity ignores divergent XML-like shadow files

[`programs/tlhdig/corpusid.py`](../programs/tlhdig/corpusid.py) defines the source universe via:

```python
root.rglob("*.xml")
```

The checked-in corpus tree contains at least one extensionless AOxml file, `CTH 832_XML_TLH/KUB 31.116`, alongside `KUB 31.116.xml`. The two files differ in content.

This does **not** prove that the extensionless copy belongs to the official 23,937-record corpus; it may be an accidental shadow file. It does show that a directory described as an immutable upstream release can contain divergent AOxml material outside the identity manifest.

### Recommended fix

Pin the entire upstream archive inventory, not only `*.xml`, or explicitly whitelist known auxiliary file classes and fail on unexpected XML-like content.

---

## 12. Medium: generated corpus metadata is stale

[`programs/tlhdig/featuremeta.py`](../programs/tlhdig/featuremeta.py) still contains descriptions that no longer match the implementation. For example, the `docid` description says the planned `docgroup` layer is not implemented even though `docgroup` nodes now exist.

That stale text has propagated into the generated TF feature metadata itself.

There is also a smaller provenance/documentation mismatch: `docid_raw` is described as verbatim `<docID>`, while the converter sets it to the same stripped string as `docid`.

### Recommended fix

Treat feature metadata as part of the generated public API. Add tests that compare declared feature descriptions/statuses against the actual emitted schema.

---

## Known architectural issues that remain valid

### Duplicate `docid`

`docgroup` is useful, but `docid` remains a manuscript identity rather than a unique record identity. There are 141 duplicated `docid` values in the current graph, so using `docid` as the level-1 section feature can still produce ambiguous addresses.

A cleaner long-term design would use an unambiguous **record ID**—probably derived from `src_file` or another stable source-record key—for section addressing, while retaining `docid` as manuscript identity and `docgroup` for equivalence/grouping.

### Crossing-tag repairs

The 74 structural crossing-tag repairs remain genuine philological uncertainties. Hash-pinned patches and XML validity prove reproducibility, not that moving a wrapper/word boundary expresses the original editor's intention.

The current approach—cataloguing them for specialist review rather than pretending they are mechanically resolved—is appropriate.

### Missing `lex`

The missing lexical layer is lower priority than the completeness and selector defects above. It is derived convenience data and can safely wait until occurrence-level morphology is proven correct.

---

## Validation and CI architecture

The ordinary CI is useful but still heavily component-oriented. It runs:

- unit tests;
- corpus identity;
- repair-manifest verification;
- source sign round-trip;
- morphology parsing.

The complete dataset build plus census and independent marker comparison runs in a separate scheduled/on-demand workflow.

The project's regression history suggests a clear pattern: local components are often correct, while integration bugs appear when their outputs are wired into the TF graph. The damage-cluster bugs repeatedly passed unit tests and were found only at corpus scale.

### Recommended CI addition: deterministic adversarial integration shard

Every PR should build a real TF dataset from a small deliberately difficult corpus subset, perhaps 50–200 documents containing:

- repaired files;
- nested `<w>`;
- contentless lines;
- contentless words;
- composite witnesses;
- duplicate `docid`;
- multiple `mrp0sel` forms;
- `AO:Akkgram` and `AO:Sumgram`;
- all damage families;
- cross-line damage;
- documents with no readable signs;
- lines with no readable signs inside otherwise readable documents;
- heavy notes and editorial metadata.

The shard test should load the generated TF in a fresh process and compare source-construct censuses with graph-construct censuses.

Keep the full 23,937-file build as the release gate.

---

## Usability gaps

The latest README correctly fixes one previous false claim: it no longer says `use("alexsosn/TLHdig-TF")` works before an `app/` directory exists, and it documents the direct `Fabric` loading path.

The remaining usability cost is significant:

- first full load is roughly 12 minutes;
- peak memory is roughly 5 GB;
- subsequent loads are much faster but still require a compiled local cache;
- there is no TF app/rendering layer yet.

An `app/` with curated feature loading, useful formats, search examples, and good fragment/damage rendering would help substantially. It should come after the graph-completeness defects are fixed so that the app does not make an incomplete ontology easier to consume.

---

## Recommended priority

| Priority | Work |
|---|---|
| **P0** | Preserve every `<lb>` / `clb` / note and investigate all source-lower-bound count violations |
| **P0** | Correct multi-valued `mrp0sel` modelling |
| **P0** | Make dataset builds fresh/atomic and make verification stamps content-bound |
| **P1** | Implement a true TF-vs-source Contract A gate |
| **P1** | Add a full Contract B source-to-graph census |
| **P1** | Model `AO:Akkgram`, `AO:Sumgram`, and inventory all remaining AOxml constructs |
| **P1** | Fix fragment extents and implement the witness/join graph |
| **P1** | Run sign/morph gates over repaired streams |
| **P1** | Narrow exception handling |
| **P2** | Replace `docid` as section identity |
| **P2** | Synchronise design, feature metadata, and generated documentation |
| **P2** | Add `lex` |
| **P3** | TF app/renderers and usability work |

## Architectural conclusion

The project has become good at preserving and validating **local representations**, but it still lacks a single authoritative **source construct → TF construct completeness gate**.

Damage-marker handling became much more trustworthy once it acquired an independent source-to-graph conservation check. The rest of Contract B needs the same treatment.

Until then, `tf/0.1.0` is best described as an **integration prototype with demonstrable structured-data loss**, rather than a beta research corpus. The line/colon/note deficits and multi-selector bug are sufficient on their own for that verdict.
