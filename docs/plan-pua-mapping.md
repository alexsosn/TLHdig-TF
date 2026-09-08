# Plan: reproducible PUA mapping status (#20)

This plan is frozen after `docs/research-pua-mapping.md` and before production code.

## 1. User-visible semantic contract

Add `cu_pua_unmapped` as a **line node integer feature**:

> number of Private Use Area code points in the verbatim line-level `cu` string whose exact code point lacks a pinned direct mapping in the committed PUA status table.

This is a count of unresolved PUA *occurrences*, not distinct code points and not a guess at sign identity.

For every line:

- `cu_pua` = all PUA code-point occurrences in `cu`;
- `cu_pua_unmapped` = PUA occurrences whose committed status is not directly mapped;
- therefore `cu_pua - cu_pua_unmapped` = directly mapped PUA occurrences.

The feature is line-only. A sign-level flag would be incomplete because 218 current PUA occurrences occur on level-0 lines without complete `cu_sign` alignment. Existing `cu_sign` remains unchanged.

## 2. Mapping-status data

Add one committed machine-readable mapping/status file under `programs/` with:

- schema version;
- external source/package identity and version;
- each known exact PUA code point;
- status: `mapped-deliberate-pua` or `ambiguous-legacy-pua` (with `unknown-pua` reserved for research/reporting);
- sign/HZL/standard-Unicode fields when evidenced;
- a short evidence statement.

Only `mapped-deliberate-pua` counts as mapped for `cu_pua_unmapped`. `ambiguous-legacy-pua` stays unresolved until a pinned source directly proves the historical crosswalk.

Current frozen population:

- mapped: `U+100000`, 924 occurrences;
- unresolved: `U+100001`, `U+100003`, `U+100005`, `U+100006`, `U+100009`, 2,719 occurrences;
- total PUA: 3,643 occurrences.

The table is evidence/configuration, not a Unicode rewrite map. No PUA character is replaced.

## 3. Classifier implementation

Add a small `tlhdig.pua` module responsible only for:

- correct Unicode PUA detection across BMP PUA, Supplementary PUA-A and Supplementary PUA-B;
- loading/validating the committed status table;
- classifying an exact code point as directly mapped, declared unresolved, or undeclared;
- counting all and unresolved PUA occurrences in a string.

The converter uses this module for `cu_pua` and `cu_pua_unmapped`. On the current corpus this must leave every existing `cu_pua` value unchanged.

An **undeclared future PUA value is unresolved by default**, never mapped. Conversion may represent it as unresolved, but the permanent corpus/release gate must fail until research explicitly adds it to the committed status table. Thus new source data cannot silently expand the trusted mapping set.

## 4. Permanent independent checker

Add `programs/check_pua_mapping.py` as a corpus-level conservation gate. It must independently walk the repaired source `lb/@cu` stream and the shipped TF graph and verify:

1. exact source/TF PUA code-point inventory and occurrence counts;
2. `cu` strings remain unchanged by this feature;
3. every `cu_pua` equals the count of PUA characters in that line;
4. every `cu_pua_unmapped` equals the count of non-directly-mapped PUA characters in that line;
5. all observed PUA code points are declared in the committed status table;
6. frozen current totals are 3,643 PUA / 924 mapped / 2,719 unresolved;
7. line/sign alignment is not required to classify a line, so level-0 occurrences remain covered.

The checker may consume the committed mapping/status JSON as the declared contract, but must not import converter counting helpers. This separates graph production from conservation verification.

## 5. RED gate

Before implementation, commit tests that fail for the missing contract:

- mapped PUA occurrence (`U+100000`) => `cu_pua=1`, `cu_pua_unmapped=0`;
- declared unresolved PUA (`U+100009`) => `1`, `1`;
- mixed string with mapped + unresolved + ordinary cuneiform => total and unresolved counts differ correctly;
- non-PUA cuneiform => both counts zero/feature absent according to TF sparse serialization;
- future undeclared PUA => unresolved classifier result and explicit checker/table-coverage failure;
- synthetic level-0 line remains classifiable at line level without a sign assignment;
- mapping-table schema rejects duplicate/invalid code points and invalid statuses;
- corpus constants match the frozen research inventory.

The hosted RED must show only failures attributable to the absent production module/feature/checker.

## 6. Artifact/version integration

Do **not** allocate an immutable TF version on the research/RED branch. #66 is already an artifact-changing lane at RED.

Immediately before implementation:

1. refresh `main` and all artifact-changing PR ownership;
2. whichever lane reaches production integration first allocates the next unused TF version;
3. rebase this branch onto that exact current `main`;
4. allocate the then-next immutable TF version and update predecessor delta metadata;
5. regenerate the full artifact rather than modifying an existing version.

The serialized semantic delta expected from this ticket is the new `cu_pua_unmapped.tf` feature plus release/version metadata required by the immutable-version mechanism. Existing feature bodies, especially `cu.tf`, `cu_sign.tf`, and `cu_pua.tf`, must remain semantically unchanged.

A release-policy revision must make the PUA conservation checker mandatory for the new artifact while preserving all historical release-policy contracts. The concrete policy number is assigned only after rebasing, to avoid collision with other active release lanes.

## 7. Full test gate

After implementation run:

- targeted PUA unit/integration tests;
- full unit/adversarial suite;
- permanent PUA conservation checker;
- cuneiform alignment and locked sign-reference checks;
- source sign round-trip;
- corpus/repair identity;
- feature metadata/reference generation;
- census and app validation;
- predecessor-delta certification proving no undeclared semantic artifact changes;
- full canonical release certification on the exact final tree.

## 8. Independent adversarial review

A logically independent final review must challenge at least:

- circular use of learned `signmap.tsv` or `cu_sign` as external mapping authority;
- accidental treatment of `ambiguous-legacy-pua` as mapped;
- incomplete PUA range detection;
- mixed-value counting errors;
- level-0 coverage loss;
- any rewrite/normalization of original `cu` or `cu_sign` values;
- undeclared future PUA values silently passing as mapped;
- unpinned or mutable external provenance;
- unexpected changes to existing TF feature bodies;
- release-version/policy collision with concurrently integrated feature lanes.

Any blocking finding returns through RED → fix → full gates → fresh review.
