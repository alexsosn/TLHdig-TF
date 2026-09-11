# Plan: byte-reproducible Text-Fabric output (#122)

Status: frozen after `docs/research-reproducible-tf-bytes.md`.

Sequence: research → plan → deterministic RED → minimal normalization → unit GREEN → first hosted clean rebuild/full validation → second independent exact-code clean rebuild → per-file/output-digest equality check → exact-head ordinary CI → logically independent adversarial review → guarded merge.

## 1. Contract

For the same pinned source snapshot, converter/validation code, declared build inputs, and dependency version, independent clean builds must produce byte-identical final `tf/<TF_VERSION>` and `tf-provenance/<TF_VERSION>` artifact trees, excluding `BUILD-MANIFEST.json` itself.

Corpus semantics, TF schema/features, app formats, and public load paths must not change.

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

1. two otherwise identical synthetic TF files differing only in `@dateWritten` differ byte-for-byte before normalization;
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

## 5. Minimal implementation

Use standard-library byte/path operations; no new dependency and no generic metadata-policy framework.

A minimal approach may scan `read_bytes()` line-by-line while retaining each line's terminator, determine the header boundary, locate the unique `@dateWritten=` header line, and write the concatenation of all original byte slices except that line. Use atomic replacement if practical so a failure cannot truncate a feature file.

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

Both runs must:

- complete successfully;
- pass every current substantive validation gate;
- emit the same output file-key set;
- emit the same SHA-256 for every generated main/provenance file;
- emit the same aggregate `outputs.digest`.

Do not infer reproducibility from aggregate equality alone: compare the per-file map too.

If any byte differs, stop, identify the smallest differing files, add a focused RED for the new nondeterministic source, and repeat both builds after the fix.

## 8. Final committed artifact/manifest

After dual-build equality is proven, commit/ship the exact generated bytes and a manifest produced by validation of those bytes. Ordinary CI must pass `check_build_manifest.py` on the exact final head.

The manifest remains build/provenance metadata, not a recursive release certificate.

## 9. Documentation

Update active build/release documentation to state:

- Text-Fabric's wall-clock `@dateWritten` is removed from generated `.tf` files for reproducibility;
- `@writtenBy=Text-Fabric` remains;
- the operation removes volatile generated metadata, not corpus content;
- reproducibility is demonstrated by two independent clean builds plus per-file equality, while semantic correctness remains enforced by the normal corpus/app gates.

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
- aggregate equality was accepted without per-file equality;
- committed manifest describes different bytes than the final artifact.

Any blocker requires a regression, correction, full GREEN, repeat hosted proofs when bytes are affected, and fresh exact-head review.

## 11. Merge gate

Before merge:

- exact production code used for both clean-build proofs is identifiable;
- both builds are byte-identical file-by-file;
- all substantive validation gates pass on both;
- committed artifact and manifest agree;
- exact-final-head ordinary CI is GREEN;
- independent review has no unresolved blocker.

## Non-goals

- historical generated snapshot retention;
- recursive release certification;
- TF schema/node-number changes;
- general dependency locking (#106);
- aesthetic metadata normalization;
- preserving a genuine wall-clock timestamp in every generated feature file.
