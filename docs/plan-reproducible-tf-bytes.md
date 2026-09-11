# Plan: byte-reproducible Text-Fabric output (#122)

Status: frozen after `docs/research-reproducible-tf-bytes.md`.

Sequence: research → plan → deterministic RED → minimal normalization → unit GREEN → first hosted clean rebuild/full validation → second independent exact-code clean rebuild → output-digest equality check → exact-head ordinary CI → logically independent adversarial review → guarded merge.

## 1. User-visible/build contract

For the same pinned source snapshot, TLHdig-TF converter/validation code, declared build inputs, and dependency version, independent clean builds must produce byte-identical final `tf/<TF_VERSION>` and `tf-provenance/<TF_VERSION>` artifact trees (excluding `BUILD-MANIFEST.json`, which records the validated output).

The generated corpus semantics, TF node/edge schema, feature values, app formats, and public load paths do not change.

## 2. Normalization contract

Add a narrow post-save helper in `programs/tlhdig/compact.py` or a similarly focused generated-output module. Preferred public shape:

```python
def normalize_generated_metadata(path: Path) -> bool:
    ...


def normalize_dir(directory: Path) -> list[str]:
    ...
```

Exact names may vary; behavior is frozen:

- operate only on regular `*.tf` files supplied by the caller;
- never follow a symlink;
- fail closed if an encountered `*.tf` path is a symlink or unexpected non-regular filesystem object;
- remove exactly the Text-Fabric-generated `@dateWritten=...` header line;
- preserve `@writtenBy=Text-Fabric`;
- preserve every other header line, blank-line separator, and body byte/text exactly;
- be idempotent: a second normalization changes nothing;
- do not manufacture a deterministic-looking timestamp;
- do not canonicalize arbitrary metadata or data bodies in this helper.

A file with no `@dateWritten` is already normalized and should be left byte-identical. Multiple `@dateWritten` lines or a `@dateWritten` occurrence outside the header should fail closed rather than silently guessing.

## 3. Build orchestration

Keep Text-Fabric as the writer. Do not monkey-patch installed dependency code.

Required build order after #118 lands:

1. preflight required inputs/source identity;
2. reset exact current generated main/provenance trees;
3. run `convert.build()` into current main output;
4. normalize generated metadata across all main `*.tf` files;
5. compact node features using existing deterministic compaction;
6. split/move provenance features and regenerate provenance README;
7. defensively normalize final provenance `*.tf` files (idempotent when already normalized);
8. print build summary and leave complete validation to `validate_current.py`.

The second provenance normalization is intentionally cheap and closes the final-tree boundary if future code creates a provenance feature after the initial normalization.

No generated files other than `.tf` feature/config files are affected.

## 4. Deterministic RED commit

Before production code, add tests only. RED must prove the absent contract with small fixtures and no full corpus dependency.

At minimum:

1. two otherwise identical synthetic TF files differing only in `@dateWritten` have different bytes/digests under current behavior;
2. expected normalization removes the volatile line while preserving `@writtenBy` and all caller metadata/body bytes;
3. cover a node feature and at least one non-node shape (edge/config/WARP-like header/body) so implementation cannot hide inside `compact_file()`;
4. normalization is idempotent;
5. body text containing the literal string `@dateWritten=` is not modified;
6. duplicate header `@dateWritten` entries fail closed;
7. symlinked `.tf` file fails closed without modifying its target;
8. Text-Fabric can load a normalized synthetic dataset/feature where practical;
9. build orchestration test proves normalization happens after conversion and covers provenance final output.

The RED commit contains tests/docs only. Existing tests remain green; only new normalization expectations fail.

## 5. Minimal implementation

Use standard-library text/path operations. No new dependency.

Parsing need only understand the Text-Fabric header boundary: metadata precedes the first blank line. Work on decoded UTF-8 because `.tf` files are UTF-8 text and current build/compaction already does so.

Do not generalize this into a metadata policy framework. The confirmed volatile field is `dateWritten`; any additional nondeterminism found by dual hosted builds gets a separate focused regression before expanding the normalization.

## 6. Unit/integration GREEN gate

Require:

- full `python -m pytest programs/tests -q`;
- normalization tests GREEN;
- existing compaction tests GREEN;
- existing build-clean-output tests from #118 GREEN;
- current build-manifest tests GREEN;
- no change to the canonical 16 validation gate list.

Changing `compact.py`/build code invalidates the current code identity in `BUILD-MANIFEST.json`; do not hand-edit manifest hashes.

## 7. First hosted clean build

On production-code head:

- run the normal clean Dataset workflow;
- require build success;
- require all 16 `validate_current.py` gates;
- capture the generated `BUILD-MANIFEST.json` as evidence;
- record its closed-world output file set and `outputs.digest`.

Do not commit the manifest yet as final proof until the second independent build agrees.

## 8. Second independent exact-code build

Without changing production code, source inputs, dependencies, or build configuration, run a second clean Dataset build from the same exact production-code commit.

Acceptance is strict:

- same output file-key set;
- same SHA-256 for every generated main/provenance file;
- same aggregate `outputs.digest`;
- all 16 validation gates GREEN again.

`codeCommit`/workflow-run metadata may differ only if a non-code evidence/workflow commit is intentionally used; preferred execution is two runs of the exact same commit so even provenance is straightforward.

If any generated output differs, stop. Diff the smallest differing files, add a focused RED for the newly discovered source of nondeterminism, amend research/plan only if the design boundary materially changes, then fix and repeat both hosted builds.

## 9. Committed manifest

After two-build equality is proven, commit a manifest produced by validation of the exact generated bytes being committed/shipped. Ordinary CI must then pass `check_build_manifest.py` on the exact final branch head.

Do not treat output-digest equality as a replacement for manifest verification; both are required for this ticket.

## 10. Documentation

Update active build/release documentation to state:

- Text-Fabric's wall-clock `@dateWritten` is removed from generated `.tf` files for reproducibility;
- `@writtenBy=Text-Fabric` remains;
- this is generated-metadata normalization, not corpus-content transformation;
- byte reproducibility is checked by independent clean builds, while semantic correctness remains enforced by the existing corpus/app gates.

Historical research documents need not be rewritten.

## 11. Independent adversarial review

Review the exact final diff independently and try to show:

- normalization can alter corpus body data;
- normalization strips caller metadata beyond `dateWritten`;
- duplicate/malformed headers are silently accepted;
- symlinks are followed;
- config/edge/WARP files remain volatile because only node features are normalized;
- provenance features escape normalization;
- compaction order changes semantics;
- build order normalizes stale previous files rather than fresh converter output;
- two hosted builds used different production code or dependency inputs;
- output digest equality was inferred without per-file equality;
- manifest describes different bytes than those committed.

Any blocker requires a focused regression test before correction, full GREEN, both hosted rebuild proofs where output bytes are affected, and a fresh exact-head review.

## 12. Merge gate

Before merge:

- exact production code used for the two clean-build proof is identifiable;
- two independent hosted clean builds are byte-identical;
- all substantive validation gates pass on both;
- committed current artifact and manifest agree;
- exact-final-head ordinary CI is GREEN;
- no blocking adversarial finding remains.

## Non-goals

- historical TF snapshot retention;
- recursive release certification;
- changing TF schema/features/node numbering;
- dependency locking beyond the existing declared environment (#106);
- normalizing arbitrary metadata for aesthetics;
- preserving a real wall-clock build timestamp inside every generated feature file.
