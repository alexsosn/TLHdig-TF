# Plan: build mature user documentation for TLHdig-TF

## Goal

Create a documentation layer for TLHdig-TF that is:

- usable by Hittitologists who know little or no Text-Fabric;
- precise enough for corpus linguistics and reproducible research;
- complete at the feature/edge level;
- explicit about uncertainty and source-derived versus inferred semantics;
- synchronized with the **released TF graph**, not merely the conversion plan;
- supported by executable tutorials and research examples;
- automatically checked for schema/documentation drift.

This work should preserve the existing conversion research and plan as developer/design
documents. The new documentation is an end-user layer on top of them.

---

## Guiding rules

### 1. Released data beats design documents

Never document a node type, feature, edge, text format, or section as present merely
because `TF-CONVERSION-PLAN.md` says it should exist.

Generate the public schema inventory from the released/loaded TF build.

### 2. One source of truth for volatile facts

Do not hand-copy:

- node counts;
- feature coverage counts;
- observed feature vocabularies;
- edge cardinalities;
- exclusion counts;
- corpus version strings.

Generate them from the build or from checked metadata.

### 3. One source of truth for short feature semantics

Keep `programs/tlhdig/featuremeta.py` as the canonical source for TF
`@description` strings.

Add documentation metadata around it rather than duplicating the descriptions in
Markdown.

### 4. Raw values remain authoritative where semantics are unresolved

Use a documented semantic-status system:

- `confirmed`
- `measured`
- `reverse-engineered`
- `provisional`
- `raw-only-authoritative`

A derived feature with uncertain upstream semantics must say so.

### 5. Examples use stable scholarly addresses

Prefer:

- `docid` + `collabel` + `lnno`, with an edition/record disambiguator where required;
- source file identifiers where section addresses are ambiguous.

Do not build tutorials around raw TF node numbers as if they were persistent IDs.

### 6. Every code example must be executable

Tutorial code and README snippets should be run in CI against the documented release.

---

# Phase 0 — establish the documentation target

## 0.1 Verify how users obtain the dataset

At the time of the documentation audit (2026-08-29):

- the README advertises `tf/0.1.0/`;
- GitHub's Contents API did not expose `tf/` or `tf/0.1.0/`;
- the GitHub releases endpoint was empty.

Before writing installation instructions, decide the actual distribution mechanism:

- committed TF files;
- GitHub release asset;
- Zenodo artifact;
- generated locally from source;
- another Text-Fabric-supported checkout/release layout.

### Acceptance

This command, or its documented replacement, works in a clean environment:

```python
from tf.app import use
A = use("alexsosn/TLHdig-TF")
```

If it does not, the docs must not advertise it without the required parameters or build
step.

---

## 0.2 Define the exact release being documented

Record in one machine-readable place:

```text
upstream TLHdig version
TF schema/build version
tested Text-Fabric version/range
source corpus hash
release tag / commit / DOI
```

Suggested location:

```text
programs/tlhdig/version.py
```

or another existing build metadata module if one already serves this purpose.

### Acceptance

`docs/about.md`, generated feature docs, notebooks, and README all obtain or verify the
same version metadata.

---

## 0.3 Regenerate validation state

Before docs authoring:

1. run the full build;
2. run the ledger/exclusion checks;
3. run `census.py`;
4. run source-marker/source-span gates;
5. record current `KNOWN-ISSUES.md` state;
6. freeze a release candidate.

Do not write detailed examples against a moving ontology.

---

# Phase 1 — documentation metadata and generation

## 1.1 Add documentation metadata

Create:

```text
programs/tlhdig/docmeta.py
```

or extend `featuremeta.py` cleanly.

Recommended structure:

```python
FEATURE_DOC = {
    "lemma": {
        "status": "confirmed",
        "source": "w/@mrpN field 1",
        "applies_to": ("analysis",),
        "related": ("gloss", "morph", "pos", "stemclass"),
    },
    "sel_group": {
        "status": "provisional",
        "source": "w/@mrp0sel",
        "applies_to": ("word",),
        "related": ("mrpsel", "sel_base", "sel_clitic"),
        "note": "sg/pl semantics are not formally documented upstream",
    },
}
```

For edges:

```python
EDGE_DOC = {
    "analyses": {
        "source_type": "word",
        "target_type": "analysis",
        "cardinality": "one-to-many",
        "valued": False,
        "status": "confirmed",
    },
}
```

### Include

- semantic status;
- source AOxml field/path;
- expected node type;
- related features;
- optional extended note;
- closed vocabulary override where automatic enumeration is inappropriate;
- whether absence has special meaning.

### Do not include manually

- observed value counts;
- node coverage counts;
- edge counts.

Those come from the dataset.

---

## 1.2 Build a documentation generator

Create:

```text
programs/docs/build_docs.py
```

Responsibilities:

1. load the exact target TF release;
2. enumerate node features, edge features, warp features;
3. retrieve TF value types and descriptions;
4. derive observed source/target node types for edges;
5. compute coverage counts;
6. enumerate values for low-cardinality features;
7. produce stable example passages;
8. combine generated facts with `featuremeta.py` and `docmeta.py`;
9. write generated documentation.

### Generated outputs

```text
docs/features.md
docs/features/<feature>.md
docs/generated/schema.md
docs/generated/node-counts.md
```

`docs/features.md` is the index promised by the existing conversion plan.

Individual feature pages should be generated because ~80+ features are too many for one
maintainable page.

---

## 1.3 Preserve manual notes safely

Use explicit generated blocks:

```markdown
<!-- BEGIN GENERATED -->
...
<!-- END GENERATED -->

## Interpretation notes

Manual prose here...
```

The generator may replace only the generated block.

Alternative: generate the entire feature page from structured metadata and keep longer
conceptual prose in topic pages. Prefer that if it stays readable.

---

## 1.4 Add documentation drift checks

Create:

```text
programs/docs/check_docs.py
```

Fail if:

- a released feature has no `@description`;
- a released feature is absent from the generated reference;
- `docmeta.py` claims the wrong node type;
- an edge's observed source/target types conflict with metadata;
- a documented closed vocabulary omits observed values;
- generated files differ from checked-in files;
- an internal Markdown link is broken;
- a notebook refers to a missing feature;
- README/tutorial quick-start cannot load the release.

Add this to CI after the release distribution exists.

---

# Phase 2 — core conceptual documentation

Write these pages manually, using generated tables rather than copied counts.

---

## 2.1 `docs/index.md`

### Content

- one-paragraph corpus summary;
- documentation map;
- four entry routes:
  - "I am a Hittitologist";
  - "I know Text-Fabric";
  - "I want the feature reference";
  - "I want research examples";
- current release/status warning;
- links to `KNOWN-ISSUES.md` and census.

### Acceptance

A new user can reach any major documentation topic in at most two clicks from the
README.

---

## 2.2 `docs/about.md`

### Content

- upstream TLHdig identity and DOI;
- creators/institutions;
- source corpus version;
- TF release version;
- coverage summary;
- source versus generated-data distinction;
- exclusions;
- licences:
  - source corpus;
  - converter/docs;
- citation;
- acknowledgements;
- link to reproducibility and known issues.

### Rule

Do not repeat volatile node counts. Link/embed generated census tables.

---

## 2.3 `docs/model.md`

### Content

1. Text-Fabric model in ~2 paragraphs;
2. why `sign` is the slot;
3. current node types grouped:
   - textual/structural;
   - analytical;
   - editorial;
   - relational;
4. graph diagram;
5. section types/features;
6. structure hierarchy;
7. edge table;
8. text formats;
9. current node counts from generated include;
10. planned-vs-released warning.

### Diagram

Prefer Mermaid in Markdown, generated from schema metadata if feasible:

```text
document
  -> surface / column / line
line
  -> word
word
  -> sign
word --analyses--> analysis
word --selected--> analysis
line --witness--> fragment
document --edition--> docgroup
cluster --startsAt/endsAt--> sign
note --noteref--> sign
```

The exact diagram must reflect the release.

---

## 2.4 `docs/transcription.md`

### Content checklist

- AOxml overview;
- sign segmentation;
- `srcxml`, `sym`, `after`;
- sign `type`;
- writing-system flags:
  - `sgr`
  - `agr`
  - `det`
  - `num`
- correction/editorial sign annotations:
  - `corr`
  - `subscr`
  - `materlect`
  - `surplus`
- layout nodes / contentless `<w>`;
- line reference grammar;
- surfaces, columns, fragments;
- language features;
- line-level cuneiform;
- PUA/broken cuneiform flags;
- source spans;
- repair stream/original source relationship;
- available text formats;
- links to conversion research.

### Hittitologist review gate

Mark unresolved semantics clearly before publication.

---

## 2.5 `docs/morphology.md`

### Content checklist

- one diagram: `word -> analyses -> analysis`;
- `mrpN` conversion;
- sparse/zero-based indices;
- base analysis fields;
- clitic fields;
- selector model;
- selected versus unresolved words;
- `mrpsel_kind`;
- `sel_base`;
- `sel_clitic`;
- `sel_group`;
- field 4 and `field4_kind`;
- `parse_ok`;
- unanalysed words;
- all relevant code tables;
- 5–10 real examples;
- minimal TF API examples;
- minimal TF Search examples;
- semantic-status table for disputed fields.

### Required query snippets

- all analyses for one word;
- selected analysis if present;
- words with >1 candidate and no selected analysis;
- lemma search;
- POS + morph search;
- clitic search.

---

## 2.6 `docs/damage.md`

### Content checklist

- source marker families;
- cluster node definition;
- point versus span;
- `width`;
- `orphan`;
- marker offsets;
- synthesized boundaries;
- `from_open_marker`;
- `from_close_marker`;
- `startsAt`;
- `endsAt`;
- induced sign flags;
- cross-line behaviour;
- recommended secure/damaged filters;
- examples of a zero-width point and a real span;
- validation/census links.

### Required warning

Show explicitly why this is wrong for "damaged word":

```text
cluster type=del
```

without excluding `width=0` point markers when the user's definition requires actual
damaged coverage.

---

## 2.7 `docs/query-guide.md`

### Minimal sections

1. installation/loading;
2. pinning version;
3. section addressing;
4. text retrieval;
5. features;
6. locality/containment;
7. edges;
8. TF Search;
9. morphology;
10. damage;
11. metadata/CTH/subcorpus/language;
12. witnesses/editions;
13. export;
14. performance;
15. common mistakes.

### Common mistakes table

Must include:

- lemma on `analysis`, not `word`;
- selection can be absent;
- `docid` may not be unique;
- `cu` is not sign-aligned;
- point clusters;
- `None` versus source sentinel/empty value;
- raw node IDs are not scholarly persistent IDs.

---

## 2.8 `docs/reproducibility.md`

### Content checklist

- upstream DOI/version/hash;
- TF release/version;
- build command;
- repair manifest;
- exclusion ledger;
- known lossy file(s);
- crossing-tag review;
- validation gates;
- census;
- test/CI status;
- how to reproduce a release;
- frozen-release policy;
- schema compatibility policy.

---

# Phase 3 — generated feature reference

## 3.1 `docs/features.md`

Generate an index grouped by node type/concept:

- TF warp;
- sign;
- word;
- analysis;
- cluster;
- line;
- column/surface;
- document;
- edit;
- note/fragment/docgroup/lex if present;
- edges.

Columns:

| feature | kind | node type | value type | coverage | status | description |
|---|---|---|---|---:|---|---|

Every feature links to its detailed page.

---

## 3.2 Individual feature pages

Template:

```markdown
# `sel_group`

**Kind:** node feature  
**Node type:** `word`  
**Value type:** string  
**Semantic status:** provisional  
**Source:** `w/@mrp0sel`

<short description from featuremeta>

## Values

| value | count | meaning |
|---|---:|---|
| all | ... | ... |
| sg | ... | upstream semantics not formally documented |
| pl | ... | upstream semantics not formally documented |

## Related features

...

## Example

Stable passage + Python snippet.

## Caveats

...
```

For high-cardinality free-text features (`comment`, `gloss`, `srcxml`) do not dump value
tables. Show cardinality, null coverage, and representative samples only.

---

# Phase 4 — foundational tutorials

Create `tutorial/README.md` explaining the order and tested corpus version.

---

## 4.1 `tutorial/00_start.ipynb`

### Tasks

- load the corpus;
- print version metadata;
- show node counts;
- find a real tablet by section;
- show plain/source transliteration;
- inspect one line;
- inspect one word and its signs.

### Acceptance

Runs from top to bottom in a clean environment.

---

## 4.2 `tutorial/01_model_and_text.ipynb`

### Tasks

- inspect `otype`;
- navigate up/down;
- show sections;
- compare text formats;
- show line-level cuneiform;
- inspect a relational edge.

---

## 4.3 `tutorial/02_morphology.ipynb`

### Tasks

Use real words that demonstrate:

- one selected analysis;
- multiple candidates;
- no selector;
- clitic analysis;
- sparse or zero-based analysis index if possible;
- `parse_ok=0` example if one survives in release.

Do not fabricate examples.

---

## 4.4 `tutorial/03_damage.ipynb`

### Tasks

Use real examples of:

- regular damage span;
- zero-width `del` point;
- mid-sign boundary;
- cross-line range;
- orphan range;
- damage-aware lemma concordance.

---

## 4.5 `tutorial/04_search.ipynb`

Progression:

1. form;
2. lemma;
3. lemma + morph;
4. ordered multiword query;
5. CTH/subcorpus constraint;
6. morphology + damage exclusion;
7. relational edge query if TF Search syntax supports the exact released relation
   cleanly; otherwise combine search with API edge traversal.

---

## 4.6 `tutorial/05_export.ipynb`

### Tasks

- export one document;
- export a lemma concordance;
- include candidate analyses;
- include damage status;
- include stable textual address;
- write CSV and Parquet;
- record release metadata next to output.

---

# Phase 5 — research-grade cookbook

Use `docs/applications-deep-research-report.md` as the design source.

Implement first:

```text
tutorial/research/
  damage_aware_concordance.ipynb
  morphology_ambiguity.ipynb
  parallel_passages.ipynb
  duplicate_editions.ipynb
```

Each notebook must have:

1. research question;
2. literature context;
3. corpus hypothesis;
4. data extraction;
5. filtering/uncertainty policy;
6. analysis;
7. validation;
8. interpretation;
9. limitations;
10. reproducibility metadata.

### Do not lead with generic topic modelling

The existing research report correctly prioritizes questions tied to Hittitological
practice: damage sensitivity, ambiguity, parallels, editions, dating, clitics,
prosopography.

---

# Phase 6 — README refactor

Do this **after** core docs and tutorials exist, so links are real.

Target README structure:

```text
logo
one-paragraph summary
status + exact release
quick start
3–4 short research examples
corpus/source summary
documentation links
current limitations
citation/licensing
acknowledgements
```

### Keep the 3–4 examples extremely short

Suggested examples:

1. attestations of a lemma excluding actual lacuna spans;
2. words with unresolved competing morphological analyses;
3. distribution of a lemma/construction by CTH/subcorpus;
4. compare duplicate editions / witness-linked passages once those released layers are
   stable.

Each README example should link to a notebook for the full treatment.

---

# Phase 7 — citation, changelog, release docs

## 7.1 Add `CITATION.cff`

Include:

- TLHdig-TF software/data-conversion citation;
- link/instructions to cite upstream TLHdig separately;
- DOI once TLHdig-TF itself has one.

Do not imply that citing the converter replaces citing TLHdig.

---

## 7.2 Add `CHANGELOG.md`

Record user-visible schema changes:

- node types;
- feature additions/removals;
- semantic changes;
- section-address changes;
- repair changes that affect textual extents;
- distribution/release changes.

Do not list every internal refactor.

---

## 7.3 Freeze releases

Once a release is cited, keep it retrievable.

Release notes should include:

- upstream version;
- TF schema version;
- major node counts;
- exclusions;
- known issues;
- documentation version;
- tested Text-Fabric version;
- checksum/DOI.

---

# Phase 8 — CI and quality gates

Add a documentation job after build/test jobs.

Suggested checks:

```text
pytest
full corpus/build gates
programs/census.py
programs/docs/build_docs.py --check
programs/docs/check_docs.py
execute foundational notebooks
README quick-start smoke test
link checker
```

For notebook execution use `nbclient`, `jupyter nbconvert --execute`, or a small pytest
wrapper.

Research notebooks may be too slow for every commit. Split:

- foundational notebooks: every CI run;
- research notebooks: nightly/release workflow or reduced deterministic sample.

---

# Phase 9 — browser/app documentation

Only begin when the TF app exists and rendering is stable.

Create:

```text
docs/browser.md
```

Document:

- available display formats;
- source-faithful transliteration;
- plain transliteration;
- rich Hittitological rendering;
- line-level cuneiform;
- how damage/restoration is styled;
- feature display;
- search interface;
- links to source/provenance.

Test screenshots manually on light and dark GitHub/browser themes if screenshots are
included.

---

# Phase 10 — domain review

Before declaring documentation stable, request review from at least one Hittitologist for:

- `materlect`;
- `subscr`;
- `mrp` field 4;
- selector letters/groups;
- morphology/POS glosses;
- fragment/witness terminology;
- damage/restoration terminology;
- surface/column/line citation labels;
- crossing-tag repair descriptions.

Record unresolved items as documentation issues rather than silently choosing a meaning.

---

# Proposed implementation order

## P0 — required before a trustworthy public release

1. verify dataset distribution / `use()` path;
2. freeze release metadata;
3. build schema/feature docs generator;
4. write `about.md`;
5. write `model.md`;
6. write `transcription.md`;
7. write `morphology.md`;
8. write `damage.md`;
9. generate `features.md` + individual feature pages;
10. write `query-guide.md`;
11. write `reproducibility.md`;
12. add docs drift CI.

## P1 — required for a mature research corpus

13. `00_start.ipynb`;
14. `01_model_and_text.ipynb`;
15. `02_morphology.ipynb`;
16. `03_damage.ipynb`;
17. `04_search.ipynb`;
18. `05_export.ipynb`;
19. first four research notebooks;
20. README refactor;
21. `CITATION.cff`;
22. `CHANGELOG.md`.

## P2 — after corpus/app stabilization

23. browser/app guide;
24. additional research notebooks;
25. optional MkDocs/GitHub Pages site;
26. optional machine-readable schema export / docs API.

---

# Concrete file tree after P1

```text
TLHdig-TF/
├── README.md
├── CITATION.cff
├── CHANGELOG.md
├── KNOWN-ISSUES.md
├── docs/
│   ├── index.md
│   ├── about.md
│   ├── model.md
│   ├── transcription.md
│   ├── morphology.md
│   ├── damage.md
│   ├── query-guide.md
│   ├── reproducibility.md
│   ├── features.md
│   ├── features/
│   │   ├── ... one page per released feature/edge ...
│   ├── generated/
│   │   ├── schema.md
│   │   └── node-counts.md
│   ├── research-recipes.md
│   ├── TF-CONVERSION-RESEARCH.md
│   ├── TF-CONVERSION-PLAN.md
│   └── applications-deep-research-report.md
├── tutorial/
│   ├── README.md
│   ├── 00_start.ipynb
│   ├── 01_model_and_text.ipynb
│   ├── 02_morphology.ipynb
│   ├── 03_damage.ipynb
│   ├── 04_search.ipynb
│   ├── 05_export.ipynb
│   └── research/
│       ├── damage_aware_concordance.ipynb
│       ├── morphology_ambiguity.ipynb
│       ├── parallel_passages.ipynb
│       └── duplicate_editions.ipynb
└── programs/
    ├── docs/
    │   ├── build_docs.py
    │   └── check_docs.py
    └── tlhdig/
        ├── featuremeta.py
        └── docmeta.py
```

---

# Definition of done

The documentation project is complete for the first mature release when all of the
following are true:

- [ ] a clean user can obtain/load the exact documented TF release;
- [ ] source and TF versions are displayed consistently;
- [ ] every released node type and edge is documented;
- [ ] every released feature appears in the reference;
- [ ] closed vocabularies have code tables;
- [ ] feature pages distinguish confirmed and provisional semantics;
- [ ] morphology ambiguity is explained and executable;
- [ ] damage/point-cluster semantics are explained and executable;
- [ ] cuneiform non-alignment is explicit;
- [ ] duplicate `docid` behaviour is explicit;
- [ ] exclusions/repairs/source fidelity are documented;
- [ ] six foundational notebooks execute successfully;
- [ ] four research notebooks execute on the documented release;
- [ ] README examples execute successfully;
- [ ] generated docs are up to date;
- [ ] CI fails on schema/docs drift;
- [ ] citation/licensing are unambiguous;
- [ ] known issues are linked from all relevant entry points;
- [ ] a Hittitologist has reviewed the unresolved domain semantics or they remain visibly
      marked provisional.

---

# Suggested first implementation PRs

Keep changes reviewable.

### PR 1 — documentation infrastructure

- `docmeta.py`
- `programs/docs/build_docs.py`
- `programs/docs/check_docs.py`
- generated `docs/features.md`
- generated feature pages
- CI drift check

### PR 2 — corpus/model reference

- `docs/index.md`
- `docs/about.md`
- `docs/model.md`
- `docs/transcription.md`
- `docs/reproducibility.md`

### PR 3 — morphology and damage

- `docs/morphology.md`
- `docs/damage.md`
- documentation metadata/status review
- real corpus examples

### PR 4 — introductory tutorials

- `00_start`
- `01_model_and_text`
- `02_morphology`
- `03_damage`
- `04_search`
- `05_export`
- notebook CI

### PR 5 — research recipes + README

- first four research notebooks
- `docs/research-recipes.md`
- README refactor
- `CITATION.cff`
- `CHANGELOG.md`

### PR 6 — TF browser app docs

Only after the app and rich renderers are merged and stable.
