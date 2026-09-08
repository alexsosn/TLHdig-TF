# Research: Text-Fabric app version contract

Issue: #37

## Question

Can `app/config.yaml` drift from the released Text-Fabric version without a release gate noticing?

## Current state on main

The immediate stale value reported in #37 no longer reproduces:

- `programs/tlhdig/__init__.py` defines `TF_VERSION = "0.3.0"`;
- `app/config.yaml` defines `provenanceSpec.version: "0.3.0"`.

The equality was repaired as part of the immutable 0.3.0 allocation for manuscript joins. That release change explicitly replaced the old app value `0.1.0` with `0.3.0`.

## Existing guards

There are two relevant validation paths.

### Ordinary CI

`.github/workflows/ci.yml` runs the complete `programs/tests` pytest suite. `programs/tests/test_release_version.py::test_current_release_documentation_and_app_follow_tf_version` asserts:

```python
assert config["provenanceSpec"]["version"] == TF_VERSION
```

Therefore an ordinary pull request or push that changes only one side of the app/version pair is already rejected by CI.

### Release certification

`programs/release_check.py` does not run pytest. Its application gate is:

```text
python programs/check_app.py
```

`check_app.py` loads `TF_VERSION`, selects `tf/<TF_VERSION>`, parses `app/config.yaml`, and calls:

```python
appcheck.check(tf_dir, config)
```

`programs/tlhdig/appcheck.py::check()` validates node types, referenced features, excluded features, and the default text format. It does not inspect `provenanceSpec.version`.

Thus the canonical release-certification path can currently pass its `app` gate even if `app/config.yaml` points `use()`/the browser to a different corpus version. The independent pytest assertion does not close that gap because it is outside `release_check.py`.

## Failure model

The important invariant is not merely that the current literal happens to be `0.3.0`. It is:

> The app version used by Text-Fabric must equal the version of the artifact selected by the app validation/release gate.

For the repository's current release tooling that expected version is `TF_VERSION`.

A stale app pointer is particularly dangerous because the app can still be syntactically valid and the referenced older release can still exist. The failure is therefore silent semantic version skew rather than a missing-file error.

## Candidate designs

### A. Rely only on `test_release_version.py`

Rejected. It protects ordinary CI but not the standalone release-certification app gate.

### B. Make `appcheck.check()` always infer the expected version from `tf_dir.name`

Possible, but it would change the semantics of a general helper that is also used with synthetic test directories and by other validation scripts. It would force every caller/config fixture to carry a provenance version even when testing unrelated app rules.

### C. Add an explicit optional `expected_version` contract to `appcheck.check()`

Preferred.

- `appcheck.check(tf_dir, config, expected_version=TF_VERSION)` requires `provenanceSpec.version` to exist and equal `TF_VERSION`.
- Existing helper callers that validate only feature/node coverage can omit the argument and retain current behavior.
- `programs/check_app.py` supplies `TF_VERSION`, so both CI's dedicated app gate and `release_check.py` inherit the invariant.
- Unit tests can exercise missing, mismatched, and matching versions without a full TF app load.

## Scope and artifact impact

This is validation-only work. It changes neither source conversion nor any `.tf` node/feature/edge value and does not require a new TF artifact version.

`app/config.yaml` itself is already correct on current main, so production work should not rewrite the current version literal merely to create a diff.

## Research conclusion

#37 remains valid, but its remaining defect is narrower than the original report: the immediate stale pointer was incidentally corrected by the 0.3.0 release work, while the release-certification invariant is still missing. The smallest non-duplicative fix is an explicit expected-version check in `appcheck.check()` exercised by `check_app.py`, while retaining the existing release-version pytest assertion as defense in depth.
