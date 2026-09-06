# Research: release certification and `BUILD-COMPLETE`

Issue: #24

This inventory was made against `main` at `f3e415e7090a3026d7687b2aa580e42e0b4e99ab`, after #22 made external sign-reference acquisition explicit and reproducible.

## Current stamp semantics

`programs/census.py` is currently the only production caller that writes `BUILD-COMPLETE`. It loads the shipped TF dataset in a fresh process, checks its census invariants and one section-address probe, then calls `tlhdig.stamp.write()`.

`tlhdig.stamp.digest()` hashes every `.tf` file in the main dataset and provenance module. This correctly prevents a stamp for build A from certifying later TF bytes from build B. `programs/build.py` also deletes a stale stamp before rebuilding.

The stamp does **not** currently bind:

- which validation gates ran;
- the code commit that ran them;
- the corpus identity manifest;
- the repair manifest;
- the external sign-list lock;
- pass/fail/skip state for external checks;
- whether the release was merely regression-valid against known-defect baselines or met a stronger zero-known-fidelity-defect policy.

`programs/publish_dataset.sh` calls only `programs/check_stamp.py` before staging. Therefore any invocation of `census.py` that succeeds can currently create a publishable stamp even if other release gates were not run.

## Workflow inventory

### Hosted PR/push CI (`.github/workflows/ci.yml`)

| gate | target | skip/baseline semantics | current relation to stamp |
|---|---|---|---|
| pytest `programs/tests` | code + 91-doc adversarial shard | hard fail | none |
| corpus identity inline check | frozen source bytes | hard fail | none |
| `verify_patches.py` | repair manifest/source hashes | hard fail | none |
| `check_signs.py` | source → signs round trip | known-loss policy inside gate | none |
| `check_morph.py` | morphology parsing | hard regression gate | none |
| `check_app.py` | app config vs shipped TF | hard fail | none |
| `check_stamp.py` | committed TF digest vs existing stamp | validates only current stamp contents | consumes stamp |
| `check_tags.py` | AOxml destination inventory | hard fail | none |
| `check_provenance_split.py` | main/provenance split | hard fail | none |
| `check_alignment.py` | cuneiform coverage | measured regression floor | none |
| `fetch_signrefs.py --mode ordinary` | external sign-list availability/integrity | explicit availability skip may exit 0 | none |
| `check_signrefs.py --mode ordinary` | external sign-list comparison | explicit availability skip may exit 0 | none |

The ordinary CI suite does **not** run `check_structure.py`, `check_contract_a_graph.py`, or `check_markers.py`.

### Dataset workflow (`.github/workflows/dataset.yml`)

The on-demand/monthly full build currently runs:

1. `programs/build.py`
2. `programs/census.py`
3. `programs/check_markers.py`

This ordering is unsafe as release certification: `census.py` writes `BUILD-COMPLETE` **before** marker conservation runs, and the workflow omits structure conservation, Contract A graph validation, sign round-trip, morphology, app, alignment, tag/provenance checks, and external sign references.

## Gate semantics that must remain explicit

### `check_structure.py`

This is a regression-valid gate, not a zero-defect proof. It allows the known word deficit up to `structure.KNOWN_WORD_DEFICIT` (currently 15) and fails only if the deficit grows. A successful run must therefore be recorded as a pass under a policy that still acknowledges a non-zero known defect.

### `check_contract_a_graph.py`

This is also regression-valid rather than zero-defect. It skips whole repaired documents listed in `contract_a_known.txt` and skips graph/source-content comparison for words in `known_lossy.txt`. A green exit code means there are no *additional* mismatches outside those declared sets.

### External sign references after #22

`fetch_signrefs.py` and `check_signrefs.py` now support `--mode ordinary` and `--mode release`. Ordinary mode may return success for an explicit availability skip. Release mode makes an unavailable/partial/stale input non-zero. `reports/signrefs-status.json` records the state. A release certifier should invoke release mode and must never translate that non-zero/skip into a pass.

### Other measured baselines

`check_alignment.py` enforces a regression floor rather than perfect coverage. External sign-reference disagreement has a measured ceiling, not a claim that every outvoted assignment is wrong. These are acceptable in `regression-valid` mode and should remain described as such.

## Required release identity

A successful certification can be reproduced and audited if it records at least:

- `sourceVersion` and `tfVersion`;
- digest and feature-file count for the main + provenance `.tf` artifact;
- code commit SHA;
- SHA-256 of `programs/corpus.sha256` (identity of the frozen source manifest);
- SHA-256 of the repair manifest used by the build;
- SHA-256 of `programs/signrefs.lock.json` for the external validation inputs;
- ordered required gates with command and terminal status.

The artifact digest must be computed before the gate sequence and again after it. If the digest changes, no stamp may be written even if all subprocesses exited zero.

## `regression-valid` vs `research-ready`

The current corpus cannot truthfully claim zero known fidelity defects while the declared structural/Contract-A loss sets remain non-empty. The release command should therefore expose two policies:

- `regression-valid`: all required gates pass; declared known-defect baselines are allowed but recorded.
- `research-ready`: all required gates pass **and** the explicitly designated fidelity-defect baselines are empty/zero. At minimum this includes `known_lossy.txt`, `contract_a_known.txt`, and `structure.KNOWN_WORD_DEFICIT`.

This distinction must not reinterpret legitimate explicit source exclusions (for example encrypted/unparseable upstream files) as silently successful conversion; exclusions remain separately accounted by the source ledger.

## Design consequences

1. `census.py` must stop owning the stamp. It remains one required gate and report generator.
2. One canonical `release_check.py` should run the complete ordered release gate set and be the only normal writer of `BUILD-COMPLETE`.
3. The successful gate manifest must itself be cryptographically bound by the stamp; otherwise a valid stamp plus a later-edited manifest can lie about what ran.
4. A failed or skipped required gate must leave no valid stamp.
5. The dataset workflow should invoke the canonical release command after `build.py` rather than independently sequencing a subset of checks.
6. Ordinary PR CI may continue to use `--mode ordinary` for external references, but that state cannot produce a release stamp.
