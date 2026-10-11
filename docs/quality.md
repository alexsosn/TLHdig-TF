# Quality, validation and limitations

TLHdig-TF has executable checks for source identity, repairs, textual conservation, morphology, structure, cuneiform, manuscript relations, provenance, app configuration and generated-output identity. These checks make specific invariants reproducible; they do not turn an unfinished pre-alpha corpus into a fully validated critical edition.

## Current-build validation

`programs/validate_current.py` runs the complete validation suite against one unchanged current artifact. Only after every required gate succeeds does it write `BUILD-MANIFEST.json`.

The suite currently covers source/corpus identity, repair applicability, sign round-trip, morphology, structural checks, sign language, manuscript joins, source-span recovery, marker conservation, source-tag inventory, provenance splitting, cuneiform alignment, locked external sign-reference diagnostics, app integrity and census generation.

The exact gate list is code, not this prose page; see [`RELEASE.md`](RELEASE.md).

## What a green gate means

A green gate means its stated invariant holds for the tested current artifact. It should not be generalized beyond that contract. Examples:

- an exact build ledger proves every pinned source file is either converted or explicitly excluded; it does not make the exclusions disappear;
- a structure regression baseline can prevent further loss while a known existing deficit remains;
- cuneiform coverage can increase without implying equal confidence for every alignment method;
- source-byte provenance can be exact for supported spans while boundary-moving repairs remain philologically uncertain.

## Maintained limitations

[`../KNOWN-ISSUES.md`](../KNOWN-ISSUES.md) is the current-state register. Important classes include:

- unresolved crossing-tag and balanced-but-lossy XML structures;
- explicitly excluded source files;
- lines without ordinary section addresses and duplicate `docid` values;
- raw-only source constructs that have not been assigned derived semantics;
- incomplete morphology cases;
- partial and heterogeneous-confidence sign-level cuneiform alignment.

Generated reports are authoritative for current counts. If a prose number and a generated report disagree, use the generated report and treat the prose as stale.

## Research use

For analyses sensitive to one of these limitations, state the filtering rule and inspect the corresponding report. Do not interpret a missing feature value as linguistic absence until the feature's coverage and generation rules support that inference.

TLHdig remains the authoritative scholarly interface for individual-text consultation; TLHdig-TF's validation is aimed at making corpus-scale computation auditable.
