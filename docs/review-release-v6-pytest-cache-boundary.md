# Adversarial review: release-v6 pytest cache boundary

Issue: #69 / PR #81

This review is logically independent of the protected-tree implementation pass and is recorded before the corrective RED test and production workflow change.

## Blocking finding

Exact-head ordinary CI on `bb2a9110888636f509e680915d1c35d23cc2c94b` passed the complete unit suite and every repository gate through generated feature documentation, then failed `programs/check_stamp.py` because the preceding pytest run had created ignored files such as:

```
programs/tests/__pycache__/test_appcheck.cpython-313-pytest-8.3.4.pyc
```

The current protected-tree implementation is intentionally stricter than a path-based `__pycache__` exemption. It accepts only ordinary `.pyc` payloads that map to a tracked protected source and serialize identically to a fresh compilation of that source. Pytest assertion-rewrite caches contain transformed executable code and therefore correctly do **not** satisfy that equivalence check.

Weakening `_generated_python_cache()` to trust pytest-tagged cache filenames would reopen the forged-bytecode bypass documented in `review-release-v6-pycache-boundary.md` and is rejected.

## Corrective contract

Ordinary repository CI must not create Python bytecode caches before the protected-tree/stamp gate. Set `PYTHONDONTWRITEBYTECODE=1` for the CI test job so pytest and ordinary imports execute from source without leaving ignored executable cache files in protected paths.

The protected-tree verifier itself remains unchanged:

- genuinely equivalent normal interpreter caches may still be accepted;
- forged, malformed, orphaned, excluded-source, noncanonical, or pytest-rewritten caches remain dirty/fail closed;
- no cache filename family is trusted merely because a tool normally generates it.

## RED / GREEN gate

Before editing `.github/workflows/ci.yml`, commit a regression test requiring the CI job to disable bytecode writes. Hosted CI on that RED head must fail for that missing workflow contract.

GREEN then adds only the job-level environment setting. The same exact-head ordinary CI run must prove the practical integration property by reaching and passing `check_stamp.py` after the unit suite.

Because `.github/workflows/ci.yml` is CI orchestration rather than a release input consumed by `release_check.py`, this amendment does not change release-v6 protected-tree semantics, policy schema, TF bytes, or certification evidence format.

A fresh final adversarial review must still challenge whether any executable cache is being broadly trusted, whether the CI environment is applied before pytest starts, and whether normal local fail-closed behavior remains intact.
