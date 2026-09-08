# Plan: source-faithful sign language propagation

Issue: #19. Research basis: `docs/research-sign-language.md`.

This plan is committed before any production/schema change.

## 1. Semantic contract

Add a node feature:

```text
sign.lang
```

Meaning: the effective **source-declared** language in scope for that source sign.
It is not a classifier prediction and not a normalized language ontology.

For every readable sign emitted from a source `<w>`, choose the first positive value in:

```text
w/@lg → active clb/@lg → current lb/@lg → text/@xml:lang
```

A value is positive iff `raw.strip()` is non-empty and is not exactly `XXXlang`.
The stored value is the winning stripped source string. No lexical or transliteration
heuristic is permitted.

If no positive declaration exists, omit `lang` on that sign.
Synthetic `anchor=1` sign slots never receive `lang`.

## 2. Scope state in the converter

Extend `_State` with language state that mirrors existing structural lifetime rather
than reparsing ancestry at sign emission time:

- `text_lang`: positive `text/@xml:lang` or absent;
- `line_lang`: raw/positive language of the current `lb`;
- `colon_lang`: raw/positive language of the active `clb`;
- the current word's `lg` is local to `_State.word()`.

Lifecycle:

1. constructor receives the text-level declaration;
2. `start_line(node)` updates line language;
3. when `start_line()` detects a parsed column change and closes the colon, clear
   `colon_lang` at the same semantic point;
4. `start_colon(node)` replaces `colon_lang`, including clearing it when `lg` is
   absent/empty/`XXXlang`;
5. `_State.word()` resolves the effective value once per word and applies it to every
   non-empty sign token created from that word;
6. technical anchor creation remains language-free.

Recovered `lb`/`clb` descendants are treated as the same boundary events production
already uses. #19 does not separately rewrite malformed structural recovery.

## 3. No normalization layer in this ticket

Do not introduce `lang_norm`, language IDs, ISO codes, or aliases. Existing coarse-level
features preserve source strings and the corpus contains legacy/malformed raw labels.
A normalization ontology would be a separate feature with separate research.

`ign` remains a real raw value. Empty and `XXXlang` remain non-positive and are never
written as a sign value.

## 4. Permanent independent conservation checker

Add `programs/check_sign_language.py`.

It must not import a converter language-propagation helper. It independently:

1. verifies corpus identity / uses the pinned repair manifest;
2. scans the strict production population in deterministic source order;
3. reconstructs the same source event grammar and parsed-column colon lifetime;
4. tokenises top-level words using the existing lexical sign tokenizer only to define
   the source-sign population;
5. builds expected per-document ordered `(sym/source-position, lang-or-absent,
   winning-level)` rows;
6. reads shipped TF with only the structural/features it needs;
7. removes `anchor=1` slots from the comparison;
8. compares each document's ordered source-sign language sequence exactly;
9. fails if an anchor carries `lang`;
10. fails unless the exact frozen coverage counts hold.

Frozen target census:

```text
total source signs       3,365,129
with lang                3,364,981
absent                         148
line                     3,259,913
colon                       64,686
word                        40,187
text                           195
```

The checker writes `reports/sign-language.md` with aggregate values, winning-level
census, absent counts, anchor audit, and first mismatches if any.

The checker compares the value sequence, not merely counts. The level census is a
research/conservation diagnostic; no `lang_source` feature is shipped.

## 5. RED gate

Before implementation, add failing tests covering all issue-mandated semantics.

### Fixture-level RED cases

1. **text inheritance** — line/colon/word silent, text `Hit` → signs `Hit`;
2. **line override** — text `Hit`, line `Akk` → signs `Akk`;
3. **colon override** — line `Hit`, colon `Hur` → signs `Hur` across subsequent lines
   in the same parsed column;
4. **word override** — active colon/line `Hit`, word `Akk` → that word `Akk` only;
5. **nested precedence** — word beats colon, colon beats line, line beats text;
6. **return from word override** — following word returns to the active outer scope;
7. **new colon** — replacement colon changes the effective value;
8. **column change** — active colon is cleared when the next line changes column;
9. **empty word attribute** — does not block outer positive language;
10. **empty line attribute** — falls back to text when no colon is active;
11. **`XXXlang`** — non-positive and falls back outward;
12. **`ign`** — remains literal `ign`;
13. **genuinely unlabelled sign** — feature absent;
14. **technical anchor** — never carries language;
15. **recovered nested boundary fixture** — event semantics match production structure
    without treating nested ancestry itself as a sign-inline override.

### Checker RED cases

At minimum, mutate a small generated TF fixture so that the checker detects:

- wrong sign language;
- language added to an absent sign;
- language omitted from a determined sign;
- language on an anchor;
- sign-order/row mismatch.

Hosted RED evidence must show failures specifically because `sign.lang` / the checker do
not yet exist, without unrelated failures.

## 6. Implementation changes

Expected production files:

- `programs/tlhdig/convert.py` — state + propagation;
- `programs/tlhdig/featuremeta.py` — feature semantics;
- `app/config.yaml` — expose `lang` on sign display;
- `programs/check_sign_language.py` — independent corpus conservation;
- `programs/tlhdig/release_policy.py` / `programs/release_check.py` — required gate;
- CI — ordinary sign-language conservation check;
- version/provenance/docs files required for immutable 0.4.0.

No morphology, cuneiform alignment, manuscript graph, repair, or tokenisation semantics
should change.

## 7. Version and release policy

Adding a shipped sign feature requires a new immutable artifact:

```text
TF_VERSION = 0.4.0
SOURCE_VERSION remains 0.3
```

The app points to 0.4.0. 0.1.0, 0.2.0 and 0.3.0 plus their provenance modules remain
byte-for-byte immutable.

Adding `sign-language` to the canonical required release gates changes policy identity:

```text
release-v3 → release-v4
```

The new gate must appear in `release_policy.REQUIRED_GATES` and the executable gate list
in the same position/order. Certification is run only after the final protected
source/config commit is frozen.

## 8. GREEN and regression gates

After implementation:

1. targeted sign-language fixture tests;
2. full `programs/tests` suite including adversarial shard;
3. sign round-trip;
4. structure conservation;
5. morphology;
6. manuscript joins;
7. marker/tag/provenance gates;
8. cuneiform alignment and locked external sign-reference checks;
9. independent `check_sign_language.py` exact corpus audit;
10. census;
11. app validation;
12. historical artifact immutability check;
13. immutable 0.4.0 build;
14. `release_check.py --mode regression-valid` under release-v4.

A change to sign count/order or unrelated feature values is a blocker.

## 9. Documentation / migration

Update feature documentation and README to state:

- `sign.lang` is effective source language;
- raw source labels are deliberately not normalized;
- absent means undetermined by source declarations, not "Hittite by default";
- precedence is word → colon → line → text;
- 0.4.0 adds the feature without changing old artifacts.

`KNOWN-ISSUES.md` should mark this preservation-map target as implemented only after the
0.4.0 artifact and conservation report exist.

## 10. Cleanup before review

Remove temporary issue-19 research scripts/workflows once their measurements are frozen
in the permanent research document and checker. Keep only durable tests, checker,
research/plan docs, reports and release machinery.

## 11. Logically independent adversarial review

The final review is performed from the exact PR patch/head after certification outputs
are committed. It must independently attack:

- precedence and scope reset boundaries;
- recovered nested line/colon events;
- column-change colon clearing;
- empty/`XXXlang` false certainty;
- raw-label preservation;
- all 148 absent signs;
- all 21,215 anchors remaining language-free;
- exact 3,365,129 non-anchor population and winning-level census;
- per-document sign ordering;
- absence of unrelated graph/morphology/cuneiform changes;
- 0.1/0.2/0.3 immutability;
- release-v4 gate identity and certification binding.

Any blocker restarts the dev → test → fresh independent review sub-loop.
