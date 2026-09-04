# Independent review — project metadata (Phase 3)

This review is intentionally separate from the implementation pass. It is not the final approval; it records findings that must be closed before the final-diff review.

## Review findings

1. **Beta 0.3 converter accepted a legacy Beta 0.2 path with no project code.**
   `sourcepath.parse()` correctly supports both published grammars, but `convert.director()` only checked `parse_ok`. A path such as `CTH 101_XML/KUB 21.8.xml` could therefore produce a document with blank `project`, contradicting the Phase 3 invariant for the pinned TLHdig 0.3 source release.

2. **The generated provenance README was version-stale.**
   `programs/build.py` hard-coded `tf/0.1.0` and `tf-provenance/0.1.0` in the README written inside `tf-provenance/<TF_VERSION>/`. The first certified `0.2.0` artifact therefore carried an incorrect load example even though its TF feature gates were green.

3. **Current-facing documentation still advertised `0.1.0` after the ontology version bump.**
   README quick-start paths, the current Known Issues heading, CFF summary and direct-Fabric integration example still named the historical prototype. The conversion-plan repository-layout example also still named `0.1.0`. Historical audit/research documents were deliberately left unchanged because those references identify the state they measured.

## TDD evidence

Findings 1–2 were converted to regression tests before production changes. CI #86 on the test-only head reported exactly:

- `345 passed, 2 failed`;
- `test_beta_03_converter_rejects_legacy_path_without_project_code` — no `ValueError` was raised;
- `test_provenance_readme_names_the_current_release` — generated README still named `0.1.0`.

Production fixes were then limited to:

- rejecting a successfully parsed source path whose `project` is empty at the TLHdig 0.3 converter boundary;
- formatting the provenance README load paths from `TF_VERSION`.

Finding 3 received its own test-only RED. CI #91 reported **347 passed, 1 failed**, with the sole failure `test_current_release_documentation_follows_tf_version`; the first assertion showed README still advertising `0.1.0`. Current operational docs were then updated to `0.2.0`, the README examples use canonical `project` while loading the compatibility `subcorpus` feature too, and the stale external Agora registry block remains untouched because it documents an external pin rather than this repository's current path.

Because finding 2 changes generated release content, the previously certified branch artifact is not final and must be regenerated from scratch before merge.

## Remaining gates

- ordinary full CI GREEN on all review regressions and current-doc contract;
- fresh certified rebuild of `tf/0.2.0` and `tf-provenance/0.2.0` from the reviewed generator, including structure and Contract-A release checks;
- preservation check for `0.1.0`;
- verify the regenerated provenance README names `0.2.0`;
- final independent review of the complete PR diff;
- any further finding loops back through regression test → fix → CI/rebuild → re-review;
- merge, then tag/release `tlhdig-0.3_tf-0.2.0` on the exact merged commit.
