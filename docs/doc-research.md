# Research: documentation architecture for TLHdig-TF

## Purpose

This document answers a practical question: **what documentation should a mature
Text-Fabric corpus provide, and what does TLHdig-TF specifically need before it can be
presented as a research-ready corpus?**

The comparison set is deliberately mixed:

- **ETCBC/BHSA** — the strongest example of a large, long-lived TF corpus with detailed
  feature reference documentation and explicit version/provenance policy.
- **ETCBC/Peshitta** and **ETCBC/SyrNT** — smaller Syriac corpora that cleanly separate
  corpus/about documentation, transcription/model documentation, and start/search
  tutorials.
- **ETCBC/DSS** — a sign-slot Semitic corpus whose feature documentation explains the
  slot model, node types, sections, and the relation between source transcription and TF.
- **Nino-cunei/Old Babylonian**, **Old Assyrian**, and **Uruk** — the closest cuneiform
  precedents. They combine corpus/provenance documentation, source-transcription
  modelling, conversion checks, TF apps, and executable notebooks.
- **Doc4TF** — not a corpus, but directly relevant because it generates and validates
  feature documentation from the actual TF dataset, reducing documentation drift.

The recommendations below are based on the current `main` branch of
`alexsosn/TLHdig-TF` inspected on **2026-08-29**.

---

## 1. What mature TF corpora actually document

### 1.1 Landing page / corpus identity

Mature corpus repositories use the README as an entry point, not as the complete manual.
The recurring information is:

1. what the corpus contains;
2. where the source data came from;
3. what annotation layers exist;
4. how to load it;
5. where the detailed documentation and tutorials live;
6. version/status information;
7. licence and citation;
8. authors/acknowledgements.

Examples:

- BHSA README: corpus identity plus links into the wider BHSA data family.
- Peshitta README: corpus identity, software, tutorial, status, authors, and citation.
- Old Babylonian README: corpus, source (CDLI), Text-Fabric, tutorial, authors, status.
- ETCBC Syriac README: exact text coverage, feature overview, editions, and contributors.

**Implication for TLHdig-TF:** the existing README already contains much of this, but it
currently also carries long explanations of damage semantics, query pitfalls, design
history, and provisional statistics. Those belong in stable topic pages and tutorials.
The README should eventually become a concise map of the resource plus 3–4 compelling,
tested examples.

---

### 1.2 Corpus provenance and source description

The mature examples consistently document the source independently of the TF graph.

Old Babylonian's `docs/about.md`, for example, explains:

- what the source corpus is;
- how it was obtained from CDLI;
- what source format was used;
- what subset of metadata was retained;
- where the transcription specification lives;
- how conversion correctness was checked.

BHSA goes further: its documentation records the pipeline, frozen data versions,
persistent identifiers, and the reproducibility rationale for retaining old versions.

Peshitta separates `about.md` from `transcription.md` and `textfabric.md`.

**Implication for TLHdig-TF:** the documentation must keep four identities separate:

1. **TLHdig Beta 0.3** as the upstream scholarly dataset;
2. the **AOxml source representation**;
3. the **TLHdig-TF converter/ontology version**;
4. a particular **published TF build/release**.

The current conversion plan already correctly distinguishes `sourceVersion = 0.3` from
`tfVersion = 0.1.0`. The user-facing docs should preserve that distinction everywhere.

---

### 1.3 Explicit TF data model

Good TF corpus documentation explains the graph before listing features.

SyrNT's feature documentation introduces:

- the slot type;
- node types above slots;
- `otype` and `oslots`;
- edges;
- section types and section features;
- then the corpus-specific feature table.

DSS similarly explains why `sign` is the slot and lists the object types built above it.

Uruk is especially relevant to TLHdig because it distinguishes the **full ontology**
from the three navigational section levels. TLHdig-TF already adopted that lesson in the
conversion plan.

**TLHdig-TF therefore needs a dedicated `docs/model.md` that answers:**

- Why is `sign` the slot?
- Which node types exist **in the released build**?
- Which are structural, analytical, editorial, or relational?
- Which nodes cover slots and which may be anchored/relational?
- Which edges exist, in what direction, and with what cardinality?
- What are the three TF sections?
- How do `document`, `docgroup`, and manuscript identity differ?
- How do `fragment`/witness relationships differ from containment?
- What is the role of `layout` nodes?
- Which parts of the ambitious conversion plan are actually present in the current
  released version?

A diagram is worth including, but it must be generated from or checked against the
actual graph schema so that planned node types do not silently become documented as
released ones.

---

### 1.4 Feature reference

BHSA is the strongest model here.

It has:

- a feature index grouped by conceptual layer;
- separate pages for individual features;
- the node type on which a feature occurs;
- a short semantic definition;
- tables for coded values;
- distinctions such as `NA` versus `unknown`;
- examples;
- links between related features.

For example, the BHSA `gn` page does not merely say "gender". It explains applicability
and enumerates the codes (`m`, `f`, `NA`, `unknown`) and their different meanings.

That level of detail is essential for TLHdig-TF because names such as `field4_kind`,
`sel_group`, `orphan`, `width`, `prime`, `linetail`, `mrpsel_kind`, and `cudirty` are not
self-explanatory to either a Hittitologist or a TF user.

### Required metadata for every TLHdig-TF feature

Every feature page should state:

| Field | Required content |
|---|---|
| name | exact TF feature name |
| kind | node feature / edge feature / TF warp feature |
| value type | string / int / valued edge / unvalued edge |
| applies to | node type(s) |
| meaning | corpus-level semantic definition |
| upstream source | AOxml element/attribute or derived source |
| transformation | verbatim / normalized / parsed / inferred / derived |
| missing value | what absence means; do not conflate `None`, empty, `XXXlang`, unknown |
| value vocabulary | complete table if closed or quasi-closed |
| frequency | generated count of nodes carrying the feature |
| examples | real corpus values and stable passage addresses |
| query example | minimal Python and/or TF search example |
| caveats | uncertainty, legacy anomalies, lossy/provisional interpretation |
| introduced | TF schema/release version |

For **edge features**, also document:

- direction (`word -> analysis`, `line -> fragment`, etc.);
- target node type;
- one-to-one / one-to-many / many-to-many behaviour;
- whether the edge carries a value;
- what absence means.

---

## 2. Why TLHdig-TF needs more than a conventional feature table

The current repository has an unusually rich `programs/tlhdig/featuremeta.py`.
That file is already described as the source for `@description` metadata and planned
`docs/features.md`. This is a strong basis, but a one-line description is insufficient
for several TLH-specific layers.

### 2.1 Morphological ambiguity is part of the data model

TLHdig does not provide one analysis per word. It may provide many `mrpN` analyses and a
selector that resolves some, but not all, cases.

Documentation must make clear that:

- `analysis` is a node type;
- a word can link to multiple candidate analyses;
- `index` comes from `mrpN` and is not a positional re-numbering;
- the index space may start at 0 and contain gaps;
- `selected` is not guaranteed to exist;
- an absent selection is meaningful uncertainty, not a parser failure;
- `parse_ok=0` is a parsing-status statement, not morphological uncertainty;
- base and clitic analyses are represented separately;
- `field4_kind` is an interpretation of an overloaded upstream field.

This deserves `docs/morphology.md`, not just feature entries.

The page should include the full `mrp` grammar, but user-facing prose should be shorter
than the conversion-research document and should link back to the detailed reverse
engineering.

---

### 2.2 Some semantics are not equally certain

`featuremeta.py` already contains good cautionary wording:

- `sel_clitic` is described as reverse-engineered;
- `sel_group=sg/pl` is not formally documented upstream;
- `materlect_anomalous` distinguishes bare `!`/`?` values;
- `lang_raw` preserves the original `XXXlang`;
- `src_span` has had non-trivial correctness issues;
- several repair cases require philological judgement.

This should become an explicit documentation policy.

Use a small, consistent semantic-status vocabulary:

- **confirmed** — documented upstream or mechanically unambiguous;
- **measured** — established by exhaustive corpus inspection;
- **reverse-engineered** — interpretation fits the corpus but lacks upstream
  documentation;
- **provisional** — useful interpretation with unresolved counterexamples/questions;
- **raw-only authoritative** — derived interpretation must not be treated as canonical.

Do not make users infer the confidence level from prose.

This status should appear on feature pages and in a compact table in
`docs/morphology.md` / `docs/transcription.md`.

---

### 2.3 Damage/editorial ranges need their own conceptual documentation

TLHdig-TF's damage model is one of the main reasons to use the corpus, and one of the
easiest parts to query incorrectly.

The docs must explain separately:

- `cluster` nodes;
- cluster families (`del`, `laes`, `ras`, `add`);
- spans versus point breaks;
- `width=0`;
- why point breaks may be anchored to a sign but must not be counted as damaging it;
- induced sign flags (`missing`, `laes`, `ras`, `add`);
- `orphan=open/close`;
- synthesized start/end bounds;
- `from_open_marker` / `from_close_marker`;
- `start_offset` / `end_offset`;
- `startsAt` / `endsAt`;
- cross-line ranges;
- nested/re-open behaviour;
- the difference between physical damage, editor-supplied restoration, erasure,
  addition, and correction marks.

A user should be able to answer:

> "How do I retrieve securely preserved attestations of lemma X?"

without reading converter code or `KNOWN-ISSUES.md`.

This should live in `docs/damage.md` plus an executable `tutorial/03_damage.ipynb`.

---

### 2.4 Cuneiform representation has a hard boundary

The docs must state prominently:

- `cu` is **line-level Unicode cuneiform**;
- it is not sign-aligned;
- `cu_broken` and `cu_pua` describe properties of that line-level string;
- sign-level transliteration and line-level cuneiform should not be silently joined by
  position;
- the corpus does not create a fabricated sign-level Unicode alignment.

This belongs both in `docs/transcription.md` and in the feature pages for `cu`,
`cu_broken`, and `cu_pua`.

---

### 2.5 Source fidelity and repair provenance are research-facing concerns

Most TF corpora can hide conversion mechanics from ordinary users. TLHdig-TF should not
fully do so because:

- 53 source files are excluded from the current build;
- XML repairs exist;
- a subset of crossing-tag repairs make structural choices;
- `src_span` is intended to support source recovery;
- the build has explicit source-conservation and census invariants.

The current `KNOWN-ISSUES.md`, `reports/census.md`, and
`reports/crossing-tag-review.md` are valuable, but they need a user-facing synthesis in
`docs/provenance.md` or `docs/reproducibility.md`.

The detailed repair list should remain a report. The docs should explain what kinds of
repairs exist, how they are pinned, what is mechanical, what requires philological
review, and what claims a researcher can safely make.

---

## 3. Current TLHdig-TF documentation audit

### Strong material already present

#### `README.md`

Already provides:

- corpus purpose;
- status warning;
- quick `tf.app.use()` example;
- source corpus description;
- research motivation;
- several real query ideas;
- limits of the conversion;
- repository layout;
- licensing/citation;
- high-level model summary.

It should be **shortened later**, not replaced.

#### `docs/TF-CONVERSION-RESEARCH.md`

This is valuable developer/design documentation and should remain.
It contains measured corpus facts, AOxml reverse engineering, morphology grammar,
line-reference grammar, markup inventory, and malformed-file analysis.

Do not turn it into the user manual. Link to it from relevant reference pages.

#### `docs/TF-CONVERSION-PLAN.md`

Also valuable and should remain as design history/specification.
However, it describes target architecture and therefore must never be the only place
users learn which nodes/features exist in a released build.

#### `KNOWN-ISSUES.md`

Good practice. It is unusually concrete about which guarantees have failed, why, and
what is fixed. Keep it.

For documentation, add a short "Current limitations" summary elsewhere and link here.

#### `reports/census.md`

Exactly the right approach for volatile counts: generated from the loaded dataset and
marked "Do not hand-edit."

This pattern should be extended to feature documentation.

#### `programs/tlhdig/featuremeta.py`

This should become the semantic seed for generated feature pages.
It already avoids overclaiming uncertain upstream semantics.

#### `docs/applications-deep-research-report.md`

This is a strong source for tutorial/cookbook design.
It should be converted from one long research report into executable notebooks and a
short `tutorial/README.md` index rather than left as the only practical guide.

---

### Gaps

#### P0: no released-build schema manual

There is no concise page that says, for the **current published build**:

- these are the node types;
- these are their containment/edge relationships;
- these are the sections;
- these text formats exist;
- these features occur on each type.

The conversion plan is not a substitute because it contains planned as well as
implemented architecture.

#### P0: no complete feature/value reference

A mature corpus with this many features needs more than feature names in the README.
Closed vocabularies and overloaded fields especially need value tables.

#### P0: no end-user morphology manual

The `mrp` model is central to real research and too complex to infer from feature names.

#### P0: no end-user damage manual

The README contains pieces of the explanation, but the semantics need one canonical page
with tested queries.

#### P0: distribution/load instructions need release-state verification

During this audit, GitHub's Contents API returned **404 for `tf/` and `tf/0.1.0`**, and
the repository's releases endpoint returned an empty list, while the README says a
dataset exists at `tf/0.1.0/` and shows `use("alexsosn/TLHdig-TF")`.

Before documentation promises that command as the primary installation path, CI should
run it against the same distribution mechanism users will receive. If the TF data are
intentionally not committed to `main`, the docs need to point to the actual release
asset, Zenodo record, or build procedure.

This is a documentation/release integration issue, not a request to change the corpus
model.

#### P1: no progressive tutorial path

Mature corpora normally have at least `start` and `search` notebooks.
The cuneiform examples often add display/export/specialized notebooks.

TLHdig-TF needs a short progression before the advanced research notebooks.

#### P1: no stable "about/provenance/citation" page

The README has this information, but it should be reusable from releases, notebooks,
and future documentation without requiring users to cite a moving README.

#### P1: no documentation drift gate

The repository already learned the cost of hand-copied counts.
Feature docs should be generated/validated from the actual dataset in the same spirit as
`census.py`.

#### P2: no browser/app manual yet

The conversion plan anticipates an `app/` with rich transliteration/cuneiform rendering.
Document it after the app exists and its views are stable.

---

## 4. Recommended documentation information architecture

A good target tree is:

```text
README.md

docs/
  index.md
  about.md
  model.md
  transcription.md
  morphology.md
  damage.md
  query-guide.md
  reproducibility.md
  features.md                 # generated index
  features/                   # generated/semigenerated individual pages
    sign/
    word/
    analysis/
    line/
    document/
    edges/
  research-recipes.md         # short index into notebooks

tutorial/
  README.md
  00_start.ipynb
  01_model_and_text.ipynb
  02_morphology.ipynb
  03_damage.ipynb
  04_search.ipynb
  05_export.ipynb
  research/
    damage_aware_concordance.ipynb
    morphology_ambiguity.ipynb
    parallel_passages.ipynb
    duplicate_editions.ipynb

reports/
  census.md
  crossing-tag-review.md
  ...generated validation reports...

KNOWN-ISSUES.md
CITATION.cff
CHANGELOG.md
```

Do **not** require a documentation framework in the first implementation.
Plain Markdown rendered by GitHub plus Jupyter notebooks matches mature TF practice and
keeps maintenance simple. A MkDocs/GitHub Pages layer can be added later without
changing the content model.

---

## 5. What each page should contain

### `docs/index.md`

A one-screen navigation page for four audiences:

- Hittitologist who wants to query the corpus;
- TF/Python user;
- corpus linguist/NLP user;
- converter maintainer.

Include links to:

- start tutorial;
- corpus/provenance;
- model;
- features;
- morphology;
- damage;
- search guide;
- research notebooks;
- known issues;
- conversion research/plan.

---

### `docs/about.md`

Canonical corpus identity:

- TLHdig upstream title, creators, institution, DOI, version, release date;
- coverage: documents/subcorpora/CTH range, but volatile counts linked to generated
  census rather than copied;
- what TLHdig-TF adds and does not add;
- source licence versus converter/docs licence;
- citation instructions for upstream data and, when appropriate, TLHdig-TF release;
- acknowledgements;
- source hash / identity pointer;
- TF schema version and release version;
- link to known exclusions.

---

### `docs/model.md`

Canonical graph model:

- sign slots;
- current node types, grouped by role;
- section levels and section features;
- structure hierarchy;
- node/edge diagram;
- containment versus relational edges;
- text formats;
- stable-address examples;
- table with node type, purpose, typical parent/context, count link.

Include a large warning box:
**"This page describes the released build; the conversion plan may describe future
nodes/features."**

---

### `docs/transcription.md`

User-facing AOxml/TF mapping:

- sign tokenization rule;
- `srcxml`, `sym`, `after`;
- Sumerogram/Akkadogram/determinative/numeral flags;
- corrections, `subscr`, `materlect`, `surplus`;
- line numbering (`lnr`, `lnno`, `ln`, `prime`, `linetail`);
- surface/column/fragment labels;
- language handling;
- cuneiform `cu` and its non-alignment;
- source byte spans and repair provenance;
- text formats and what each is for.

Link to the exhaustive conversion research for grammar/inventory details.

---

### `docs/morphology.md`

- how `mrpN` becomes `analysis` nodes;
- candidate versus selected analysis;
- sparse and zero-based `mrp` indices;
- selector syntax and selector statuses;
- base/clitic split;
- lemma/gloss/morph/stemclass/POS fields;
- full field-4 interpretation and confidence status;
- `parse_ok`;
- absence/unanalysed words;
- how to obtain "all analyses", "selected analysis", and "only unambiguous words";
- value tables for POS and any stable morphological code systems;
- examples from real passages;
- known unresolved upstream questions.

---

### `docs/damage.md`

- editorial marker families;
- cluster geometry;
- points versus spans;
- induced sign flags;
- orphan/synthesized bounds;
- mid-sign offsets;
- cross-line behaviour;
- zero-width query trap;
- recommended definitions of "secure", "damaged", "restored", "editorially uncertain";
- tested query templates;
- limitations and validation references.

---

### `docs/query-guide.md`

A corpus-specific guide rather than a generic TF manual.

Sections:

1. loading the exact version;
2. passage addressing;
3. retrieving text;
4. walking sign -> word -> line -> document;
5. accessing candidate analyses;
6. using edges;
7. TF Search templates;
8. damage-aware search;
9. querying CTH/subcorpus/language;
10. fragments/witnesses/editions;
11. export to pandas/CSV/Parquet;
12. performance notes for an ~8M-node corpus;
13. common mistakes.

Explicit common mistakes should include:

- looking for `lemma` on `word` instead of `analysis`;
- assuming every word has a selected analysis;
- treating `width=0` cluster anchors as damaged signs;
- treating `cu` as sign-aligned;
- treating `docid` as globally unique;
- assuming absent features and empty strings are equivalent;
- citing raw node numbers as persistent identifiers.

---

### `docs/reproducibility.md`

- source release and hashes;
- converter/schema version;
- deterministic build command;
- exclusion ledger;
- repair manifest;
- validation gates;
- current census;
- known lossy/provisional cases;
- crossing-tag review status;
- how releases are frozen;
- how to reproduce an older analysis;
- policy for schema-breaking versus data-only changes.

---

### `docs/features.md` + `docs/features/**`

Generated or semi-generated.

`features.md` should provide:

- node-type groups;
- feature name;
- kind;
- short description;
- value type;
- coverage count;
- link to individual page.

Individual pages should combine:

1. generated facts from the actual TF dataset;
2. semantic description from `featuremeta.py`;
3. optional hand-written extended note for complex features.

Generated blocks should be clearly delimited so manual prose is not overwritten.

---

## 6. Documentation generation and validation

### 6.1 Do not make Markdown the source of truth for schema facts

Use:

- actual TF feature files / loaded API for existence, type, value ranges, counts;
- `featuremeta.py` for short semantic descriptions;
- a small metadata extension for documentation-only fields such as confidence status,
  upstream AOxml path, related features, and long-form notes;
- `census.py` for corpus-wide node/range counts;
- `KNOWN-ISSUES.md` for current defect status.

### 6.2 Suggested metadata extension

Either extend `featuremeta.py` or add `programs/tlhdig/docmeta.py`:

```python
FEATURE_DOC = {
    "sel_group": {
        "status": "provisional",
        "source": "w/@mrp0sel",
        "applies_to": ["word"],
        "related": ["mrpsel", "sel_base", "sel_clitic"],
        "note": "all is observed; sg/pl semantics are not formally documented upstream",
    },
}
```

Keep `DESCRIPTIONS` backward-compatible with TF `@description` generation.

### 6.3 Generator

Add something like:

```text
programs/docs/build_docs.py
programs/docs/check_docs.py
```

The generator should:

- load the published TF build;
- enumerate all node and edge features;
- obtain feature metadata;
- count coverage;
- enumerate closed/low-cardinality vocabularies;
- sample stable examples;
- generate `docs/features.md`;
- generate per-feature pages;
- generate a schema table for `docs/model.md` or an include file.

### 6.4 Drift checks

CI should fail if:

- a TF feature exists without a description;
- a described feature does not exist in the target build, unless marked planned/retired;
- an edge's observed source/target node types disagree with its documentation;
- a documented closed vocabulary omits observed values;
- a generated docs file is out of date;
- tutorial notebooks fail to execute on the release;
- README quick-start fails;
- internal documentation links are broken.

Doc4TF is useful precedent: it generates feature pages from the actual dataset and also
offers a version-delta tool. TLHdig-TF can borrow the principle without adopting its
notebook wholesale.

---

## 7. Tutorial strategy

Mature TF repositories nearly always provide a basic start/search path.
Nino-cunei goes further with display, export, similarity, and cookbook notebooks.

TLHdig-TF should have two tiers.

### Tier A: learn the corpus

#### `00_start.ipynb`

- install/load;
- pin version;
- show corpus metadata and generated census;
- retrieve one tablet by section;
- display transliteration;
- inspect a word and its signs.

#### `01_model_and_text.ipynb`

- slots/nodes;
- sections;
- `L.u` / `L.d`;
- text formats;
- structure and line-level cuneiform;
- edges.

#### `02_morphology.ipynb`

- candidate analyses;
- selected analysis;
- ambiguous/unselected cases;
- POS/morph queries;
- clitics.

#### `03_damage.ipynb`

- clusters;
- spans/points;
- damage flags;
- safe filtering;
- cross-line example.

#### `04_search.ipynb`

- TF Search syntax;
- morphology + structure;
- morphology + damage;
- subcorpus/CTH filtering;
- relational edges.

#### `05_export.ipynb`

- dataframe extraction;
- selected/all analyses;
- stable passage identifiers;
- CSV/Parquet;
- recording corpus version for reproducibility.

### Tier B: research recipes

Build these from the existing applications research report, with real literature-grounded
questions:

1. damage-aware concordance/collocation;
2. morphological ambiguity and contextual disambiguation;
3. parallel-passage / text-reuse discovery;
4. duplicate-edition alignment;
5. later: dating/dialect features, clitic syntax, prosopography, stylometry.

The first four are enough for the initial documentation release.

Each research notebook should contain:

- a real research question;
- relevant literature;
- exact corpus prerequisites;
- extraction/query code;
- validation strategy;
- interpretation limits;
- expected runtime/memory;
- stable output tables or plots;
- a section on how the TF representation improves on direct AOxml processing.

---

## 8. README after the documentation exists

The README should eventually contain only:

1. logo + one-paragraph description;
2. status/release warning;
3. quick start;
4. 3–4 short research examples;
5. corpus coverage summary with links to generated census;
6. documentation map;
7. licensing/citation;
8. acknowledgements.

Move long discussions of:

- bracket semantics;
- selector internals;
- zero-width clusters;
- detailed model design;
- historical failed counts;
- converter architecture

to their canonical docs pages.

The README can keep short warnings, but every warning should link to the authoritative
page.

---

## 9. Release/version documentation

BHSA's frozen-version policy is worth adopting conceptually even if TLHdig-TF remains
much smaller as a project.

A published result should be able to say:

```text
TLHdig upstream: 0.3
TLHdig-TF schema/build: 0.1.0
release artifact: <DOI/tag/commit>
Text-Fabric: <tested version>
```

For a research corpus, old published versions should remain retrievable once cited.

Recommended semantic policy:

- patch: converter bug fix with unchanged public schema where practical;
- minor: additive features/node types or compatible semantic improvements;
- major: breaking ontology/feature meaning or section-address changes.

Document exceptions explicitly; do not pretend strict SemVer can capture upstream corpus
revisions automatically.

---

## 10. Documentation-specific content that must be reviewed by a Hittitologist

Before calling the docs authoritative, obtain domain review for:

- `materlect`;
- `subscr`;
- `mrp` field 4 interpretation;
- `mrp0sel` lower-/upper-case split and `all/sg/pl`;
- POS/morphology code glosses;
- language flags and quotation semantics;
- damaged/restored terminology;
- the 74 crossing-tag structural repairs;
- interpretation of fragment/witness join metadata;
- line/surface/column terminology and citation examples.

The docs may still be published before every question is settled, but unresolved items
must be labelled with the semantic-status scheme above and retain raw values.

---

## 11. Acceptance standard for "mature documentation"

TLHdig-TF should be considered well documented when a new researcher can, without
opening converter source code:

1. identify the exact source and TF release they are using;
2. understand the slot/node/edge model;
3. find every feature and every closed-vocabulary code;
4. distinguish raw source values from derived interpretations;
5. retrieve a tablet/line by a scholarly address;
6. obtain all and selected morphological analyses;
7. correctly filter damage/restoration;
8. understand what cuneiform is and is not aligned to;
9. export a reproducible dataframe;
10. find known exclusions/repairs/limitations;
11. run at least four research-grade example notebooks;
12. cite the upstream corpus and TLHdig-TF correctly.

The documentation should also pass an automated schema/docs drift check on every release.

---

## 12. Sources reviewed

### TLHdig-TF

- Repository: https://github.com/alexsosn/TLHdig-TF
- README:
  https://github.com/alexsosn/TLHdig-TF/blob/main/README.md
- Conversion research:
  https://github.com/alexsosn/TLHdig-TF/blob/main/docs/TF-CONVERSION-RESEARCH.md
- Conversion plan:
  https://github.com/alexsosn/TLHdig-TF/blob/main/docs/TF-CONVERSION-PLAN.md
- Feature metadata:
  https://github.com/alexsosn/TLHdig-TF/blob/main/programs/tlhdig/featuremeta.py
- Known issues:
  https://github.com/alexsosn/TLHdig-TF/blob/main/KNOWN-ISSUES.md
- Census:
  https://github.com/alexsosn/TLHdig-TF/blob/main/reports/census.md
- Applications research:
  https://github.com/alexsosn/TLHdig-TF/blob/main/docs/applications-deep-research-report.md

### BHSA / ETCBC

- BHSA repository:
  https://github.com/ETCBC/bhsa
- BHSA documentation index:
  https://github.com/ETCBC/bhsa/blob/master/docs/index.md
- BHSA feature index:
  https://github.com/ETCBC/bhsa/blob/master/docs/features/0_home.md
- Example detailed feature page (`gn`):
  https://github.com/ETCBC/bhsa/blob/master/docs/features/gn.md
- ETCBC Syriac corpus:
  https://github.com/ETCBC/syriac
- Peshitta:
  https://github.com/ETCBC/peshitta
- Peshitta docs:
  https://github.com/ETCBC/peshitta/tree/master/docs
- SyrNT transcription/feature documentation:
  https://github.com/ETCBC/syrnt/blob/master/docs/transcription.md
- DSS feature documentation:
  https://github.com/ETCBC/dss/blob/master/docs/feature_documentation.md

### Cuneiform TF corpora

- Old Babylonian:
  https://github.com/Nino-cunei/oldbabylonian
- Old Babylonian about/provenance:
  https://github.com/Nino-cunei/oldbabylonian/blob/master/docs/about.md
- Old Babylonian tutorials:
  https://github.com/Nino-cunei/oldbabylonian/tree/master/tutorial
- Old Assyrian:
  https://github.com/Nino-cunei/oldassyrian
- Uruk:
  https://github.com/Nino-cunei/uruk

### Documentation tooling

- Doc4TF:
  https://github.com/tonyjurg/Doc4TF
