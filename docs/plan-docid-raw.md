# Plan: make `docid_raw` source-derived

**Issue:** #10  
**Research prerequisite:** `docs/research-docid-raw.md`

This ticket follows **research → plan → RED → implement → test → independent review**.
No production converter, feature metadata, version constant, generated artifact, or current-version
documentation may change before this plan is committed.

## 1. Research result that constrains the design

The pinned TLHdig Beta 0.3 converter population contains 23,884 document records. Every one has
a present, non-empty `<docID>` and none uses the filename fallback. Exactly three parsed values
differ from `.strip()`, all by one trailing ASCII space:

```text
CTH 209_XML_TLH/KBo 50.89 .xml   -> 'KBo 50.89 '
CTH 628_XML_HFR/Merzifon I .xml  -> 'Merzifon I '
CTH 670_XML_TLH/KBo 71.241 .xml  -> 'KBo 71.241 '
```

No current value contains TAB/LF/CR or nested `<docID>` markup. A separate Text-Fabric 13.1.0
`CV.walk` → fresh `Fabric.load` experiment proves that the trailing space survives exactly.

Therefore this is a correction to values of an existing shipped feature, not a new ontology and
not an identifier redesign.

## 2. Semantic contract

Keep `docid` **exactly** as it behaves today:

```python
docid = (raw_docid or Path(rel).stem).strip()
```

Define `docid_raw` as:

> the parsed textual content returned by `root.findtext("AOHeader/docID")`, before `.strip()`
> and before filename fallback.

It is source-derived but not byte-for-byte XML markup. XML entity expansion and parser line-ending
normalization happen before this value exists.

### Missing / empty policy

The feature represents textual content, not XML-element presence.

- present, non-empty source text: emit that string exactly, including leading/trailing whitespace;
- present, whitespace-only source text: emit the whitespace exactly;
- missing `<docID>`: omit `docid_raw`;
- present `<docID>` with no text / empty string: omit `docid_raw`.

Missing-vs-present-empty element provenance is out of scope. If that distinction becomes
research-relevant it requires a separate source-structure feature, not a synthetic value in
`docid_raw`.

This policy preserves the existing `docid` filename fallback independently.

## 3. Version and publication policy

TF `0.2.0` is already published and immutable as `tlhdig-0.3_tf-0.2.0`.
The corrected feature changes three real graph values, so do not rebuild `0.2.0` in place.

Bump:

```text
SOURCE_VERSION = 0.3       unchanged
TF_VERSION     = 0.2.1     patch correction to existing feature semantics
RELEASE_TAG    = tlhdig-0.3_tf-0.2.1
```

A patch version is appropriate because no feature is added/removed, no node/edge model changes,
and no public addressing/grouping contract changes; only an existing feature is made faithful to
its documented source meaning.

Preserve `tf/0.2.0`, `tf-provenance/0.2.0`, `tf/0.1.0`, and `tf-provenance/0.1.0` unchanged.

## 4. RED gate — tests before production

Add tests first and run CI on the test-only head. Required contract tests:

1. source `<docID>` with a trailing space yields normalized `docid` and unstripped `docid_raw`;
2. source `<docID>` with leading and trailing spaces preserves both in `docid_raw` while `docid`
   remains stripped;
3. missing `<docID>` keeps the current filename-derived `docid` but omits `docid_raw`;
4. empty `<docID/>` keeps the current filename-derived `docid` but omits `docid_raw`;
5. whitespace-only `<docID>` preserves its whitespace in `docid_raw` and preserves the current
   `docid == ""` behavior; if a full TF fixture cannot represent a blank section heading, test this
   extraction boundary without changing production behavior merely to satisfy the fixture;
6. duplicate grouping remains keyed by normalized `docid`, not `docid_raw`;
7. `TF_VERSION` target is `0.2.1` only after the behavior RED has been demonstrated; the version
   bump itself must not be used as a substitute for the semantic RED.

The RED is valid only when failures correspond to the old `docid_raw=docid` behavior, not an
invalid Text-Fabric fixture.

## 5. Minimal implementation

In `programs/tlhdig/convert.py`, at the document boundary:

```python
raw_docid = root.findtext("AOHeader/docID")
docid = (raw_docid or Path(source_path.src_file).stem).strip()
```

Emit `docid_raw=raw_docid` only when `raw_docid not in (None, "")`.
Do not use `source_stem` as the fallback expression if doing so would alter current semantics;
retain the existing `Path(rel).stem` behavior equivalently.

Do not modify:

- `OTEXT.sectionFeatures`;
- `docgroup` construction or `edition` edges;
- `src_file` semantics;
- `project` / `subcorpus` behavior;
- source-path parsing;
- filename normalization;
- `docid` normalization/fallback policy.

Update `programs/tlhdig/featuremeta.py` so `docid_raw` describes the actual new contract and does
not claim byte-level XML fidelity.

Then bump `TF_VERSION` to `0.2.1` and update current operational documentation only after the
semantic tests are green.

## 6. Post-implementation unit / CI gate

Require the complete unit/adversarial suite to pass, then the normal repository CI gates:

1. corpus identity;
2. repair manifest;
3. sign round-trip;
4. morphology;
5. app config;
6. build stamp for the currently committed release until the new artifact is generated;
7. AOxml destination coverage;
8. provenance split;
9. cuneiform alignment;
10. outside-sign-list gate when references are available.

Because `TF_VERSION=0.2.1` makes the old committed build stamp intentionally stale, the artifact
rebuild follows immediately after code/unit correctness is established; CI configuration or tests
must distinguish the planned pre-artifact transition rather than weakening stamp validation.

## 7. Clean TF 0.2.1 artifact rebuild

Build a new versioned artifact from the reviewed generator; never overwrite 0.2.0.

Required sequence:

1. verify `SOURCE_VERSION=0.3`, `TF_VERSION=0.2.1`;
2. record tree SHAs of all published 0.2.0 and 0.1.0 artifact directories;
3. remove only any branch-local unreleased `tf/0.2.1` / `tf-provenance/0.2.1` remnants;
4. run the complete unit/adversarial suite;
5. run `programs/build.py` to produce `0.2.1`;
6. run census and write `BUILD-COMPLETE`;
7. run marker conservation, structure conservation and Contract A;
8. run all ordinary corpus/release gates;
9. run `programs/publish_dataset.sh` or its equivalent certified staging gate;
10. prove published 0.2.0 and 0.1.0 trees remain byte-identical;
11. commit only the certified 0.2.1 artifact and generated current reports.

## 8. Artifact-specific regression proof

Load `tf/0.2.0` and `tf/0.2.1` selectively and compare documents by `src_file`.
Require:

- exactly 23,884 documents in both;
- identical `src_file` sets;
- `docid` identical for every document across versions;
- section features unchanged;
- `project == subcorpus` still holds for every 0.2.1 document;
- exactly **three** `docid_raw` values differ between 0.2.0 and 0.2.1;
- the three changed `src_file` values are exactly the research-measured paths above;
- their 0.2.1 values are exactly `'KBo 50.89 '`, `'Merzifon I '`, and `'KBo 71.241 '`;
- fresh Text-Fabric reload preserves those trailing spaces;
- no current document lacks `docid_raw` because all current source `<docID>` values are present
  and non-empty;
- node/edge counts and existing census invariants remain unchanged except generated timestamps and
  version metadata.

Also compare the 0.2.1 graph against repaired source `<docID>` values directly, not merely against
hard-coded examples.

## 9. Current-version documentation

After 0.2.1 exists, update operational/current references such as:

- README current version and load paths;
- KNOWN-ISSUES current artifact heading/wording;
- CITATION.cff version;
- Agora/direct-load examples where they describe this repository's current path;
- generated provenance README via `TF_VERSION`.

Do not rewrite historical reports or the published 0.2.0 release record.

## 10. Independent review before merge

Review the final post-rebuild diff independently from the implementation pass. At minimum challenge:

- did `docid` change anywhere, including fallback and whitespace-only behavior?;
- is `docid_raw` actually source-derived and unstripped?;
- are missing/empty values omitted rather than filename-derived?;
- can TF 13.1.0 reload the three real trailing-space values exactly?;
- did grouping remain keyed by normalized `docid`?;
- did section addressing remain unchanged?;
- were 0.2.0 / 0.1.0 artifacts mutated?;
- is `0.2.1` a clean rebuild from the reviewed converter?;
- do source version, TF version, docs, stamps and release tag agree?;
- did any unrelated identifier or ontology change leak into the ticket?

Every testable review finding loops back through RED regression → fix → relevant full gates →
independent re-review.

## 11. Merge and release

Only after the final independent review and green gates:

1. merge with an expected-head-SHA guard;
2. require post-merge CI on the exact merge commit;
3. verify `main` still points to that commit;
4. create tag and GitHub Release `tlhdig-0.3_tf-0.2.1` on that exact merge commit;
5. verify the remote tag SHA and non-draft/non-prerelease release state.
