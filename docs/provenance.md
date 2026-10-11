# Provenance and reproducibility

TLHdig-TF keeps source identity, conversion logic and generated output separate enough to audit where a graph value came from.

## Pinned source

The repository contains a pinned TLHdig source snapshot. `programs/corpus.sha256` binds the expected source-file identities, and build validation checks that snapshot before treating generated output as current.

The source dataset and the TF conversion have separate version identities. A TF schema/build change does not imply a different upstream TLHdig source release.

## Repairs

Malformed source XML is not silently rewritten. Byte-pinned repair instructions in the repair manifest state exactly which source bytes are expected and which transformation is applied. Repair verification fails when its byte preconditions no longer match.

Some boundary-moving repairs remain philologically unresolved. Provenance can show what transformation was applied; it cannot turn an uncertain editorial boundary into certainty. See [`../reports/crossing-tag-review.md`](../reports/crossing-tag-review.md).

## Main graph and optional provenance module

Ordinary corpus semantics live in the main TF artifact. Source-heavy recovery features are split into the optional `tf-provenance/<TF_VERSION>` module so normal loading does not automatically pay the memory cost of byte-level provenance.

The current optional module exposes source-oriented features such as `srcxml` and `src_span` where supported. It is not loaded merely by reading the main graph.

Document-header recovery is still incomplete in the current model; #57/#58 own the planned whole-header provenance work and retirement of the misleading `docid_raw` feature. Until that lands, do not claim that every header byte can be recovered from the TF graph.

## Current build manifest

After a clean build passes the complete current validation suite, `tf/<TF_VERSION>/BUILD-MANIFEST.json` binds:

- source/policy input hashes;
- executable/config identity relevant to conversion and validation;
- closed-world identity of the main and provenance output trees, with only Text-Fabric's volatile `@dateWritten` metadata canonicalized by output-identity v2;
- the validated source and TF versions;
- the names of the validation gates that succeeded.

`BUILD-MANIFEST.json` is current-build integrity/provenance metadata. It is not a recursive historical certification authority and does not promise compatibility with old pre-alpha generated snapshots. The output identity is deliberately not a raw byte-for-byte hash of the `@dateWritten` header line: that timestamp is canonicalized so semantically identical clean rebuilds can be compared, while every other tracked output path/content remains in the closed-world identity.

See [`RELEASE.md`](RELEASE.md) for the exact build → validate → manifest workflow.

## Reproducible reporting

For a research result, record at least the TF/repository revision, relevant feature filters and any exclusion/alignment policy used. When source-repair or provenance details affect the argument, cite the corresponding report or source record rather than relying only on a TF node number.
