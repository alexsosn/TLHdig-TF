# Cuneiform and sign alignment

TLHdig-TF distinguishes **source line-level cuneiform** from **derived sign-level alignment**. They are related, but they do not have the same evidential status.

## Line-level source data

Where TLHdig supplies cuneiform for a line, the line can carry `cu` and associated status/count features. This preserves the available source string even when it cannot be aligned safely to every transliterated sign.

## Sign-level `cu_sign`

`cu_sign` is produced only where the alignment procedure can justify assigning a Unicode cuneiform value to a particular `sign` slot. Missing `cu_sign` therefore has several possible causes: genuinely unrendered source material, ambiguity, compounds/tokenization, PUA values or an alignment class not yet handled safely.

Use line-level status/features such as `cu_aligned`, `cu_method`, `cu_broken`, `cu_unrendered`, `cu_undecided` and related fields to interpret the result. Exact current coverage and the breakdown by mechanism live in [`../reports/alignment.md`](../reports/alignment.md).

## PUA values

Private Use Area code points occur in the source and are preserved. `cu_pua` records their presence, but the current graph does not yet expose the planned mapped-versus-unresolved classification for every PUA value. #20 owns that work.

Do not replace a PUA value with a modern Unicode sign merely because a visual or lexical similarity seems plausible. Mapping evidence must be explicit and reproducible.

## External sign lists

External sign lists are used as independent diagnostics. Agreement is useful evidence, but a majority of external lists is not automatically ground truth for a Hittite-context assignment: lists can conflict, omit Hittite-specific values or encode different conventions.

The current sign-reference and disagreement reports should therefore be read as validation/triage evidence rather than a license for automatic majority-vote rewriting.

## Safe analysis practice

When a study depends on sign-level cuneiform:

- report which alignment/status classes were accepted;
- distinguish unavailable alignment from negative linguistic evidence;
- keep unresolved/PUA cases visible unless the research question explicitly excludes them;
- use the generated alignment/sign-reference reports for the current artifact rather than copying a coverage percentage from prose.
