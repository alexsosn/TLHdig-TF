# Project metadata research

**Status:** research gate complete; implementation must follow `docs/plan-project-metadata.md`.

## Question

What source-path information should become document-level Text-Fabric metadata, and what must remain compatibility or display vocabulary?

## Evidence

### 1. The source path carries a project code

`docs/TF-CONVERSION-RESEARCH.md` §2.1 measured Beta 0.3 and found that the top-level directory suffix in

```text
CTH <cth>_XML_<project>/...
```

encodes the HPM editorial sub-project. The current converter already extracts that suffix into the TF feature `subcorpus`.

The source-path evolution research in `reports/source-path-evolution.md` adds an important boundary: the path is a release-scoped source-record identifier, and the Beta 0.2 layout did not systematically carry the project code in the same top-level form. Project metadata must therefore describe the current source record, not claim cross-release identity.

### 2. `subcorpus` is already public API

Repository search shows `subcorpus` in:

- the README examples and feature-loading snippets;
- `docs/TF-CONVERSION-PLAN.md`, `docs/doc-plan.md`, `docs/doc-research.md`, and application research;
- `app/config.yaml` document display;
- `programs/tlhdig/featuremeta.py`;
- converter tests and the generated TF dataset.

Deleting or silently changing `subcorpus` in the same release would break documented queries and application configuration. A canonical `project` feature can be introduced, but `subcorpus` must remain as a compatibility alias for now and must equal `project` on every document.

### 3. Human-readable project names are not source-path data

Official HPM pages confirm that the codes correspond to editorial projects/corpora, for example:

- TLHdig: https://hatti.adwudlit.uni-mainz.de/TLHdig/
- HFR, *Das Corpus der hethitischen Festrituale*: https://hatti.adwudlit.uni-mainz.de/HFR/
- PTAC, *Hittite Palace-Temple Administrative Corpus*: https://hatti.adwudlit.uni-mainz.de/PTAC/
- the HPM project/corpus index, which lists Hittite Annals, Hittite Divinatory Texts, LuwGramm and other partner corpora: https://hatti.adwudlit.uni-mainz.de/HPM/

These human labels are useful vocabulary, but they are not values literally encoded in the XML or path. They can also be renamed or translated independently of the source record. Repeating them as a `project_name` feature on every document would mix source-derived data with a curated display layer and would cause dataset changes when only the vocabulary changes.

**Decision:** do not emit `project_name` as a document feature in this phase. If a human-readable vocabulary is needed later, keep it once in documentation/app configuration or another controlled-vocabulary layer.

### 4. Intermediate directories are provenance, not project assignments

Beta 0.3 contains technical/nested paths such as:

```text
CTH 670_XML_HFR/CTH 670-0076-0100/11_c.xml
```

Beta 0.2 also contains classification-looking directories such as `CTH 241.I_PTAC`; the Phase 1 research showed that many are empty and cannot safely be promoted to per-record project assignments.

**Decision:** preserve intermediate components losslessly as `source_subdir`, but never infer or override `project` from them.

### 5. Filename stem is useful provenance but not a new identity

`src_file` is already the canonical release-scoped source-record identifier. `source_stem` is only a convenient decomposition of that path. It must never be described as a second persistent ID.

### 6. Malformed path grammar must not silently degrade metadata

The old converter regex returns empty `cth`/`subcorpus` when the top directory does not match. The Phase 1 research includes a real Beta 0.2 example, `CTH 473_XM/...`, showing why silent fallback is dangerous: absent metadata would be indistinguishable from genuinely absent source semantics.

For the Beta 0.3 converter, every source path is expected to satisfy the parser contract. A parser failure is therefore an invariant violation and should fail conversion explicitly rather than generate blank project metadata.

## Resulting model

For each current Beta 0.3 document:

```text
src_file       = CTH 670_XML_HFR/CTH 670-0076-0100/11_c.xml
cth            = 670
project        = HFR
subcorpus      = HFR        # compatibility alias
source_subdir  = CTH 670-0076-0100
source_stem    = 11_c
```

No `project_name` feature is emitted.

## Invariants

1. `src_file` is preserved unchanged from the normalized corpus-relative path already used by manifests.
2. `project == subcorpus` for every document.
3. `cth`, `project`, `source_subdir`, and `source_stem` are derived by the dedicated source-path parser, not duplicate regex logic.
4. Intermediate directories never change `project`.
5. Every converted Beta 0.3 document has a parser-success path.
6. `source_stem` and `source_subdir` are descriptive decomposition, not cross-release identifiers.
