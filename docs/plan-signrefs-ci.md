# Plan: reproducible external sign-reference validation

Issue: #22

Research prerequisite: `docs/research-signrefs-ci.md`.

## Contract

External-reference execution has four machine-readable states:

- `passed`: the complete locked input set was verified, parsed, and the scholarly gate passed;
- `failed`: integrity, parsing, or scholarly validation failed;
- `skipped-unavailable`: the complete set could not be obtained because an input/network resource was unavailable;
- `skipped-policy`: the caller intentionally requested an offline/no-network diagnostic run and no complete verified local set was available.

Every invocation writes/prints the state and the per-source provenance used. A partial set is never `passed`.

Policy differs by mode:

- **ordinary**: `skipped-unavailable` and `skipped-policy` are explicit successful *diagnostic* outcomes; integrity mismatch or malformed content is still `failed`;
- **release**: only `passed` exits successfully. Either skip state exits non-zero, so #24 cannot certify a release on a missing witness.

## Data and acquisition design

1. Add `programs/signrefs.lock.json` as the single source lock. Each entry records local filename, canonical URL/repository, immutable revision, expected content/object hash, hash kind, license, and lineage/provenance note.
2. Add a small stdlib-only acquisition module under `programs/tlhdig/`:
   - validate the lock schema before network access;
   - fetch GitHub raw files by commit and verify Git blob SHA-1 over `blob <len>\0<bytes>`;
   - fetch Wiktionary through the MediaWiki revisions API by exact revision ID, require the returned revision ID, compare the returned MediaWiki SHA-1 with the lock, then write the returned content;
   - write through a temporary file and atomically replace the local reference only after integrity succeeds;
   - never accept a current branch, mutable `latest` URL, redirect-derived version, or unpinned content.
3. Add `programs/fetch_signrefs.py` to populate the ignored `refs/` directory. It exposes ordinary/release policy and a maintainer inspection mode that can print the upstream revision hash without writing an unlocked file; this is used once to bootstrap a newly pinned source, not by certification.
4. Make `programs/check_signrefs.py` validate completeness/integrity before calling `signrefs.load()`. Keep the existing vote/alignment semantics unchanged.
5. Emit `reports/signrefs-status.json` with overall state plus source/revision/hash records. Keep `reports/signrefs.md` as the human-readable scholarly report.
6. Update hosted CI to fetch the locked references before `check_signrefs.py`. CI remains reproducible from a clean checkout and no secrets.
7. Document offline behavior and the fact that the external data remain transient and git-ignored.

## TDD order

### RED: lock/acquisition tests

Add tests before production code for:

1. complete locked set -> verified/available;
2. one missing local file -> incomplete, never pass;
3. wrong Git blob hash -> hard failure;
4. wrong MediaWiki revision/hash -> hard failure;
5. malformed/empty payload -> hard failure before scholarly success;
6. network/fetch failure -> `skipped-unavailable` in ordinary mode and non-zero in release mode;
7. atomicity: a failed replacement cannot overwrite a previously verified file;
8. lock entry without immutable revision/hash -> rejected before fetch.

### RED: execution-policy tests

9. ordinary offline/no-fetch incomplete run -> `skipped-policy`, exit 0;
10. release offline/no-fetch incomplete run -> skip state but exit non-zero;
11. full verified inputs permit the existing sign-reference gate to run;
12. partial inputs never invoke the scholarly vote as though complete.

### GREEN implementation

Implement only enough acquisition/status plumbing to satisfy those tests; do not alter sign normalisation, equivalence classes, vote thresholds, or corpus alignment.

### Integration

- wire `.github/workflows/ci.yml` to acquisition + validation;
- verify a draft PR first demonstrates the RED tests, then becomes green after implementation;
- use the maintainer hash-inspection path to obtain and lock Wiktionary revision `83078078` before declaring the PR complete;
- ensure a clean runner reports all six source names/revisions and `passed`, not a silent skip.

## Independent review gate

Before merge, re-read the final diff from the perspective of an adversarial reviewer and challenge at least:

- license/provenance claims versus the pinned upstream revisions;
- any mutable URL or unverified redirect;
- hash verification timing (must occur before replacing/using files);
- partial-set behavior;
- ordinary versus release exit codes;
- whether `skipped-*` can accidentally satisfy #24;
- network/auth assumptions on a clean GitHub-hosted runner;
- whether test fixtures exercise production fetch/status code rather than mocks that bypass it.

Any finding re-enters implementation + tests, then the review pass repeats.
