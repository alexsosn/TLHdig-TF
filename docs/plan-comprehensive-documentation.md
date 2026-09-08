# Plan: comprehensive researcher-facing documentation

Issue: #46. Research basis: `docs/research-comprehensive-documentation.md`.

This plan is frozen before any public-manual authoring or documentation-checker
implementation.

## 1. Goal and boundary

Build one coherent researcher-facing manual over the already substantial TLHdig-TF
feature, release, provenance and validation material. The manual must explain the
**released graph and its scholarly semantics**, not narrate development history.

This ticket does **not** own:

- generated per-feature pages or their app wiring (#43);
- browser support behavior (#44);
- acquisition/distribution mechanics (#47/#39);
- new corpus identity/schema semantics;
- a documentation hosting stack merely for visual parity with BHSA.

Those owners are linked from the manual once their contracts are green.

## 2. Public information architecture

Use the smallest page set that still gives each scholarly domain a stable home:

```text
docs/index.md
docs/about.md
docs/data-model.md
docs/features/                  # existing generated reference, owned by #43
docs/text-formats.md
docs/editorial.md
docs/identifiers.md
docs/morphology.md
docs/cuneiform.md
docs/provenance.md
docs/quality.md
docs/querying.md
docs/references.md
docs/browser.md                 # owned by #44
docs/distribution.md            # owned by #47
```

Keep `docs/RELEASE.md` and `docs/AGORA-INTEGRATION.md` as specialized operational
pages. Do not add a separate public `conversion.md`: `provenance.md` gets the concise
conversion/reproducibility narrative and links to `TF-CONVERSION-RESEARCH.md` for the
full technical history.

## 3. Page contracts

### `index.md`

The canonical documentation landing page. It explains audience and routes users to
corpus identity, graph semantics, feature reference, text/editorial conventions,
identifiers, morphology, cuneiform, provenance/quality, querying, browser,
distribution, references and known limitations.

It must not duplicate long explanations from child pages.

### `about.md`

Explain TLHdig as authoritative upstream source, coverage, source/AOxml identity,
source-version versus TF-version distinction, licence, attribution/citation, and the
high-level difference between source-authored and converter-derived information.

### `data-model.md`

Explain the released graph: `sign` slots; structural, analytical, editorial and
relational node families; containment versus edge relations; section levels; and
stable-versus-technical identity concepts. Any inventory of shipped node/edge types is
generated or checked against the current certified artifact.

### `text-formats.md`

Explain plain/transliteration/cuneiform-facing formats, separator preservation and the
app renderer's role. Appearance is not the semantic contract: underlying TF features
remain authoritative.

### `editorial.md`

Explain damage/lacuna/erasure/addition/restoration/correction and rarer editorial
annotations, including what absence means and where source certainty is limited.

### `identifiers.md`

Explain section addressing, `document`/`docgroup`, source paths, duplicate identifiers,
upstream-link fail-closed behavior, manuscript apparatus identities and known remaining
addressing limitations. Do not invent a new identifier scheme.

### `morphology.md`

Explain candidate `analysis` nodes, word→analysis relations, selectors, base/clitic
fields, parse status, ambiguity and the difference between source uncertainty and
converter failure.

### `cuneiform.md`

Explain line-level source cuneiform, alignment-derived sign information, PUA/unrendered/
undecided states, external sign-reference validation and safe interpretation limits.

### `provenance.md`

Explain source acquisition, immutable source identity, repair manifest, conversion,
optional provenance module, release reproducibility and how to trace data back to
source. Header-provenance claims remain conditional on the owning lane landing.

### `quality.md`

Translate executable conservation/certification checks into user-facing guarantees and
limitations. Summarize, do not copy volatile counts. Link `KNOWN-ISSUES.md` and
`docs/RELEASE.md` for current details.

### `querying.md`

Provide small executable Python/Text-Fabric examples for core graph navigation,
features, competing analyses, editorial states, manuscript relations and cuneiform.
Examples use stable scholarly addresses where available and never imply raw TF node
numbers are persistent identifiers.

### `references.md`

Canonical scholarly/source references for TLHdig, AOxml/source documentation,
Text-Fabric and domain-specific interpretation sources used by the manual.

## 4. One source of truth per fact

| Fact | Canonical owner | Manual rule |
|---|---|---|
| feature name/type/short definition | `featuremeta.py` + generated `docs/features/` | link; do not hand-copy inventories |
| shipped schema/counts | certified TF artifact + generated reports | generate/check; avoid copied volatile counts |
| current source/TF version | version/release metadata + app invariants | verify dynamically |
| limitations | executable gates + `KNOWN-ISSUES.md` | summarize and link without softening |
| release mechanics | release policy + `docs/RELEASE.md` | summarize only |
| browser contract | #44 | link only after green |
| distribution contract | #47/#39 | link only after green |
| scholarly interpretation | handwritten domain pages | explain and cite |

No public page may treat a ticket plan or converter implementation detail as a shipped
API contract.

## 5. RED gate: durable documentation contract

Before authoring the manual, add tests/checking code that fails on current `main` for
missing public documentation rather than for unrelated repository state.

Add a focused checker, preferably `programs/check_docs.py`, plus tests in
`programs/tests/test_docs_manual.py`.

### Required RED failures

1. required public pages from §2 are absent;
2. `docs/index.md` does not link every in-scope public domain;
3. README does not route users to the canonical documentation landing page;
4. internal Markdown links in public manual pages do not resolve;
5. generated feature reference is not clean under its existing `--check` contract;
6. schema names claimed in `data-model.md` are not present in the current artifact;
7. public docs may not silently name a TF version different from canonical release
   metadata;
8. executable examples selected for CI fail against the current artifact;
9. browser/distribution links may exist before their owners land, but commands or
   guarantees from those tickets must not be copied into #46 and advertised as shipped.

The initial hosted RED run must show failures caused by missing manual pages/navigation,
with all pre-existing tests green.

## 6. Checker design

Keep checking local and dependency-light.

`check_docs.py` should:

- define the public-manual page set in one place;
- parse relative Markdown links sufficiently for repository docs;
- ignore external HTTP links for ordinary CI rather than making CI network-dependent;
- verify the landing-page navigation set;
- verify README → `docs/index.md` discoverability;
- obtain current TF version from existing canonical Python metadata;
- inspect the committed current artifact for schema claims that the manual marks with a
  machine-checkable convention;
- delegate feature-reference drift to `build_feature_docs.py --check` rather than
  reimplementing it;
- expose a deterministic CLI exit status and concise diagnostics.

Do not introduce MkDocs, Sphinx or a crawler dependency solely for this ticket.

## 7. Authoring order after RED

Implement in dependency-safe waves.

### Wave A — stable current-main semantics

Author:

- `index.md`
- `about.md`
- `data-model.md`
- `text-formats.md`
- `editorial.md`
- `morphology.md`
- `cuneiform.md`
- `quality.md`
- `references.md`

Use only already-certified behavior. Rebase before authoring if #55 has landed so
current release/schema metadata is authoritative.

### Wave B — identity/provenance/query synthesis

Author:

- `identifiers.md`
- `provenance.md`
- `querying.md`

Coordinate examples and claims with current identity/addressing and provenance state.
Unresolved limitations are documented explicitly rather than hidden.

### Wave C — owner links

When available, link:

- `browser.md` from #44;
- `distribution.md` from #47.

#46 does not manufacture substitute browser/distribution behavior to make the manual
look complete.

## 8. Executable examples

Keep a small curated set rather than testing every prose snippet.

Required example classes:

1. load/access the documented artifact using an already-supported local or consumer path;
2. resolve a scholarly section/address and inspect sign/text features;
3. inspect competing morphological analyses;
4. query an editorial/damage state;
5. traverse manuscript/apparatus relations;
6. inspect cuneiform/alignment state safely.

If a clean consumer acquisition path still belongs to #47, CI may use the committed
artifact directly and `querying.md` must say that public installation instructions live
in `distribution.md` once certified.

## 9. Documentation quality rules

- Separate source fact, converter derivation and interpretation.
- State uncertainty explicitly.
- Prefer semantic explanation over code paraphrase.
- Do not freeze large counts that already have generated reports.
- Do not use raw node IDs as scholarly identifiers in examples.
- Do not imply optional provenance is loaded by default.
- Do not describe planned 0.4+/header/browser/distribution behavior as shipped before
  its owning PR lands.
- Keep README concise; it should route, not duplicate the manual.

## 10. GREEN/test gate

Before review:

1. targeted documentation-checker tests;
2. `python programs/check_docs.py`;
3. generated feature docs `--check`;
4. executable documentation examples;
5. full `python -m pytest programs/tests -q`;
6. existing app/release checks relevant to links/version/schema consistency.

Any stale schema claim, broken internal link, undocumented required domain or example
that only works from a warm/local accidental state is a blocker.

## 11. Logically independent adversarial review

Review the exact final PR head from a fresh context and attack:

- copied/stale schema and counts;
- developer notes masquerading as scholarly semantics;
- source fact versus derived/inferred fact confusion;
- hidden limitations or overconfident wording;
- contradictions with `KNOWN-ISSUES.md`, feature metadata or release checks;
- raw-node-number examples presented as persistent citation;
- browser/distribution behavior claimed before owners are green;
- optional provenance accidentally documented as default;
- dead links and circular navigation;
- BHSA cargo-cult structure or unnecessary publishing infrastructure;
- examples relying on uncommitted files, warm caches or unreleased artifacts.

A blocker restarts authoring/test → fresh independent review. Merge only after exact-head
CI and independent review are both green.
