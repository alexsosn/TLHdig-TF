# Research: generated feature docs must distinguish feature files from TF cache directories

Issue: #110
Date: 2026-09-10

This is a research-only gate. No production code is changed here.

## Observed failure

Header-provenance release integration exposed a generic bug in `tlhdig.featuredocs.discover_features()` before TF 0.5.0 materialization. The current implementation enumerates both core and optional provenance locations with `Path.glob("*.tf")` and immediately passes every match to `read_header()`.

A deterministic regression fixture creates legitimate `lemma.tf` / `srcxml.tf` feature files alongside directories named `.tf` and `scratch.tf`. Python's glob result contains those directories as path matches, and `read_header()` then attempts `path.open()`, producing `IsADirectoryError` wrapped as `FeatureDocsError`.

Hosted evidence from the #66 integration branch: CI run `34485745770`, job `102899442336` passed 616 tests, skipped 4 and failed exactly two tests. One was the cache-directory regression; the other was the deliberately absent TF 0.5.0 artifact. The cache error therefore reproduces independently of the new provenance semantics.

## Text-Fabric cache semantics

The repository pins Text-Fabric 13.1.0. Text-Fabric's own documentation describes compiled cache data under a directory named `.tf` inside a TF version directory and documents manually clearing it by deleting that `.tf` directory. Existing Text-Fabric examples likewise show paths such as `.../tf/<version>/.tf/...`.

Therefore a `.tf` directory next to `*.tf` feature files is a normal runtime state of a loaded corpus, not malformed corpus data.

The generated feature reference is explicitly sourced from shipped **feature-file headers**, not runtime caches. Cache contents must never influence feature inventory or semantics.

## File-kind boundary

A Text-Fabric feature in this repository is represented by a regular file whose basename ends in `.tf`. Directories with the same suffix are not features.

The safest inventory boundary is:

- ignore directory entries even when their names match `*.tf`;
- continue to parse matching regular files exactly as today, including failing on malformed feature headers;
- do not recursively inspect `.tf` cache directories;
- do not infer feature existence or metadata from compiled cache data.

### Symlinks

`Path.is_file()` follows symlinks, which would make a `name.tf` symlink to an arbitrary target look like a shipped feature. Generated release documentation should describe files actually shipped in the module rather than external targets. A tracked/untracked symlink also creates avoidable ambiguity about which bytes define the feature header.

Selected boundary: a candidate `*.tf` path must be a non-symlink regular file. Directory matches are ignored as runtime/non-feature entries. A symlink matching `*.tf` should fail closed with a `FeatureDocsError` rather than be silently followed or silently omitted, because its presence looks like an intended feature filename but does not satisfy the shipped-feature-file contract.

## Scope

This ticket is deliberately independent of TF 0.5.0 and whole-document provenance. It changes only feature-file discovery. It must not:

- change feature descriptions or generated Markdown format;
- change TF corpus bytes;
- change version selection;
- change optional-provenance loading;
- weaken malformed regular-file validation.

## Evidence to preserve in tests

The plan/TDD gate should cover:

1. `.tf/` runtime cache directory beside ordinary feature files is ignored;
2. another directory ending in `.tf` is ignored;
3. the same cases are exercised in both core and optional provenance module locations;
4. valid regular `.tf` files remain discovered;
5. malformed regular `.tf` files still fail with `FeatureDocsError`;
6. a symlink named `*.tf` fails closed where symlinks are supported;
7. generated feature ordering/output remains deterministic.

The expected production change should be small and centralized in feature-path enumeration, not scattered exception handling in `read_header()`.