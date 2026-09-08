# Plan: recover corrupt sign-reference caches safely

**Issue:** #36  
**Research prerequisite:** `docs/research-signref-corrupt-cache-recovery.md`

This ticket follows **research → plan → RED → implementation → test → independent review**. No production acquisition code changes before this plan.

## 1. Invariants

Preserve these existing contracts:

- a verified cache is reused when `refresh=False`;
- `refresh=True` re-fetches even a verified cache when network access is allowed;
- missing inputs may be an explicit policy/availability skip in ordinary mode;
- a known integrity failure is a hard `FAILED` state in both ordinary and release modes;
- fetched bytes are verified against the pinned revision/hash before replacing a cached file;
- failed/unavailable recovery never overwrites the previous cached bytes.

New contract:

- with network access allowed, an invalid cached file is a recoverable condition: attempt a verified re-fetch;
- if recovery succeeds, replace it atomically and report the source as `verified` with detail `fetched`;
- if recovery is unavailable or invalid, retain a hard failure rather than downgrading the known corrupt cache to a skip;
- when `refresh=False`, unrelated verified cached siblings are not re-fetched merely because another source is corrupt.

## 2. RED tests

Add failing tests before production changes for:

1. corrupt cache + network + `refresh=False` → fetcher is called, good bytes replace corrupt bytes, result `PASSED`;
2. corrupt cache + network + `refresh=True` → same recovery succeeds;
3. corrupt cache + `network=False` → fetcher not called, result stays `FAILED`, bytes unchanged;
4. corrupt cache + recovery network unavailable → result remains `FAILED`, bytes unchanged;
5. corrupt cache + fetched payload fails integrity → result `FAILED`, bytes unchanged;
6. mixed set with one valid cached source and one corrupt source, `refresh=False` → only corrupt source is fetched;
7. existing verified-cache refresh regression remains green.

The primary RED must fail because current `prepare()` returns the local `FAILED` result before acquisition, not because of an invalid fixture.

## 3. Implementation design

Make the acquisition path itself capable of recovering an invalid existing cache without broad refresh:

- in `acquire()`, when `target.is_file()` and `refresh=False`, verify the cache as today;
- on successful verification, keep the current cached fast path;
- on verification failure, remember that this source had a cached integrity failure and fall through to the fetch path instead of appending/continuing immediately;
- if the replacement verifies, `_atomic_write()` replaces the corrupt file;
- if the fetch is unavailable after a cached integrity failure, report that source as `failed` (with detail including both the cached failure and recovery failure) so aggregate state remains `FAILED`;
- if replacement integrity verification fails, existing `FAILED` handling applies and no write occurs.

Then change `prepare()` ordering:

- if local state is `FAILED` and `network=False`, return the local hard failure unchanged;
- if local state is `FAILED` and network is allowed, continue to `acquire()` rather than returning;
- preserve all existing `PASSED`, missing/policy-skip and explicit-refresh behavior.

This design avoids forcing `refresh=True` for the entire source set, so valid siblings remain cached during targeted recovery.

## 4. Scope control

Do not change:

- lock schema or hashes;
- `fetch_source()` transport/provenance semantics;
- `verify_payload()`;
- mode exit-code policy;
- release certification or TF artifacts;
- CLI flags or names.

No new allowlist, retry loop or automatic hash update is permitted.

## 5. Test gate

Run at least:

```text
python -m pytest programs/tests/test_signref_inputs.py programs/tests/test_signref_refresh.py -q
python -m pytest programs/tests -q
```

Then rely on normal PR CI for corpus identity, repair/sign/morph/app/release gates that are unaffected but serve as regression coverage.

## 6. Independent adversarial review

A logically separate review pass must challenge:

- downgrade of a known integrity failure to an ordinary-mode skip;
- accidental refresh of every valid cached source;
- overwriting corrupt cache bytes before replacement verification;
- behavior with mixed valid/corrupt/missing sources;
- `network=False` accidentally invoking the fetcher;
- changing existing `refresh=True` semantics;
- duplicate retry/fetch behavior between `prepare()` and `acquire()`;
- hidden release/artifact impact.

Blocking findings trigger implementation → tests → fresh review.
