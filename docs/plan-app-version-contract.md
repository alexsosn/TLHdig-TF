# Plan: Text-Fabric app version invariant

Issue: #37
Research: `docs/research-app-version-contract.md`

## Goal

Make the dedicated app gate, and therefore release certification, fail whenever `app/config.yaml` selects a Text-Fabric version different from `TF_VERSION`.

## Contract

Extend:

```python
appcheck.check(tf_dir, config)
```

to accept an optional keyword-only expected version:

```python
appcheck.check(tf_dir, config, *, expected_version=None)
```

When `expected_version` is not `None`:

1. `config.provenanceSpec.version` must be present;
2. its value, converted to text without semantic version normalization, must equal `expected_version` exactly;
3. a missing value and a mismatched value each produce one clear problem message;
4. all existing app feature/type/format checks still run so callers receive the complete problem set.

When `expected_version` is `None`, version validation is skipped. This preserves the helper's current use in focused fixtures and non-release callers.

`programs/check_app.py` must call:

```python
appcheck.check(tf_dir, config, expected_version=TF_VERSION)
```

This makes the invariant part of the existing CI app gate and of `release_check.py` without adding a new gate or duplicating release orchestration.

## TDD / RED gate

Before implementation, add unit tests to `programs/tests/test_appcheck.py` proving:

1. matching `provenanceSpec.version` passes when `expected_version` is supplied;
2. a mismatched version fails and the message contains both configured and expected values;
3. a missing `provenanceSpec.version` fails when `expected_version` is supplied;
4. existing configs without provenance metadata still pass when no expected version is requested.

Also add a shipped-config test that calls the same version-aware `appcheck.check()` path used by `check_app.py`, so future refactors cannot leave the script and library contracts disconnected.

The RED commit must precede production changes. On the RED commit the new tests are expected to fail because `check()` does not yet accept `expected_version`.

## Implementation

Change only:

- `programs/tlhdig/appcheck.py` — version validation;
- `programs/check_app.py` — pass `TF_VERSION`;
- tests required by the RED contract.

Do not change `app/config.yaml`: it already matches `0.3.0`.

## Test gate

Run, at minimum:

```text
python -m pytest programs/tests/test_appcheck.py -q
python -m pytest programs/tests/test_release_version.py -q
python programs/check_app.py
python -m pytest programs/tests -q
```

CI is expected to rerun the repository-wide corpus gates after the PR opens.

Because this is validation-only work, no generated TF artifact or release stamp should change in the PR.

## Adversarial review gate

Review independently against the final diff and challenge:

- whether the gate actually runs from `release_check.py` rather than only pytest;
- whether a missing version can pass silently;
- whether YAML numeric coercion or non-string values create surprising equality behavior;
- whether version normalization could make distinct release identifiers compare equal;
- whether adding the argument breaks existing `appcheck.check()` callers;
- whether tests merely duplicate implementation logic instead of asserting the public contract;
- whether the PR accidentally modifies the immutable `tf/0.3.0` artifact or certification files.

Blocking findings require another implementation/test/review iteration.

## Completion

Close #37 when the version-aware app gate is green in CI and the final adversarial review finds no blocking issue.
