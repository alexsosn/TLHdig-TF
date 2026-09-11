# Plan: byte-reproducible Text-Fabric output (#122)

Status: frozen after `docs/research-reproducible-tf-bytes.md`.

Sequence: research → plan → deterministic RED → minimal normalization → unit GREEN → first hosted clean rebuild/full validation → second independent exact-code clean rebuild → **raw** per-file SHA equality → manifest/current-build verification → exact-head ordinary CI → logically independent adversarial review → guarded merge.

## 1. Contract

For the same pinned source snapshot, converter/validation code, declared build inputs, and dependency version, independent clean builds must produce byte-identical final `tf/<TF_VERSION>` and `tf-provenance/<TF_VERSION>` artifact trees, excluding `BUILD-MANIFEST.json` itself and Text-Fabric's compiled cache directory.

Corpus semantics, TF schema/features, app formats, and public load paths must not change.

The existing `tlhdig-current-tree-v2` manifest identity is **not** the byte-equality oracle for this ticket: `_output_sha256()` intentionally skips a header `@dateWritten=` line in `.tf` files. #122 therefore requires a separate raw-file digest proof.

## 2. Normalization contract

Add a narrow post-save helper in `programs/tlhdig/compact.py` or an equally focused generated-output module. Exact API may vary, but behavior is fixed:

- operate only on caller-supplied regular `*.tf` files;
- never follow symlinks; reject symlink/non-regular entries;
- identify the Text-Fabric header as bytes up to the first blank-line separator;
- remove exactly one header line beginning `@dateWritten=`;
- preserve `@writtenBy=Text-Fabric` and every other byte exactly;
- preserve the file's existing LF/CRLF convention and final-newline/no-final-newline shape outside the removed line;
- do not rewrite the file at all when no `@dateWritten` header exists;
- fail closed on duplicate header `@dateWritten` lines or a malformed ambiguous header;
- do not touch a literal `@dateWritten=` sequence in the body;
- be idempotent;
- never manufacture a deterministic-looking timestamp or canonicalize unrelated metadata/body content.

Byte preservation is the contract. Decoding UTF-8 for validation is allowed, but a decoded-text read/split/write round trip is not acceptable unless tests prove byte identity for all nonremoved content, including CRLF.

## 3. Build ordering

Keep Text-Fabric as the writer; do not patch site-packages.

Required order:

1. preflight source/required inputs;
2. reset exact current generated trees;
3. `convert.build()` writes main output;
4. normalize all main `.tf` files;
5. run deterministic node-feature compaction;
6. split/move provenance features and regenerate provenance README;
7. defensively normalize final provenance `.tf` files;
8. validate/hash the final output through the existing current-build path.

No non-`.tf` generated file is normalized by this ticket.

## 4. RED gate

Before production code, commit tests only. Existing tests must remain green and the new expectations must fail for the intended missing behavior.

Required cases:

1. two otherwise identical synthetic TF files differing only in `@dateWritten` have different **raw SHA-256** values under current behavior, while current manifest canonicalization may treat them as identical;
2. expected normalization removes only the volatile header line while preserving `@writtenBy`, arbitrary caller metadata, blank separator and body bytes;
3. cover node and non-node shapes (edge/config/WARP-like) so implementation cannot hide in `compact_file()`;
4. separate LF and CRLF fixtures prove every nonremoved byte is unchanged;
5. include a no-final-newline fixture so the helper cannot add one accidentally;
6. a file without `@dateWritten` is left byte-identical and ideally not rewritten;
7. normalization is idempotent;
8. body text containing literal `@dateWritten=` is unchanged;
9. duplicate header `@dateWritten` lines fail closed without modifying the file;
10. symlinked `.tf` input fails closed without modifying the target;
11. Text-Fabric can load a normalized synthetic dataset/feature where practical;
12. build orchestration test proves normalization occurs after conversion and covers final provenance output.

The RED should explicitly demonstrate why `BUILD-MANIFEST.json`/`outputs.digest` cannot stand in for raw-byte equality: output-identity v2 canonicalizes the timestamp by design.

## 5. Minimal implementation

Use standard-library byte/path operations; no new dependency and no generic metadata-policy framework.

A minimal approach may scan `read_bytes()` while retaining exact line terminators, determine the header boundary, locate the unique `@dateWritten=` header line, and write the concatenation of all original byte slices except that line. Use atomic replacement if practical so a failure cannot truncate a feature file.

Do **not** change `build_manifest._output_sha256()` merely to make #122's proof easier. Its existing canonicalization is a separate current-output identity contract and can remain backward-compatible.

Any additional nondeterminism discovered by dual hosted builds gets a focused RED before this normalization contract broadens.

## 6. Unit/integration GREEN

Require:

- full `python -m pytest programs/tests -q`;
- all normalization tests GREEN;
- existing compaction/build-clean-output/build-manifest tests GREEN;
- no semantic-output change apart from the removed volatile header;
- no change to the substantive validation gate set.

Changing build/compact code invalidates current manifest code identity; regenerate through the canonical validator, never hand-edit hashes.

## 7. Two independent hosted clean builds

On one exact production-code commit, run two independent clean Dataset builds with the same source/dependency/configuration inputs.

For each final build, independently enumerate the same closed-world generated files that are intended to ship, excluding `BUILD-MANIFEST.json` and Text-Fabric's compiled `.tf/` cache directory, and compute **ordinary raw SHA-256 over the actual file bytes**. Do not call `build_manifest._output_sha256()` for this proof.

Acceptance is strict:

- both builds complete successfully;
- both pass every current substantive validation gate;
- the raw output file-key sets are identical;
- raw SHA-256 is identical for every corresponding generated file;
- current `BUILD-MANIFEST.json` verification passes separately on both builds;
- current canonical `outputs.digest` equality may be recorded as corroboration, but it is not the byte-reproducibility proof.

If any raw byte differs, stop, identify the smallest differing files, add a focused RED for the new nondeterministic source, and repeat both builds after the fix.

Persist or emit the raw digest maps as CI evidence so review can verify exact per-file equality rather than relying on a prose claim.

## 8. Final committed artifact/manifest

After dual-build raw equality is proven, commit/ship the exact generated bytes and a manifest produced by validation of those bytes. Ordinary CI must pass `check_build_manifest.py` on the exact final head.

The manifest remains build/provenance metadata with its intentional timestamp canonicalization, not a recursive release certificate and not the raw-byte proof.

## 9. Documentation

Update active build/release documentation to state:

- Text-Fabric's wall-clock `@dateWritten` is removed from generated `.tf` files for raw-byte reproducibility;
- `@writtenBy=Text-Fabric` remains;
- the operation removes volatile generated metadata, not corpus content;
- raw-byte reproducibility is demonstrated by two independent clean builds plus ordinary per-file SHA-256 equality;
- `BUILD-MANIFEST.json` separately enforces current canonical output/build integrity and intentionally ignores `@dateWritten` in `.tf` hashing.

## 10. Independent adversarial review

On the exact final head, attempt to show that:

- body bytes can be changed accidentally;
- LF/CRLF or final-newline state is normalized unintentionally;
- caller metadata beyond `dateWritten` can be stripped/reordered;
- duplicate/malformed headers are silently guessed through;
- body `@dateWritten=` text is removed;
- symlinks are followed;
- config/edge/WARP or provenance files remain volatile;
- compaction/normalization ordering changes semantics;
- stale previous output is normalized instead of fresh converter output;
- the two hosted builds used different production code or dependency inputs;
- the “raw” comparison accidentally reused canonicalized manifest hashes;
- some shipped file class was omitted from raw enumeration;
- aggregate digest equality was accepted without raw per-file equality;
- committed manifest describes different final bytes/inputs than the shipped artifact.

Any blocker requires a regression, correction, full GREEN, repeat hosted proofs when bytes are affected, and fresh exact-head review.

## 11. Merge gate

Before merge:

- exact production code used for both clean-build proofs is identifiable;
- both builds are raw-byte-identical file-by-file under an independently emitted digest map;
- all substantive validation gates pass on both;
- committed artifact and current build manifest agree under the existing manifest contract;
- exact-final-head ordinary CI is GREEN;
- independent review has no unresolved blocker.

## Non-goals

- historical generated snapshot retention;
- recursive release certification;
- TF schema/node-number changes;
- general dependency locking (#106);
- aesthetic metadata normalization;
- changing the current manifest's timestamp-canonicalization semantics solely for this ticket;
- preserving a genuine wall-clock timestamp in every generated feature file.
