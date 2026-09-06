# Building and certifying a TLHdig-TF release

`BUILD-COMPLETE` is written only by the full release certifier. `census.py` is one gate
inside that process and cannot certify a release by itself.

## Normal release sequence

From a clean checkout with the pinned source corpus present:

```bash
python programs/build.py
python programs/release_check.py --mode regression-valid
bash programs/publish_dataset.sh
```

`release_check.py` runs the required source, repair, round-trip, morphology, structure,
Contract A, marker, tag, provenance, alignment, external sign-reference, app, census and
final code-tree-stability gates against one unchanged TF artifact. The external sign
lists are fetched and checked in `release` mode, where an unavailable/partial input is a
failure rather than an allowed CI skip.

The current full-release profile is versioned as **`release-v2`** in
`programs/tlhdig/release_policy.py`. A manifest cannot define its own smaller required
set and still count as a full release: `check_stamp.py --require-full` independently
requires the exact `release-v2` gate profile, required input identities, artifact-digest
algorithm and fidelity baseline fields.

On success the certifier writes:

- `tf/<TF_VERSION>/RELEASE-CERTIFICATION.json` — the complete successful gate manifest;
- `tf/<TF_VERSION>/BUILD-COMPLETE` — compatibility metadata plus the full artifact digest
  and a SHA-256 binding to that manifest;
- `reports/release-certification.json` — the latest certification attempt for audit and
  failure diagnosis.

The manifest records the release policy, exact TF/provenance artifact identity, source
and TF versions, code commit, SHA-256 identities of the corpus manifest, repair manifest
and external sign-reference lock, the known-defect policy and every required gate result.
Those three bound input files are hashed before and after the gate sequence; a change
while validation is running invalidates certification just like a changed `.tf` file.

`publish_dataset.sh` calls `check_stamp.py --require-full`; a historical digest-only stamp
cannot authorize a new publication.

## Artifact identity

Historical `BUILD-COMPLETE` stamps use the original `digest=` field. That digest hashes
all `.tf` basenames and contents, with main-module files before provenance-module files.
It is retained unchanged so already-published artifacts remain verifiable.

That historical stream does not encode the module boundary. In principle a feature can
move between `tf/<version>/` and `tf-provenance/<version>/` without changing the sequence
of basename/content records fed to the old hash. Full certification must detect that
semantic change, so `release-v2` adds a second, module-aware identity:

- algorithm: `tlhdig-tf-modules-v2`;
- hashes an explicit algorithm/version tag;
- hashes the `main` and `provenance` module labels and end-of-module boundaries;
- within each module hashes every `.tf` basename and SHA-256 content digest in sorted
  order.

`RELEASE-CERTIFICATION.json` records this algorithm and digest. A full
`BUILD-COMPLETE` records the same module-aware digest in `artifactDigest=` while retaining
legacy `digest=` for compatibility. `check_stamp.py --require-full` recomputes both and
rejects a changed module layout even when the historical digest happens to remain equal.

## Certification modes

### `regression-valid`

```bash
python programs/release_check.py --mode regression-valid
```

All required gates must pass. Explicit known-fidelity baselines may remain non-zero, but
their counts are recorded in the manifest. A green release in this mode means the known
defect set did not grow and no required gate failed; it does not claim zero known source
fidelity limitations.

### `research-ready`

```bash
python programs/release_check.py --mode research-ready
```

Runs the same gates and additionally requires the designated fidelity-defect baselines to
be zero:

- active entries in `programs/known_lossy.txt`;
- active entries in `programs/contract_a_known.txt`;
- `tlhdig.structure.KNOWN_WORD_DEFICIT`.

The publication-time stamp verifier checks this claim independently, so a manually
rewritten `research-ready` manifest with non-zero baselines is rejected even if its hash
is recomputed into `BUILD-COMPLETE`.

Source exclusions remain separately accounted by the corpus ledger; this mode does not
pretend an explicitly unavailable/encrypted upstream record was converted.

## Code identity

The recorded commit must identify the code that actually ran. Before any release gate,
`release_check.py` asks Git for staged or unstaged changes to **tracked** files and refuses
to certify if there are any. Untracked and ignored files are intentionally excluded from
this cleanliness check because transient `refs/`, reports and caches are expected during
a release; the release inputs that affect certification are bound separately by SHA-256.

The commit identity is taken from `TLHDIG_CODE_COMMIT`, then `GITHUB_SHA`, then
`git rev-parse HEAD`, and must be a full 40-character SHA. Any environment-provided SHA
must equal the checkout's `HEAD` whenever `HEAD` is readable; a syntactically valid but
mismatched override is rejected rather than recorded as the code that ran. The resolver
can fall back to environment metadata if `rev-parse` itself is unavailable, but the full
release command still requires a usable Git checkout because the tracked-tree cleanliness
check is a separate hard prerequisite.

`release-v2` repeats the code identity check as the final required gate, after all
external validation commands. The tracked tree must still be clean **and** `git rev-parse
HEAD` must still equal the commit recorded when certification started. This closes both
ways a validator could otherwise change executable code during the run: modifying tracked
files in place, or checking out/resetting to a different clean commit.

## Historical `tf/0.2.0`

`tf/0.2.0` predates full release certification and carries a digest-bound census-era
`BUILD-COMPLETE`. `python programs/check_stamp.py` can still validate those historical
bytes with the original digest algorithm. `python programs/check_stamp.py --require-full`
rejects the legacy stamp, which is intentional: published historical artifacts are
immutable and are not rewritten merely to upgrade certification metadata.

## Failure semantics

Before any release attempt, the certifier removes a stale `BUILD-COMPLETE` and successful
manifest. A required gate succeeds only with explicit status `passed` and return code 0.
An explicit skip is never a release pass, even if an ordinary-CI command would return 0.

The module-aware TF digest is computed before the first gate and after the last. If any
`.tf` file changes bytes, filename or module membership during validation, certification
fails and no valid stamp remains. The same before/after rule applies to the bound corpus
manifest, repair manifest and external sign-reference lock. The final `code-tree-stable`
gate independently rejects tracked-tree drift or a changed/unreadable Git HEAD.

A failed attempt is written to `reports/release-certification.json`; it is diagnostic only
and cannot be used by `publish_dataset.sh`.
