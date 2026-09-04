# Independent review — project metadata (Phase 3)

This review is intentionally separate from the implementation pass. It is not the final approval; it records findings that must be closed before the final-diff review.

## Review findings

1. **Beta 0.3 converter accepted a legacy Beta 0.2 path with no project code.**
   `sourcepath.parse()` correctly supports both published grammars, but `convert.director()` only checked `parse_ok`. A path such as `CTH 101_XML/KUB 21.8.xml` could therefore produce a document with blank `project`, contradicting the Phase 3 invariant for the pinned TLHdig 0.3 source release.

2. **The generated provenance README was version-stale.**
   `programs/build.py` hard-coded `tf/0.1.0` and `tf-provenance/0.1.0` in the README written inside `tf-provenance/<TF_VERSION>/`. The first certified `0.2.0` artifact therefore carried an incorrect load example even though its TF feature gates were green.

## TDD evidence

Both findings were converted to regression tests before production changes. CI #86 on the test-only head reported exactly:

- `345 passed, 2 failed`;
- `test_beta_03_converter_rejects_legacy_path_without_project_code` — no `ValueError` was raised;
- `test_provenance_readme_names_the_current_release` — generated README still named `0.1.0`.

Production fixes were then limited to:

- rejecting a successfully parsed source path whose `project` is empty at the TLHdig 0.3 converter boundary;
- formatting the provenance README load paths from `TF_VERSION`.

Because the second fix changes generated release content, the previously certified branch artifact is not final and must be regenerated from scratch before merge.

## Remaining gates

- ordinary CI GREEN on the two new regression tests;
- fresh certified rebuild of `tf/0.2.0` and `tf-provenance/0.2.0` from the reviewed generator;
- preservation check for `0.1.0`;
- operational current-version documentation update;
- final independent review of the complete PR diff;
- any further finding loops back through regression test → fix → CI/rebuild → re-review;
- merge, then tag/release `tlhdig-0.3_tf-0.2.0` on the exact merged commit.
