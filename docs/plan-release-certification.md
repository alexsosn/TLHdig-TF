# Plan: one full release certification gate

Issue: #24

Research: `docs/research-release-certification.md`

## Compatibility boundary

`tf/0.2.0` already carries a census-era `BUILD-COMPLETE`. This ticket must not rewrite the published `.tf` artifact or collide with #10/PR #11's planned next TF artifact. The implementation therefore distinguishes:

- **legacy content-bound stamp**: validates that an existing committed artifact still matches the digest recorded by the old census stamp; useful for checking historical `0.2.0`, but never sufficient for publication under the new policy;
- **full certification stamp**: binds both the `.tf` digest and a successful release-certification manifest. `publish_dataset.sh` requires this form.

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
14. `census.py` (report/invariants only; it no longer stamps).

The command computes the main+provenance TF digest before gate 1 and after the final gate. A changed digest is a hard failure and no stamp is written.

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

Successful manifest fields:

```json
{
  "schema": 1,
  "mode": "regression-valid",
  "sourceVersion": "0.3",
  "tfVersion": "...",
  "codeCommit": "...",
  "dataset": {"digest": "sha256:...", "features": 0},
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

The manifest must not require a wall-clock timestamp for identity. `codeCommit` comes from `TLHDIG_CODE_COMMIT`, then `GITHUB_SHA`, then `git rev-parse HEAD`; inability to resolve it is a release failure.

## Known-defect policy

Add a deterministic summary for the fidelity baselines that make the current corpus regression-valid rather than research-ready:

- number of active entries in `programs/known_lossy.txt`;
- number of active entries in `programs/contract_a_known.txt`;
- `tlhdig.structure.KNOWN_WORD_DEFICIT`.

`regression-valid` records these and allows non-zero values if all existing gates pass.

`research-ready` requires all three values to be zero. It does **not** silently discard explicit source exclusions; those remain governed by the ledger/census and are recorded separately rather than treated as converted data.

## Stamp v2

Extend `tlhdig.stamp.write()` to accept the successful certification manifest and record:

```text
sourceVersion=...
tfVersion=...
features=...
digest=sha256:...
certification=sha256:<manifest bytes>
mode=...
commit=...
```

`stamp.check()` continues to validate legacy digest-only stamps by default so historical `tf/0.2.0` remains checkable. Add `require_full=True` to require:

- certification fields;
- `RELEASE-CERTIFICATION.json` present;
- certification-file hash matches the stamp;
- manifest dataset digest equals the current `.tf` digest;
- manifest source/tf version matches the stamp;
- every recorded required gate is `passed`;
- manifest mode/commit matches the stamp.

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
10. legacy stamp accepted only when `require_full=False`.

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
- comments/docstrings in census/stamp/publish workflow.

## Independent review checklist

A logically independent reviewer must verify:

- census cannot create a full stamp;
- publish refuses legacy stamps;
- a failed/skipped gate cannot leave a valid current stamp;
- external signrefs run in release mode;
- the manifest is bound cryptographically to the stamp;
- all required gates validate one unchanged TF digest;
- code/source/repair/signref identities are present and reproducible;
- `regression-valid` does not masquerade as `research-ready`;
- no published `.tf` artifact or version was modified by this PR.
