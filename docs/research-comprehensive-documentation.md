# Research: comprehensive researcher-facing documentation

Issue: #46

Baseline inspected: `main` at `967c71ce1bde901d580b422ea396bceac9f71422` (2026-09-08).
Reference corpus inspected: ETCBC/BHSA `master` documentation tree.

This is a delta audit, not a replacement for the earlier broad survey in
`docs/doc-research.md`. That survey was written against the 2026-08-29 repository and
correctly identified the need for corpus identity, provenance, graph-model, feature,
morphology, cuneiform, querying and tutorial documentation. Several prerequisites have
since landed, so #46 should now turn the accumulated developer material into one coherent
researcher-facing manual rather than restart the same research.

## 1. What changed since the earlier documentation survey

The August survey predates major documentation-enabling work now present on `main`:

- `docs/features/` is a generated, app-facing per-feature reference with a landing page;
- `app/config.yaml` points Text-Fabric feature help at that generated reference;
- the app now has an upstream TLHdig source-link adapter with ambiguity-safe behavior;
- the app now has a corpus-specific Hittitological renderer for sign-local writing,
  preservation and editorial states;
- release/version consistency, source identity, provenance splitting, manuscript graph,
  cuneiform alignment and other correctness contracts are executable rather than merely
  planned;
- `KNOWN-ISSUES.md`, `docs/RELEASE.md`, `docs/AGORA-INTEGRATION.md`, conversion research,
  architecture notes and many ticket-specific research/plan documents contain substantial
  factual material.

Therefore the primary documentation problem has changed from **missing information** to
**fragmented information with no stable public information architecture**.

## 2. Current documentation inventory and classification

### Public/useful material already present

- `README.md`: project entry point, status, basic use and important limitations.
- `docs/features/`: generated feature reference; this should remain generated and owned
  by #43 rather than rewritten by #46.
- `docs/RELEASE.md`: release/certification mechanics and version policy.
- `docs/AGORA-INTEGRATION.md`: automation/materializer integration contract.
- `KNOWN-ISSUES.md`: current correctness limitations.
- `CITATION.cff`, `LICENSE`, source attribution files: citation/licensing/provenance facts.

### Authoritative developer/research material that is not a public manual

- `docs/TF-CONVERSION-RESEARCH.md` / `docs/TF-CONVERSION-PLAN.md`;
- `docs/doc-research.md` / `docs/doc-plan.md`;
- ticket-specific `docs/research-*.md` and `docs/plan-*.md` files;
- architecture documents;
- generated validation reports and checker source.

These are valuable evidence and should be linked where useful, but they expose design
history, abandoned alternatives, implementation details and moving counts. They should
not be the path a corpus user must follow to understand the data.

### Missing public/manual layer on current `main`

The top-level `docs/` tree still lacks a coherent set of canonical researcher pages such
as:

- a documentation landing/index page;
- corpus/about/source scope;
- released TF graph/data model;
- text formats and Hittitological rendering semantics;
- document/section/manuscript identity and citation semantics;
- morphology and competing-analysis model;
- cuneiform/alignment model and its limits;
- editorial/damage/restoration semantics;
- provenance/conversion/reproducibility overview;
- query/programmatic-use guide;
- supported browser guide (owned by #44);
- supported distribution/install guide (owned by #47);
- scholarly/source references.

In other words, the feature dictionary is now substantially solved, but the **relations
between features and the scholarly interpretation of the graph** are still scattered.

## 3. BHSA comparison: pattern to copy, parts not to cargo-cult

The current BHSA documentation tree has a real `docs/index.md`, a `features/` reference,
`articles/`, `references.md`, `news.md`, and domain pages such as `cantillation.md` and
`wordgrammar.md`, plus images/assets. The important pattern is layered documentation:

1. landing/navigation;
2. generated or systematic feature reference;
3. domain-semantic pages explaining how groups of features form a scholarly model;
4. references and provenance;
5. deeper articles/history where useful.

TLHdig-TF should copy that **separation of concerns**, not BHSA-specific subjects,
publishing infrastructure, or SHEBANQ assumptions. In particular:

- no need for a `news.md` merely because BHSA has one;
- no need for an `articles/` hierarchy until TLHdig-TF has genuinely article-length
  material worth maintaining;
- no need to add MkDocs/GitHub Pages solely for visual parity;
- no BHSA lexeme/web assumptions should enter the TLH graph model;
- browser documentation must reflect TLHdig-TF's actual resource/distribution behavior,
  not BHSA installation text.

## 4. Information ownership: one source of truth per fact

A comprehensive manual will become stale unless facts have explicit owners.

| Fact class | Canonical owner | Public docs behavior |
|---|---|---|
| feature name/type/short description | `programs/tlhdig/featuremeta.py` + generated feature docs | link/embed generated reference; do not hand-copy inventories |
| shipped node/edge/feature set and counts | certified TF artifact / generated reports | generate or verify; avoid copied volatile counts |
| source and TF version | version/release metadata + app config invariants | render/verify consistently |
| known losses/limitations | executable checks + `KNOWN-ISSUES.md` | summarize and link, never silently soften |
| conversion mechanics | converter + conversion research | public overview; link detailed research for reproducibility |
| scholarly interpretation | handwritten domain pages | explain semantics and uncertainty, cite source evidence |
| browser behavior | #44 | link from manual |
| acquisition/distribution | #47/#39 | link from manual; do not duplicate commands until certified |
| release/certification | release policy + `docs/RELEASE.md` | public reproducibility summary, detailed operational link |

The manual should not duplicate release-sensitive commands or counts across many pages.

## 5. Proposed public documentation domains from the evidence

This research supports the following domain split for the planning gate.

### Corpus identity / provenance

Explain TLHdig as the authoritative source, the upstream AOxml input, the relationship
between source version and TF build version, licensing/citation, exclusions/repairs, and
what is conversion-derived rather than source-authored.

### Data model

Explain why `sign` is the slot; structural vs analytical/editorial/relational node types;
containment versus edges; the roles of `document`, `docgroup`, `fragment`, `joinstmt`,
`analysis`, `lex`, `cluster`, `layout`; section types; and which identities are safe for
citation. This page must be generated/verified against the released schema.

### Text and editorial semantics

Explain transliteration formats, separator preservation, line-level cuneiform, sign-local
Sumerogram/Akkadogram/determinative/numeral display, damage/lacuna/erasure/addition,
corrections and rarer editorial annotations. CSS appearance is not the semantic
contract; underlying features are.

### Morphology

Explain candidate `analysis` nodes, word→analysis edges, selector behavior, base/clitic
fields, parse status, gloss/lemma/stem class, and the distinction between source
ambiguity and converter parse failure. Ticket research can provide evidence, but the
public page should not read like parser source commentary.

### Cuneiform

Explain line-level `cu`, alignment-derived sign data, PUA/unrendered/undecided states,
external sign-reference validation and what users may safely infer. Do not imply a
one-to-one Unicode rendering where the alignment/checkers explicitly preserve
uncertainty.

### Identifiers and citation

Explain the three TF section levels, duplicate `docid` reality, `docgroup`, source paths,
TLHdig upstream-link fail-closed behavior, manuscript apparatus identity, and any
remaining non-addressable cases. This must coordinate with the identity tickets rather
than invent a new ID scheme in docs.

### Querying / API

Show small tested examples for selective `Fabric` loads, feature access, TF search,
competing analyses, damage/editorial queries, manuscript graph traversal and cuneiform.
Examples should use stable scholarly addresses rather than treating TF node numbers as
persistent identifiers.

## 6. Generated vs handwritten boundary

Generated/verified:

- feature index/pages;
- schema inventory;
- version/release identity;
- counts/cardinalities where shown;
- example preconditions that depend on shipped data;
- internal-link and documented-file coverage checks.

Handwritten:

- scholarly explanation of what the graph represents;
- distinctions between source fact, conversion derivation and inference;
- interpretation cautions;
- provenance narrative;
- user workflows and conceptual examples.

Do not generate paragraphs that merely paraphrase Python. Conversely, do not hand-copy
large tables the corpus can generate reliably.

## 7. Documentation topology recommendation to evaluate in the plan

A coherent minimal public layer can be built around:

```text
docs/index.md
docs/about.md
docs/data-model.md
docs/features/                  # existing generated reference
docs/text-formats.md
docs/identifiers.md
docs/morphology.md
docs/cuneiform.md
docs/editorial.md
docs/provenance.md
docs/conversion.md
docs/quality.md
docs/querying.md
docs/browser.md                 # #44
docs/distribution.md            # #47
docs/references.md
```

`docs/RELEASE.md` and `docs/AGORA-INTEGRATION.md` may remain specialized operational
pages rather than being renamed for symmetry.

The plan should decide whether `conversion.md` and `provenance.md`, or `quality.md` and
`provenance.md`, have enough independent user-facing content to justify separate pages;
do not create empty hierarchy merely to match this sketch.

## 8. Required RED/checking strategy before authoring

Before public pages are claimed complete, executable checks should fail for the current
missing contract and then protect it. Candidate checks:

1. documentation landing page exists and links every required public domain;
2. every shipped non-warp feature has exactly one generated feature page and the
   generator is clean under `--check`;
3. documented node/edge types are a subset/equal to the certified artifact schema;
4. all internal Markdown links resolve;
5. README points to the canonical docs landing page rather than duplicating the manual;
6. code snippets selected for CI actually execute against the documented release;
7. version strings in public docs cannot silently disagree with release/app metadata;
8. no documentation page advertises browser/distribution behavior whose owning smoke
   contract is not green;
9. known limitations named as user-relevant in `KNOWN-ISSUES.md` have a discoverable
   path from the manual rather than being hidden in developer notes.

The plan must choose a small durable checker instead of a broad external documentation
stack unless the latter has a demonstrated maintenance benefit.

## 9. Dependencies / sequencing

Work that can proceed immediately after planning:

- landing/about/data-model structure;
- semantic pages whose contracts are already certified on current main;
- references/provenance/conversion synthesis;
- documentation link/schema/drift checks.

Work that must remain coordinated:

- feature page generation/details → #43 contract;
- browser commands/resources → #44;
- distribution/acquisition/version selection → #47/#39;
- document identity examples → identity/addressing tickets;
- statements about 0.4.0 sign language → only after the active immutable release lands;
- header provenance semantics → only after the active provenance lane lands.

Documentation may describe an unresolved limitation explicitly, but must not describe
planned data as shipped data.

## 10. Research conclusion

The repository no longer needs another large documentation brainstorm. It needs a
**public synthesis layer with executable drift checks** over information that already
exists in feature metadata, release checks, research documents and the corpus itself.

BHSA remains a useful maturity benchmark because it separates navigation, feature
reference, domain semantics and references. TLHdig-TF should achieve comparable
*coverage and discoverability* while keeping its current strengths: generated feature
reference, explicit uncertainty, executable conservation checks, authoritative upstream
links and a thin standard Text-Fabric app.
