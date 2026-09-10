# Plan: robust generated feature-file discovery

Issue: #110
Research: `docs/research-featuredocs-cache-dirs.md`

This plan is frozen before RED tests and production changes.

## Contract

Generated feature documentation inventories shipped Text-Fabric **feature files**, not arbitrary filesystem entries whose names happen to end in `.tf`.

A candidate under a core/provenance module is handled as follows:

- non-symlink regular `*.tf` file → parse exactly as today;
- directory matching `*.tf` (including runtime `.tf/`) → ignore;
- symlink matching `*.tf` → fail closed with `FeatureDocsError`;
- malformed regular feature file → retain current `FeatureDocsError` behavior.

Do not recursively inspect directories or compiled TF cache contents.

## Implementation

Add one private helper in `programs/tlhdig/featuredocs.py`, conceptually `_feature_paths(directory)`, that:

1. iterates `directory.glob("*.tf")` in deterministic basename order;
2. rejects symlinks explicitly before following file type;
3. yields only regular files;
4. skips directories/other non-file entries.

Use the helper for both core and optional provenance discovery loops. Do not catch `IsADirectoryError` in `read_header()`; `read_header()` should continue to mean "parse this intended feature file" and fail on invalid input.

No generated Markdown representation, semantic description, ordering, module name, version, app configuration or TF artifact changes are part of this ticket.

## RED gate

Before production changes add a dedicated test module that proves current behavior is wrong:

- valid core/provenance feature files plus `.tf/` and `scratch.tf/` directories should produce exactly the valid feature names;
- a `*.tf` symlink should raise `FeatureDocsError` where symlinks are available;
- malformed regular `.tf` input should still raise;
- stable feature ordering remains deterministic.

Hosted CI must show the new cache-directory/symlink contract failing for the intended reason while unrelated tests remain green.

## GREEN gate

Implement only the centralized path-kind filter. Run:

- targeted #110 tests;
- full `programs/tests` suite;
- ordinary repository CI.

This utility change does not allocate or rebuild a TF version.

## Independent adversarial review

On the exact final head challenge:

- `.tf/` runtime cache and arbitrary suffix-matching directories;
- symlink-to-file and broken symlink behavior;
- accidental silent acceptance of malformed regular files;
- core/provenance parity;
- deterministic ordering;
- accidental recursion into cache contents;
- scope creep into generated-doc semantics or release artifacts.

Any blocker restarts RED/fix/tests/fresh review.

## Acceptance

A loaded Text-Fabric corpus may have runtime `.tf/` cache directories beside feature files without breaking generated feature documentation, and generated docs remain derived solely from explicit shipped regular feature files.