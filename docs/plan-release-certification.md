# Plan: one full release certification gate

Issue: #24

Research: `docs/research-release-certification.md`

## Compatibility boundary

`tf/0.2.0` already carries a census-era `BUILD-COMPLETE`. This ticket must not rewrite the published `.tf` artifact or collide with #10/PR #11's planned next TF artifact. The implementation therefore distinguishes:

- **legacy content-bound stamp**: validates that an existing committed artifact still matches the digest recorded by the old census stamp; useful for checking historical `0.2.0`, but never sufficient for publication under the new policy;
- **full certification stamp**: binds both the TF artifact identity and a successful release-certification manifest. `publish_dataset.sh` requires this form.

No existing `.tf` file or TF version changes in this ticket.

## Canonical command

Add `programs/release_check.py` as the only normal writer of a new full `BUILD-COMPLETE`.

Supported modes:

```text
python programs/release_check.py --mode regression-valid
python programs/release_check.py --mode research-ready
```

Both modes run the same required validation gates. `research-ready` additionally fails if designated non-zero fidelity-defect baselines remain.

## Ordered gates

Run these against the already-built artifact, fail-fast on the first non-zero required gate, and record all gates reached:

1. corpus identity (`tlhdig.corpusid` against `programs/corpus.sha256`);
2. `verify_patches.py`;
3. `check_signs.py`;
4. `check_morph.py`;
5. `check_structure.py`;
6. `check_contract_a_graph.py`;
7. `check_markers.py`;
8. `check_tags.py`;
9. `check_provenance_split.py`;
10. `check_alignment.py`;
11. `fetch_signrefs.py --mode release`;
12. `check_signrefs.py --mode release`;
13. `check_app.py`;
14. `census.py` (report/invariants only; it no longer stamps);
15. final code-tree stability check: tracked tree still clean and `HEAD` still equals the recorded start commit.

The command computes the module-aware main+provenance TF artifact digest before gate 1 and after the final gate. A changed digest is a hard failure and no stamp is written.

## Census ownership change

Change `programs/census.py` so it never writes `BUILD-COMPLETE`. Its responsibility becomes:

- fresh TF load;
- census/report generation;
- census invariants;
- exit status only.

Documentation and output must direct users to `release_check.py` for certification.

## Certification manifest

Add a pure/testable helper module `programs/tlhdig/certification.py` and write a successful manifest to:

```text
tf/<TF_VERSION>/RELEASE-CERTIFICATION.json
```

Also write the latest attempt/status to `reports/release-certification.json` so a failed run remains diagnosable without producing a valid release stamp.

Successful manifest fields include:

```json
{
  "schema": 1,
  "policy": "release-v2",
  "mode": "regression-valid",
  "sourceVersion": "0.3",
  "tfVersion": "...",
  "codeCommit": "...",
  "dataset": {
    "algorithm": "tlhdig-tf-modules-v2",
    "digest": "sha256:...",
    "features": 0
  },
  "inputs": {
    "corpusManifest": "sha256:...",
    "repairManifest": "sha256:...",
    "signrefLock": "sha256:..."
  },
  "knownDefects": {...},
  "gates": [
    {"name": "...", "command": ["..."], "status": "passed", "returncode": 0}
  ]
}
```

The manifest must not require a wall-clock timestamp for identity. `codeCommit` comes from `TLHDIG_CODE_COMMIT`, then `GITHUB_SHA`, then `git rev-parse HEAD`. If Git HEAD is readable, an environment SHA must match it. A full certification also verifies at the final gate that HEAD still equals the recorded start commit.

## Known-defect policy

Add a deterministic summary for the fidelity baselines that make the current corpus regression-valid rather than research-ready:

- number of active entries in `programs/known_lossy.txt`;
- number of active entries in `programs/contract_a_known.txt`;
- `tlhdig.structure.KNOWN_WORD_DEFICIT`.

`regression-valid` records these and allows non-zero values if all existing gates pass.

`research-ready` requires all three values to be zero. It does **not** silently discard explicit source exclusions; those remain governed by the ledger/census and are recorded separately rather than treated as converted data.

## Full stamp and artifact identity

Keep the historical `digest=` calculation byte-for-byte compatible so existing `tf/0.2.0` stamps remain verifiable. That legacy stream hashes basename/content records from main then provenance, but it does not encode the module boundary and is therefore insufficient as the identity primitive for a new full release.

For full certification add policy `release-v2` and artifact digest algorithm `tlhdig-tf-modules-v2`. The full digest hashes:

- an explicit algorithm/version tag;
- the `main` module label, each sorted `.tf` basename/content hash, and a module boundary;
- the `provenance` module label, each sorted `.tf` basename/content hash, and a module boundary.

A full stamp records both compatibility and full-release identities:

```text
sourceVersion=...
tfVersion=...
features=...
digest=sha256:<legacy-compatible digest>
artifactDigestAlgorithm=tlhdig-tf-modules-v2
artifactDigest=sha256:<module-aware digest>
certification=sha256:<manifest bytes>
mode=...
commit=...
```

`stamp.check()` continues to validate legacy digest-only stamps by default so historical `tf/0.2.0` remains checkable. `require_full=True` additionally requires:

- certification fields and the canonical current release policy;
- current module-aware artifact digest algorithm and digest;
- `RELEASE-CERTIFICATION.json` present;
- certification-file hash matches the stamp;
- manifest dataset algorithm/digest equals the current main+provenance layout and bytes;
- manifest source/tf version matches the stamp;
- every canonical required gate is present in order and `passed` with return code 0;
- manifest mode/commit matches the stamp;
- required release-input identities and fidelity baseline fields are present.

`programs/check_stamp.py --require-full` exposes this policy.

`programs/publish_dataset.sh` must use `--require-full`, so a legacy census-only stamp cannot publish a new release.

## RED sequence

Before production implementation, add tests that fail on current code for:

1. a full stamp requiring and verifying a certification manifest;
2. manifest tampering invalidating the stamp;
3. a dataset mutation invalidating both legacy/full certification;
4. a runner refusing to stamp after a required gate failure;
5. a runner refusing a release-mode external skip/non-zero status;
6. artifact digest changing between first and final gate;
7. `regression-valid` allowing recorded non-zero known defects;
8. `research-ready` refusing the same non-zero defects;
9. successful clean certification producing manifest + stamp;
10. legacy stamp accepted only when `require_full=False`;
11. syntactically valid environment commit differing from Git HEAD;
12. moving a feature between main/provenance while preserving the legacy hash stream;
13. tracked code mutation during gate execution;
14. switching/resetting to another clean Git HEAD during gate execution.

Use fake commands/runners and temporary TF files for unit tests; corpus-wide commands are covered by hosted integration execution after GREEN.

## Workflow integration

Change `.github/workflows/dataset.yml` to:

```text
build.py
release_check.py --mode regression-valid
upload reports
```

The release checker itself owns external-reference acquisition in `--mode release` and all other required gates.

PR/push CI remains the faster ordinary suite. It may validate the historical committed stamp without claiming it is a full new-release certification.

## Documentation

Update:

- `KNOWN-ISSUES.md`: close the defect and state exactly what legacy vs full stamps mean;
- README release/rebuild instructions: `build.py` → `release_check.py` → `publish_dataset.sh`;
- comments/docstrings in census/stamp/publish workflow;
- `docs/RELEASE.md`: exact policy, module-aware identity, code identity and failure semantics.

## Independent review checklist

A logically independent reviewer must verify:

- census cannot create a full stamp;
- publish refuses legacy stamps;
- a failed/skipped gate cannot leave a valid current stamp;
- external signrefs run in release mode;
- the manifest is bound cryptographically to the stamp;
- all required gates validate one unchanged module-aware TF artifact identity;
- moving a feature between main/provenance invalidates full certification even when the legacy digest collides;
- code/source/repair/signref identities are present and reproducible;
- the recorded commit equals Git HEAD at both start and final gate and the tracked tree is clean at both points;
- `regression-valid` does not masquerade as `research-ready`;
- no published `.tf` artifact or version was modified by this PR.

## Review-driven amendments

The original design used one main+provenance digest and only checked tracked-tree cleanliness before gates. Adversarial review demonstrated two concrete counterexamples: the historical digest does not bind module membership, and validation could change tracked code or switch to another clean commit after the initial check. The final plan above incorporates the resulting RED→GREEN fixes as `release-v2`; the historical digest remains only for immutable backward compatibility.
