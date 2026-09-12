# Research: compound sign-map integrity before destructive rebuild

Issue: #126

## Question

After #124 makes `programs/signmap-multi.tsv` mandatory by existence, what content-level invariant must be checked **before** `reset_current_output()` so a present but unusable compound map cannot destroy the previous validated artifact?

This is a build-preservation question, not a new cuneiform-mapping algorithm.

## Current data flow

`programs/learn_signmap.py` generates two pinned tables. `signmap-multi.tsv` is the compound table consumed by `tlhdig.convert` through `cuneiform.load_multi()` while conversion is already in progress. `programs/build.py` resets the current main/provenance output trees before calling that converter.

#124 closes the missing-file hole by checking `signmap-multi.tsv` alongside the existing repair/source/exclusion inputs before reset. It does not validate the contents.

`load_multi()` is intentionally permissive today: a missing path yields `{}`, and non-comment rows that do not satisfy its reading/sequence checks are silently skipped. Duplicate readings overwrite earlier rows through normal dictionary assignment. Therefore file existence alone cannot establish that the table the converter will actually use is meaningful.

## Generator contract

The current generator constructs `kept` rows only when all of these hold:

- the reading has at least `MIN_OBS = 5` observations;
- confidence is at least `MIN_CONF = 0.95`;
- the learned spelling contains 2–`MAX_SEQ = 4` codepoints;
- the spelling contains no damage placeholder;
- `_spellable()` accepts it, which requires `cuneiform.is_sign(seq)`;
- the reading is nonempty before the observation is recorded.

`_write()` emits six TSV columns (reading, sequence, confidence, top observations, total observations, display name). The converter only consumes the first two columns; the remaining columns are evidence about how the generated row was learned.

There is no documented generator path that deliberately emits a row for `load_multi()` to ignore.

## Current-table census

`programs/research_signmap_multi_integrity.py` was run in hosted Actions on PR #127, run `34627205549`.

Result for current `programs/signmap-multi.tsv`:

- data rows: **139**;
- `load_multi()` entries: **139**;
- duplicate readings: **0**;
- silently ignored readings: **0**;
- unexpected loaded readings: **0**;
- strict generator-contract problems: **0**.

The census also checked the generator thresholds, six-column shape, numeric observation/confidence evidence, 2–4 codepoint sequence bound, placeholder exclusion and `is_sign()`.

So strict loader-facing validation is backward-compatible with the current generated table; no present row relies on silent skipping or duplicate overwrite.

## What belongs in destructive preflight

The build preflight should establish only what is needed to avoid destroying a valid current artifact before discovering that conversion has lost its compound map:

1. the file exists (#124);
2. it contains at least one non-comment mapping row;
3. every non-comment row has a nonempty reading and a sequence that `load_multi()` can actually use (multi-codepoint cuneiform, no placeholder);
4. reading keys are unique, so no row is silently shadowed.

It should **not** pin the current count of 139 rows, observation totals, confidence values, or an expected file hash. Those may legitimately change when the table is regenerated. Exact input bytes are already bound by `BUILD-MANIFEST.json`; duplicating that hash as a destructive-preflight rule would recreate release machinery rather than protect the reset boundary.

The six-column metadata and generator thresholds remain useful research/audit evidence. They do not affect conversion once the first two columns are usable, so a metadata-policy checker can remain separate from the minimal destructive-preflight invariant.

## Parser/API direction

Do not create a second parser in `build.py`. Put diagnostics next to `cuneiform.load_multi()` so permissive conversion loading and strict preflight interpret reading/sequence validity identically.

A narrow helper such as `validate_multi(path) -> list[str]` is preferable to changing normal `load_multi()` semantics globally. It can report line-specific unusable rows, duplicate keys and an empty mapping. `build.py` can call it after the required-file existence check and before any output reset; the converter can continue using the existing loader.

This keeps the behavioral change at the destructive boundary while making the validation rule reusable and testable.

## Scope boundary

Audit during #124/#126 found no additional checked-in data file read by production conversion after reset that should be pulled into this preflight. `signmap.tsv`, `known_lossy.txt`, `contract_a_known.txt`, sign-reference locks and related files are validation witnesses/policies, not converter inputs. They remain manifest/validation inputs rather than destructive-build prerequisites.

## Conclusion

The current table proves there is no compatibility reason to preserve silent row loss. The smallest justified invariant is therefore: **a present compound map must contain at least one usable mapping, every data row must be loader-usable, and readings must be unique before current output is reset**. Byte identity stays with the current build manifest.
