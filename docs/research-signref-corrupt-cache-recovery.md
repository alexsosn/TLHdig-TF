# Research: recover corrupt sign-reference caches safely

**Issue:** #36  
**Base:** `main` at `b7e0b31d14e7037f93b7659cf394683dba4f170b`

## Question

Can `programs/tlhdig/signref_inputs.prepare()` recover a cached external sign-reference file that fails the pinned integrity check, and what failure semantics must be preserved while adding recovery?

## Current control flow

`prepare()` first calls `inspect_local()`. `inspect_local()` reports `FAILED` if any existing cached file fails `verify_payload()`.

The current `prepare()` order is:

```python
local = inspect_local(source_list, directory)
if local.state == FAILED:
    return local
if local.state == PASSED and (not refresh or not network):
    return local
if not network:
    return Result(SKIPPED_POLICY, local.sources)
return acquire(source_list, directory, fetcher=fetcher, refresh=refresh)
```

Therefore a corrupt cache returns before either `network` or `refresh` can lead to acquisition. `--refresh` cannot heal exactly the state for which a replacement is needed.

`acquire()` also does not currently heal an invalid existing file when `refresh=False`: it verifies the cached bytes, records a failed row, and `continue`s without trying the fetcher.

## Existing test coverage

`programs/tests/test_signref_refresh.py::test_prepare_refresh_refetches_even_a_verified_cache` proves that `refresh=True` re-fetches a *valid* cached file. It does not cover invalid cached bytes.

The larger `test_signref_inputs.py` suite covers lock validation, verification, acquisition, network-unavailable semantics and mode exit codes, but there is no regression for the sequence `corrupt cache -> network recovery -> verified replacement`.

## Failure-state contract

`programs/fetch_signrefs.py` explicitly states:

> Integrity failures always fail in both modes.

That contract must remain true while recovery is attempted. A corrupt cache may become `PASSED` only after a replacement payload passes the same pinned revision/hash verification and is written atomically.

A failed recovery must not downgrade a known integrity failure to `SKIPPED_UNAVAILABLE` merely because the network was unavailable. Otherwise ordinary mode could exit successfully while a known-corrupt cache remains on disk.

## Required behavior matrix

| Local state | Network | Refresh | Required behavior |
|---|---:|---:|---|
| verified | yes/no | false | use cache; no fetch |
| verified | yes | true | re-fetch; existing refresh behavior unchanged |
| missing | yes | either | fetch using existing acquisition behavior |
| missing | no | either | existing policy skip behavior unchanged |
| corrupt | no | either | remain `FAILED`; do not fetch |
| corrupt | yes | false | attempt recovery of corrupt source; valid cached siblings need not refresh |
| corrupt | yes | true | attempt refresh/recovery as requested |
| corrupt + replacement verifies | yes | either | atomically replace file; report `PASSED`/`fetched` |
| corrupt + fetch unavailable | yes | either | remain `FAILED`; corrupt file remains untouched |
| corrupt + replacement integrity fails | yes | either | remain `FAILED`; corrupt file remains untouched |

## Atomicity

`_atomic_write()` is already safe for this use: acquisition verifies fetched bytes *before* calling `_atomic_write()`, and `os.replace()` swaps the verified temporary file into place. No partial or unverified replacement needs to be introduced.

## Scope / release impact

This is developer/CI input-acquisition behavior only. It does not alter source corpus bytes, conversion semantics, TF features, node/edge numbering, section addressing, release metadata or any shipped TF artifact. No TF version bump or artifact rebuild is justified.

## Design implication

The narrow fix should make the acquisition path capable of treating an invalid existing cache as a recoverable input condition when network access is allowed, while retaining a hard failure if verified replacement cannot be obtained. It should avoid re-fetching unrelated valid cached sources unless `refresh=True` was explicitly requested.
