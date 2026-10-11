# Research: byte-reproducible Text-Fabric output (#122)

## Scope

This ticket is about the **actual generated file bytes**: for identical source/code/dependency inputs, independent clean builds should produce byte-identical current `tf/<TF_VERSION>` and `tf-provenance/<TF_VERSION>` trees (apart from `BUILD-MANIFEST.json`, which records the build).

It does not reintroduce historical release certification, retain historical generated versions, change corpus semantics/schema, or solve dependency locking.

## What the current manifest does — important correction

Current `programs/tlhdig/build_manifest.py` uses output identity algorithm `tlhdig-current-tree-v2`. For `.tf` files its `_output_sha256()` deliberately **skips a header line beginning `@dateWritten=`** before hashing. Non-`.tf` outputs are hashed byte-for-byte.

So the current build manifest is a canonicalized/logical output-integrity identity, not proof that two `.tf` files are byte-identical on disk. Two builds that differ only in Text-Fabric's wall-clock `@dateWritten` can legitimately have the same manifest file hashes and the same aggregate `outputs.digest`.

This canonicalization is useful and already solves the narrower “do timestamps make current-output identity stale?” problem. It does **not** solve this ticket's stronger file-byte reproducibility goal. Raw-byte equality therefore needs an independent proof; `BUILD-MANIFEST.json` must not be used as the sole evidence for #122.

## Original observed drift

During the clean-current-output work (#118/#119), hosted clean rebuilds showed that unchanged corpus semantics could nevertheless produce changed `.tf` bytes. That observation motivated #122. Some earlier issue/research wording attributed the changed *manifest* identity directly to the timestamp; that wording is obsolete after output-identity v2 began canonicalizing `@dateWritten`.

The surviving, measurable defect is simpler: freshly written `.tf` files still contain wall-clock metadata, so their raw bytes differ across otherwise identical saves.

## Upstream Text-Fabric writer

Text-Fabric 13.1.0 was inspected in `annotation/text-fabric`, `tf/core/data.py` at commit `0c45c386916cb52be84098796ec27ce97e5bf9fc`.

For each feature file the writer emits the feature/config/edge marker, caller metadata in sorted-key order, and then unconditionally writes:

```text
@writtenBy=Text-Fabric
@dateWritten=<current UTC wall-clock time>
```

`dateWritten` is constructed from `utcnow()` at save time. It is not supplied by caller metadata and there is no normal writer parameter for a deterministic value. This guarantees raw-byte drift when the same logical feature is saved at different times.

The inspected writer is otherwise ordered at the relevant serialization boundary:

- metadata keys are sorted;
- node and edge source ids are sorted;
- ranged node output is sorted by range endpoints;
- valued edge groups are sorted;
- WARP tuple data is reconstructed into node-keyed data and follows the same ordered writer.

That does not prove the whole TLHdig-TF build deterministic; it only establishes one necessary source of raw-byte nondeterminism.

## Existing TLHdig-TF deterministic boundaries

The project already reduces common ordering drift:

- `paths.corpus_files()` sorts source XML paths by NFC-normalized lowercase path;
- `compact.py` deterministically rewrites node-feature bodies;
- `build_manifest.py` records a closed-world current output identity and already canonicalizes only Text-Fabric's volatile header timestamp for `.tf` identity.

The compactor preserves the upstream header verbatim and applies only to node features. Edge/config/WARP files therefore keep their raw `@dateWritten` too.

## Candidate designs

### A. Remove generated `@dateWritten` after save — preferred

At TLHdig-TF's generated-output boundary, remove exactly the Text-Fabric-generated header `@dateWritten=...` line from every generated `.tf` file kind.

Keep `@writtenBy=Text-Fabric`; it is deterministic and true. Do not replace the timestamp with a deterministic pseudo-time: that would look like a wall-clock fact while no longer being one.

This is a narrow artifact-byte normalization. It is not corpus transformation and not a new metadata policy framework.

### B. Keep relying on manifest canonicalization — insufficient for this ticket

This is effectively the current state. Output identity is already stable with respect to `dateWritten`, but the files themselves remain volatile. Git diffs, raw-file caches, direct file checksums, and strict rebuild-byte comparisons remain noisy.

If the project decided that logical/canonicalized identity was sufficient, #122 could instead be closed as unnecessary. As long as the stated requirement is byte-reproducible artifacts, canonicalized manifest hashing alone cannot satisfy it.

### C. Patch/fork Text-Fabric — rejected

Patching site-packages or carrying a fork solely for timestamp policy adds disproportionate maintenance. TLHdig-TF already owns a post-save rewrite boundary.

## Natural implementation boundary

A focused helper near `compact.py` can operate on all generated regular `*.tf` files after Text-Fabric save and before final validation/shipping. It must not be hidden inside `compact_file()`, which intentionally handles only node features.

Candidate order:

1. preflight inputs;
2. reset current generated trees;
3. Text-Fabric conversion writes main output;
4. remove volatile generated metadata from every main `.tf`;
5. compact node features;
6. split/move provenance features and regenerate provenance README;
7. defensively normalize final provenance `.tf` files;
8. validate final output and write the ordinary build manifest.

## Byte-preservation constraint from adversarial review

The first plan suggested decoded UTF-8 text rewriting. That is unsafe for a byte-reproducibility ticket: text-mode newline translation can change CRLF to LF, and split/write code can manufacture or remove a final newline.

The true contract is: remove the exact byte slice occupied by one header `@dateWritten=...` line and preserve **every other byte**. Tests therefore need LF, CRLF, and EOF/no-final-newline cases. Byte-oriented parsing (or an equivalently proven byte-preserving implementation) is required.

## Compatibility questions

Removing `dateWritten` should not affect corpus data, but implementation must prove:

- Text-Fabric can load normalized synthetic files;
- app/config/corpus gates see no semantic change;
- Context-Fabric/Agora consumers do not require `dateWritten`;
- no TLHdig-TF runtime code requires the field.

Current repository behavior already treats `dateWritten` as ignorable for current-output identity, which is additional evidence that it is generated bookkeeping rather than corpus semantics.

## What remains unproven

Removing `dateWritten` is necessary for raw byte reproducibility but may not be sufficient. Converter/environment nondeterminism elsewhere must be detected empirically.

The decisive experiment is **two independent clean builds of one exact production-code commit with the same source/dependency/configuration inputs, followed by raw SHA-256 comparison of every final generated file** (excluding `BUILD-MANIFEST.json` and Text-Fabric's compiled cache directory).

The current manifest's `.tf` hashes and aggregate `outputs.digest` are not sufficient evidence because output-identity v2 intentionally omits `@dateWritten` from those hashes. They remain a separate integrity/semantic-current-build check.

## TDD implications

RED before production code must cover at least:

1. otherwise-identical `.tf` files differing only in `@dateWritten` have different **raw** SHA-256 values;
2. node and non-node TF shapes are covered;
3. normalization removes exactly one header timestamp and preserves all other bytes;
4. LF and CRLF are preserved;
5. final-newline/no-final-newline shape outside the removed line is preserved;
6. no-timestamp files are byte-identical and preferably not rewritten;
7. duplicate/malformed timestamp headers fail closed without modification;
8. a body literal `@dateWritten=` is untouched;
9. symlinked `.tf` files are rejected without touching their targets;
10. normalized synthetic TF loads;
11. build ordering covers both main and final provenance output.

After unit GREEN, run two independent exact-code hosted clean builds and compare a separately generated raw per-file digest map. Any differing file requires investigation and a focused regression before broadening normalization.

## Relationship to #115/#118

- #115 keeps only one current pre-alpha artifact and removes obsolete recursive certification semantics.
- #118 ensures a clean build cannot inherit stale generated files.
- #122, if retained, adds the stronger property that two clean builds also reproduce the same raw output bytes.

These do not require historical artifact retention.

## Conclusion

Upstream Text-Fabric's wall-clock `@dateWritten` is a confirmed raw-byte nondeterminism source. Current output-identity v2 already canonicalizes it for manifest hashing, so #122 must be evaluated and tested explicitly as a **raw artifact-byte** requirement, not as a manifest-integrity repair. If we keep that requirement, the smallest implementation is to remove only the generated timestamp line byte-preservingly and then prove sufficiency with two exact-code clean builds compared using raw per-file SHA-256 values.
