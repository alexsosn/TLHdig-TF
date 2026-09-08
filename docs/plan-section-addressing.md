# Plan: exhaustive source-faithful section addressing (#15)

Research: `docs/research-section-addressing.md`

## Boundary

The 39 lines measured on the 0.2.0 research baseline without usable `lnr` are genuinely
unnumbered in the pinned source; none can be assigned a scholarly-looking line number
without inference. Existing `lnr`, `lnno`, `collabel`, `frag`, and document identity
therefore remain source-facing features and are not overwritten.

Issue #16 owns duplicate `docid` values and level-1 identity. This ticket changes only
level-2/3 section-address features. The repository has advanced to newer immutable TF
artifacts since the research run, so implementation must first rebase onto current
`main`, rerun the census, and target the next unused immutable TF version. It must not
rewrite any published artifact or depend on the obsolete 0.2.1 sequencing assumption.

## Section schema

Add two explicit address features:

- `coladdr`: level-2 Text-Fabric section address;
- `lineaddr`: level-3 Text-Fabric section address.

Configure:

```text
sectionTypes=document,column,line
sectionFeatures=docid,coladdr,lineaddr
```

Source-facing display/citation data remain in `collabel` and `lnno`.

For an already usable and unique source heading, the address feature mirrors the source
value exactly:

```text
coladdr = collabel
lineaddr = lnno
```

Only a missing/empty value or a value that would collide at its TF section level receives
a synthetic internal address.

## Synthetic namespace

Use the fixed reserved prefix:

```text
__tlhdig_internal__:
```

A repository-wide search at planning time found no occurrence of this prefix. The
production corpus gate must independently scan every source `collabel`/line-label
candidate and fail if the prefix occurs; the implementation must not silently choose
another prefix.

Synthetic values are deterministic from source order, not node numbers:

```text
coladdr  = __tlhdig_internal__:column:<column ordinal within document>
lineaddr = __tlhdig_internal__:line:<srcln>
```

`srcln` is the source line ordinal already recorded on each line. Column ordinal is the
converter's source-order ordinal among emitted columns in that document. These values are
internal addresses only and must never be rendered/documented as scholarly line labels.

## Collision policy

Address generation is two-pass per document/column:

1. collect source-facing candidate values and occurrence counts;
2. mirror a source value only when it is non-empty and unique in the required scope;
3. synthesize every missing or colliding occurrence with the fixed namespace;
4. verify all resulting addresses are unique before emitting/finishing the document.

Scopes:

- `coladdr`: unique within a document;
- `lineaddr`: unique within its `coladdr`.

A source duplicate is preserved unchanged in `collabel`/`lnno`; only the address feature
is disambiguated. A collision involving a synthetic value or the reserved prefix is a
hard build failure, never repaired by suffix guessing.

## RED gate

Before production code, add tests for:

1. ordinary unique `collabel`/`lnno` mirror exactly into `coladdr`/`lineaddr`;
2. missing `lnr` preserves absent/empty source-facing values but receives deterministic
   synthetic addresses;
3. empty `lnr` remains distinguishable from a missing `lnr` in source-facing data;
4. two missing lines in one column receive distinct deterministic addresses;
5. duplicate non-empty `lnno` values preserve the duplicates in `lnno` while `lineaddr`
   becomes unique;
6. duplicate/missing column headings are handled analogously by `coladdr`;
7. reserved-prefix input causes a hard failure;
8. rebuild from identical source produces byte-identical address features;
9. `T.sectionFromNode()` / `T.nodeFromSection()` round-trip every emitted line address;
10. the 39 baseline cases become addressable without assigning any synthetic value to
    `lnr`, `lnno`, or `collabel`;
11. the two terminal repaired-source `<lb>` baseline candidates that do not become line
    nodes do not create phantom TF addresses;
12. pre-existing duplicate `docid` ambiguity is reported separately and is not counted
    as a #15 failure;
13. the current-main census is recorded before implementation, so changed baseline counts
    cannot be hidden by carrying forward stale constants.

The RED commit must change tests/checkers only; no converter/address implementation until
those failures are demonstrated.

## Implementation

Prefer a small pure address allocator module so collision/source-order behavior can be
unit-tested without a full TF build. The converter supplies source-facing column/line
records, receives deterministic addresses, and writes `coladdr`/`lineaddr` when nodes are
created.

Do not derive synthetic values from TF node ids: node ids can shift when unrelated graph
features change and are not source-stable identifiers.

Update feature metadata and app/README documentation to distinguish source citation
features from internal section-address features.

## Exhaustive corpus gate

Replace the current one-probe section census with an exhaustive validator over every
emitted line. It must:

- enumerate every line node;
- require non-empty `coladdr` and `lineaddr`;
- require uniqueness in the documented scopes;
- run `sectionFromNode()` then `nodeFromSection()` for every line and require the same
  node back;
- classify failures as level-1 (`docid`) ambiguity vs level-2/3 address failure;
- assert #15 introduces zero new level-2/3 collisions;
- prove all baseline unaddressed cases that still exist on current `main` now round-trip;
- prove source-facing `lnr`/`lnno`/`collabel` values on those cases remain unchanged;
- record counts of mirrored vs synthetic column/line addresses.

The gate must not suppress duplicate `docid` groups. They are reported as pre-existing
level-1 ambiguity owned by #16, while this ticket's level-2/3 guarantees are measured
independently.

## Artifact / release gate

Rebase onto current `main`, rerun the research census against the current TF version,
choose the next unused immutable TF version, build once, and run the repository's
canonical full release certification. No release is acceptable with a legacy census-only
stamp or certification against stale bytes.

Required final evidence:

- current-main pre-fix census;
- RED run(s);
- focused unit GREEN;
- exhaustive section-address report;
- normal CI;
- canonical release certification on the new artifact;
- before/after count of unaddressable lines at levels 2/3;
- confirmation that source-facing values were not synthesized;
- exact artifact/version and commit identity.

## Independent adversarial review

A logically independent reviewer must challenge:

- synthetic values leaking into `lnr`, `lnno`, `collabel`, or user-facing scholarly
  citations;
- address allocation depending on TF node ids or nondeterministic iteration;
- hidden collisions when source labels duplicate;
- a validator that checks only the known baseline cases instead of every line;
- section round-trip that accidentally succeeds against a different document in a
  duplicate-`docid` group;
- treating #16's level-1 ambiguity as fixed by this ticket;
- changing the reserved namespace/baseline merely to make a failing corpus gate green;
- artifact/version reuse or release certification against stale bytes.

Blocking findings return to implementation → tests → fresh independent review before the
implementation PR can be finalized.
