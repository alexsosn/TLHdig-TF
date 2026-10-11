# Plan: fail closed on unusable compound sign maps

Issue: #126
Research basis: `docs/research-signmap-multi-integrity.md`
Status: frozen before production implementation.

Sequence: research → frozen plan → TDD RED → minimal implementation → current-build validation → logically independent adversarial review.

## 1. Goal

Prevent a present but unusable `programs/signmap-multi.tsv` from surviving preflight, deleting the previous validated current artifact, and only then disabling compound cuneiform alignment.

Do not broaden this into a new sign-map format, a new release policy, or validation of unrelated mapping/sign-reference inputs.

## 2. Preserve the #124 boundary

#124 owns existence: a missing `signmap-multi.tsv` fails before reset.

#126 adds content integrity after that existence check and still before `reset_current_output()`:

- at least one non-comment mapping row;
- every data row has a nonempty reading;
- every data row's sequence is multi-codepoint cuneiform accepted by the same predicates as `load_multi()` and contains no damage placeholder;
- reading keys are unique.

Do not pin the current 139-row census or the file hash. `BUILD-MANIFEST.json` remains the exact-byte/input identity mechanism.

## 3. Parser design

Keep normal `load_multi()` behavior unchanged unless a RED test proves changing it is necessary. Add one narrow diagnostic helper next to it, e.g. `validate_multi(path) -> list[str]`.

The helper must reuse the same reading/sequence predicates as `load_multi()` rather than duplicate a subtly different cuneiform definition in `build.py`.

Diagnostics should identify the offending line/reason for:

- empty/comment-only map;
- malformed/unusable mapping row;
- one-codepoint/non-cuneiform/placeholder sequence;
- duplicate reading.

Generator confidence/observation metadata is research evidence, not part of this destructive-preflight implementation unless RED demonstrates it affects converter usability.

## 4. TDD RED gate

After #124 is on `main`, add tests before production code.

Required RED cases:

1. a present empty/comment-only `signmap-multi.tsv` fails before reset and preserves an old `BUILD-MANIFEST.json` sentinel;
2. a present row that `load_multi()` would silently ignore fails before reset and preserves the sentinel;
3. duplicate reading rows fail before reset rather than silently overwriting;
4. converter is never called in all failing cases.

Also add focused unit tests for the diagnostic helper contract. Observe hosted RED before implementation.

Synthetic successful-build fixtures must use a genuinely valid compound row, not a comment-only placeholder.

## 5. Minimal implementation

- add the diagnostic helper in `programs/tlhdig/cuneiform.py`;
- import/use it in `programs/build.py` after required-file existence checks and before any current-output reset;
- print a concise build failure with the first diagnostics and return nonzero;
- do not change generated TF bytes when the current valid table is present.

No unrelated validation inputs are added to `required_inputs`.

## 6. GREEN gate

Require:

- focused parser/preflight tests;
- full `python -m pytest programs/tests -q`;
- ordinary corpus/app/alignment checks;
- current artifact validation and refreshed `BUILD-MANIFEST.json`, because `build.py` and `tlhdig/cuneiform.py` are code-identity inputs;
- exact final head ordinary CI green.

The current generated output should remain byte-identical; any output digest change is a blocker requiring explanation rather than automatic acceptance.

## 7. Independent adversarial review

Review the exact final head from a fresh logical context and challenge:

- whether any current/generated row is rejected unexpectedly;
- whether preflight runs before both output trees can be deleted;
- whether duplicate keys or silent loader drops remain possible;
- whether normal `load_multi()`/conversion semantics changed unnecessarily;
- whether exact row count/hash was accidentally turned into a compatibility policy;
- whether unrelated validation inputs were pulled into build preflight;
- whether the current output digest stayed unchanged;
- whether temporary research/manifest workflows have been removed.

Any blocker restarts fix → test → fresh exact-head review.
