# Plan: comprehensive researcher-facing documentation

Issue: #46
Research basis: `docs/research-comprehensive-documentation.md`.
Status: frozen before public-manual authoring.

Sequence: research → plan → deterministic documentation RED → author/check → full tests → logically independent adversarial review.

## 1. Goal

Create a coherent researcher-facing Markdown manual for the one current pre-alpha TLHdig-TF artifact. Explain shipped graph semantics and limitations; keep development/release history in the existing technical research documents.

## 2. Public page set

The #46-owned pages are:

- `docs/index.md`
- `docs/about.md`
- `docs/data-model.md`
- `docs/text-formats.md`
- `docs/editorial.md`
- `docs/identifiers.md`
- `docs/morphology.md`
- `docs/cuneiform.md`
- `docs/provenance.md`
- `docs/quality.md`
- `docs/querying.md`
- `docs/references.md`

`docs/features/` remains generated and is linked rather than duplicated. Browser and distribution pages remain owned by #44/#47.

## 3. Source-of-truth rules

- Feature names/types/descriptions: current generated feature reference / `featuremeta.py`.
- Current artifact identity: `TF_VERSION`, app configuration and `BUILD-MANIFEST.json`.
- Corpus counts: generated reports; prose should avoid copying volatile totals unless the number is essential and checked.
- Known limitations: `KNOWN-ISSUES.md` plus executable validators/reports.
- Scholarly interpretation: handwritten domain pages with explicit source-vs-derived distinctions.

No page may rely on historical release-v3/v4/v5 certification files.

## 4. RED gate

Before authoring the public pages, add `programs/check_docs.py` and tests. The repository-level check must be RED on current `main` because the manual does not yet exist, while synthetic checker tests are GREEN.

The checker must report at least:

1. missing required manual pages;
2. missing `docs/index.md` navigation to every public domain and generated feature reference;
3. README not routing readers to `docs/index.md`;
4. broken repository-relative Markdown links;
5. explicit current-TF-version claims that disagree with `TF_VERSION`;
6. machine-marked node types or features absent from the current artifact;
7. stale generated feature documentation.

Ordinary CI must not require external HTTP availability.

## 5. Checker conventions

Use lightweight HTML comments where a prose page makes an inventory claim that should be checked mechanically:

```text
<!-- tf-node-types: sign word analysis document -->
<!-- tf-features: sym lemma morph docid -->
```

These markers are validation metadata, not reader-facing tables.

## 6. Authoring order

### Wave A — stable semantics

Author landing/about/data-model/text-formats/editorial/morphology/cuneiform/quality/references from behavior already shipped on current `main`.

### Wave B — identity/provenance/query synthesis

Author identifiers/provenance/querying against current duplicate-document, provenance-module and section-address behavior. Unresolved #16/#57/#58 limitations must be stated as limitations rather than pre-documenting their planned fixes.

### Wave C — links to separately owned user workflows

Link browser/distribution documentation only when #44/#47 provide a shipped contract. #46 does not manufacture substitute commands to make the manual look complete.

## 7. Query examples

Keep a small executable set covering:

- loading the committed current artifact for CI;
- section/text access without treating raw node IDs as stable citations;
- competing morphology analyses;
- editorial/damage querying;
- manuscript/join relations;
- cuneiform/alignment status.

Public clean-install instructions remain #47-owned; CI may load the committed artifact directly.

## 8. Quality constraints

- Separate upstream/source facts, converter-derived values and interpretation.
- State uncertainty and incomplete coverage explicitly.
- Do not imply optional provenance is default-loaded.
- Do not copy large generated feature/count inventories into prose.
- Do not claim fixes from open tickets as shipped.
- Keep README short enough to route users into the manual instead of duplicating it.
- Preserve the #115 pre-alpha policy: historical generated snapshots are not a supported compatibility surface.

## 9. GREEN gate

Before final review require:

- targeted checker tests;
- `python programs/check_docs.py`;
- generated feature-doc check;
- curated executable examples;
- full `python -m pytest programs/tests -q`;
- relevant app/current-build consistency checks.

## 10. Independent adversarial review

Review the exact final head from a fresh logical context and challenge:

- stale/copied schema or counts;
- implementation notes presented as scholarly semantics;
- source-vs-derived ambiguity;
- hidden known limitations;
- contradictions with `KNOWN-ISSUES.md`, current feature metadata or reports;
- raw node IDs presented as stable identifiers;
- browser/distribution behavior advertised before its owning ticket lands;
- optional provenance described as mandatory/default;
- dead/circular links;
- examples that work only with maintainer-local caches or files;
- any resurrection of retired historical certification concepts.

Blocking findings restart fix → test → fresh independent review.
