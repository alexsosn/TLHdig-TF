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
manuscript-apparatus conservation, Contract A, marker, tag, provenance, alignment,
external sign-reference, app, census, predecessor-delta and final code-tree-stability
gates against one unchanged TF artifact. The manuscript gate independently reconstructs
repaired/strict source apparatus and checks fragment occurrences, source-statement
multiplicity, block-scoped witnesses and the limited `joined` projection; it does not
reuse the graph emitter. The external sign lists are fetched and checked in `release`
mode, where an unavailable/partial input is a failure rather than an allowed CI skip.

The current full-release profile is versioned as **`release-v4`** in
`programs/tlhdig/release_policy.py`. A manifest cannot define its own smaller required
set and still count as a full release: `check_stamp.py --require-full` independently
requires the exact gate/input/fidelity contract belonging to the policy recorded in the
manifest. Historical **`release-v3`** manifests remain verifiable against their frozen v3
contract; unknown policy identifiers are rejected.

Release-v4 also binds the intended change from the previous certified artifact. The
release declaration is `programs/release-delta.json`. For releases after the explicit
0.3.0 adoption baseline it names the predecessor version, pins its module-aware SHA-256
digest, and declares the exact sorted set of changed serialized features as
`main:<feature>.tf` or `provenance:<feature>.tf`. The `predecessor-delta` gate fails if
the materialized predecessor has the wrong digest, if an undeclared feature changes, or
if a declared feature does not change. Added and removed features count as changes and
the side that exists must still parse as a valid TF feature.

For ordinary node/edge features the comparator ignores documentary metadata but includes
the loader-visible semantic header in the comparison: feature kind (`@node`/`@edge`),
effective `@valueType` and effective `@edgeValues`, together with the exact serialized
data body. Thus the same body with a changed value type or node/edge interpretation is a
release delta. For `otext.tf`, configuration is compared while ignoring only
`@version=` and `@dateWritten=`.

The predecessor checker itself is offline. It expects the predecessor at
`tf/<predecessorVersion>` with the corresponding optional provenance module at
`tf-provenance/<predecessorVersion>`. The predecessor version must be one path component;
path separators and traversal are rejected. If old versions are later retired from the
Git tree, a release workflow may materialize a pinned release asset at that layout before
running the unchanged checker. Missing or incorrect predecessor bytes are a hard
certification failure.

On success the certifier writes:

- `tf/<TF_VERSION>/RELEASE-CERTIFICATION.json` — the complete successful gate manifest;
- `tf/<TF_VERSION>/BUILD-COMPLETE` — compatibility metadata plus the full artifact digest
  and a SHA-256 binding to that manifest;
- `reports/release-certification.json` — the latest certification attempt for audit and
  failure diagnosis.

The manifest records the release policy, exact TF/provenance artifact identity, source
and TF versions, code commit, SHA-256 identities of the corpus manifest, repair manifest,
external sign-reference lock and release-delta declaration, the known-defect policy and
every required gate result. The predecessor gate additionally records structured evidence
containing its expected and observed changes. A normal post-baseline release records the
predecessor version/digest; the one-time adoption baseline records its frozen baseline
digest. Those four bound input files are hashed before and after the gate sequence; a
change while validation is running invalidates certification just like a changed `.tf`
file.

`publish_dataset.sh` calls `check_stamp.py --require-full`; a historical digest-only stamp
cannot authorize a new publication.

## Artifact identity

Historical `BUILD-COMPLETE` stamps use the original `digest=` field. That digest hashes
all `.tf` basenames and contents, with main-module files before provenance-module files.
It is retained unchanged so already-published artifacts remain verifiable.

That historical stream does not encode the module boundary. In principle a feature can
move between `tf/<version>/` and `tf-provenance/<version>/` without changing the sequence
of basename/content records fed to the old hash. Full certification detects that
semantic change with the module-aware identity introduced in release-v2 and retained by
release-v3 and release-v4:

- algorithm: `tlhdig-tf-modules-v2`;
- hashes an explicit algorithm/version tag;
- hashes the `main` and `provenance` module labels and end-of-module boundaries;
- within each module hashes every `.tf` basename and SHA-256 content digest in sorted
  order.

`RELEASE-CERTIFICATION.json` records this algorithm and digest. A full
`BUILD-COMPLETE` records the same module-aware digest in `artifactDigest=` while retaining
legacy `digest=` for compatibility. `check_stamp.py --require-full` recomputes both and
rejects a changed module layout even when the historical digest happens to remain equal.

## Predecessor-delta declaration

TF 0.3.0 is the single release-v4 adoption baseline. Its identity is frozen in the
release-v4 policy contract, and its committed declaration repeats that identity:

```json
{
  "schema": 1,
  "tfVersion": "0.3.0",
  "baseline": true,
  "baselineDigest": "sha256:93790f9e283c3c3d29d8a751b1eecbb7fd908745470aa36b9cec0525b90182d1"
}
```

The baseline flag is accepted only for `TF_VERSION == 0.3.0`, only when the declaration
uses that frozen digest, and only when the actual main+provenance artifact recomputes to
the same digest. The independent stamp verifier repeats the check against the
**release-v4 contract recorded by the manifest**. A mutable JSON declaration therefore
cannot redefine the adoption artifact, even by supplying a digest matching some other
self-consistent artifact under the same version directory.

A later release uses the non-baseline form:

```json
{
  "schema": 1,
  "tfVersion": "<candidate>",
  "predecessorVersion": "<previous certified release>",
  "predecessorDigest": "sha256:<64 hex>",
  "expectedChanges": [
    "main:feature.tf",
    "provenance:feature.tf"
  ]
}
```

`expectedChanges` is exact, sorted and duplicate-free. Wildcards, arbitrary paths and
unqualified feature names are invalid. Issue-specific tests still own the semantic
correctness of an intended feature change; this gate prevents unrelated serialized data,
loader semantics or ordering changes from being certified accidentally.

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

The recorded commit must identify the source and executable code that actually ran.
Before any release gate, `release_check.py` asks Git for staged or unstaged changes to the
**protected tracked tree** and refuses to certify if there are any. The protected tree is
the repository except the mutable release-output paths `tf/**`, `tf-provenance/**` and
`reports/**`: build/certification intentionally rewrite those outputs, and their identity
is enforced separately by the module-aware artifact digest and certification evidence.
A change under `programs/`, `docs/`, workflow/configuration files, the source corpus, or
other tracked input/code paths is still a hard failure.

Untracked and ignored files are excluded from this Git cleanliness check because
transient `refs/`, reports and caches are expected during a release; the release inputs
that affect certification are bound separately by SHA-256 where required.

The commit identity is taken from `TLHDIG_CODE_COMMIT`, then `GITHUB_SHA`, then
`git rev-parse HEAD`, and must be a full 40-character SHA. Any environment-provided SHA
must equal the checkout's `HEAD` whenever `HEAD` is readable; a syntactically valid but
mismatched override is rejected rather than recorded as the code that ran. The resolver
can fall back to environment metadata if `rev-parse` itself is unavailable, but the full
release command still requires a usable Git checkout because the protected-tree status
check is a separate hard prerequisite.

`release-v4` repeats this protection as the final required gate, after predecessor and
external validation. The protected tracked tree must still match the recorded commit
**and** `git rev-parse HEAD` must still equal the commit recorded when certification
started. This closes both ways a validator could otherwise change executable/source code
during the run: modifying protected tracked files in place, or checking out/resetting to
a different clean commit. Changes to TF/provenance/report outputs are allowed at this
Git layer only because their bytes/layout are checked by their dedicated release
identities before certification can succeed.

## Historical certification

`tf/0.2.0` predates full release certification and carries a digest-bound census-era
`BUILD-COMPLETE`. `python programs/check_stamp.py` can still validate those historical
bytes with the original digest algorithm. `python programs/check_stamp.py --require-full`
rejects the legacy stamp, which is intentional: published historical artifacts are
immutable and are not rewritten merely to upgrade certification metadata.

Full `release-v3` manifests are also historical after adoption of v4, but remain full
certifications. The verifier selects the immutable v3 gate/input/fidelity contract from
the manifest's recorded policy name rather than requiring every historical manifest to
claim the latest policy. This compatibility does not accept self-declared or unknown
profiles. Release-v4-specific baseline identity likewise lives in the v4 policy contract,
so later policy changes cannot silently alter historical v4 verification semantics.

## Failure semantics

Before any release attempt, the certifier removes a stale `BUILD-COMPLETE` and successful
manifest. A required gate succeeds only with explicit status `passed` and return code 0.
An explicit skip is never a release pass, even if an ordinary-CI command would return 0.

The module-aware TF digest is computed before the first gate and after the last. If any
`.tf` file changes bytes, filename or module membership during validation, certification
fails and no valid stamp remains. The same before/after rule applies to the bound corpus
manifest, repair manifest, external sign-reference lock and release-delta declaration.
The final `code-tree-stable` gate independently rejects protected-tree drift or a
changed/unreadable Git HEAD.

A failed attempt is written to `reports/release-certification.json`; it is diagnostic only
and cannot be used by `publish_dataset.sh`.
