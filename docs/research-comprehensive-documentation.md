# Research: comprehensive researcher-facing documentation

Issue: #46
Baseline: `main` at `68e2b7f80ed9ded8a42fd22f36819311e94173b3` after #115/#117 policy simplification.

## Question

What documentation is still missing for a first external researcher, given that TLHdig-TF is an explicitly pre-alpha corpus with one current generated artifact and substantial existing technical documentation?

## Current evidence

The repository already has useful documentation, but it is fragmented by purpose:

- `README.md` gives status, major limitations, a deterministic local `Fabric` quick start, and representative query examples.
- `docs/features/` is generated from shipped feature metadata and is the right source for per-feature facts.
- `KNOWN-ISSUES.md` and generated reports expose concrete source/conversion limitations.
- `docs/AGORA-INTEGRATION.md` explains consumer-specific loading behavior.
- `docs/RELEASE.md` now describes the current-build validation/manifest model rather than predecessor certification.
- ticket-specific research/plan documents contain detailed engineering evidence, but they are not a usable researcher manual.

The missing layer is a stable synthesis organized around scholarly questions: what the corpus contains, how the graph is modelled, what identifiers mean, how morphology/editorial states/cuneiform are represented, what provenance and uncertainty guarantees exist, and how to query those structures without reading implementation history.

## Policy constraints from #115/#117

Documentation must describe the current pre-alpha contract:

- one current generated TF artifact (`TF_VERSION`, currently `0.4.0`);
- one optional matching provenance module;
- no promise that historical pre-1.0 generated snapshots remain on `main`;
- correctness derives from pinned source identity, converter code, current-build validation and `BUILD-MANIFEST.json`, not release-v3/v4/v5 certificate history;
- current limitations must remain visible rather than being softened by presentation.

Historical research documents may retain dated references to older TF versions because they are evidence, not current user instructions.

## Information-architecture finding

A small Markdown manual is sufficient. No MkDocs/Sphinx/site framework is justified at this stage. The public layer should have stable homes for:

- corpus identity/status (`about.md`);
- graph/section model (`data-model.md`);
- text formats (`text-formats.md`);
- editorial/damage semantics (`editorial.md`);
- identifiers and duplicate-document caveats (`identifiers.md`);
- morphology/ambiguity (`morphology.md`);
- cuneiform/alignment confidence (`cuneiform.md`);
- source/provenance/rebuild traceability (`provenance.md`);
- validation and known limitations (`quality.md`);
- executable query patterns (`querying.md`);
- scholarly/source references (`references.md`);
- a landing page (`index.md`).

Browser and clean-distribution instructions remain owned by #44/#47; #46 should link them when available rather than inventing parallel contracts.

## Drift risks that should be executable

The manual will become misleading if it hand-maintains volatile inventories. The durable checks should therefore verify:

1. required public pages exist;
2. `docs/index.md` links the public domains and generated feature reference;
3. README routes readers to the manual;
4. repository-relative links in public manual pages resolve;
5. explicit "current TF version" claims match `TF_VERSION`;
6. machine-marked node/feature claims exist in the current committed artifact;
7. generated feature documentation remains clean under its existing check command.

External URLs should not make ordinary CI network-dependent.

## Scope boundaries

- Do not change converter/schema/artifact semantics in #46.
- Do not document planned behavior as shipped.
- Do not make optional provenance appear to be loaded by default.
- Do not use raw TF node numbers as persistent scholarly identifiers.
- Do not duplicate generated feature inventories or large volatile corpus counts in prose.
- Do not restore retired release-certification concepts to support old documentation branches.

## Existing branch disposition

Old PR #67 contains useful earlier research, plan, checker and tests, but it also carries generated `release-certification` / `BUILD-COMPLETE` changes from the superseded architecture. Those generated changes are branch debris. This refreshed lane ports only the documentation research/plan/checker/RED concepts onto current `main`.

## Conclusion

The next implementation should begin with a documentation contract/checker RED, then author the minimal manual against current graph semantics and limitations. Documentation can progress in parallel with corpus correctness work because unresolved defects can be documented explicitly; it does not need to wait for a compatibility-bearing release.
