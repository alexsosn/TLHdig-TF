# Known issues in `tf/0.1.0`

Raised by an independent code review and **verified against the released files**. The
dataset is an integration prototype: the parsing components are well tested, but several
of them are not wired into the generated graph, and some documented guarantees are
therefore false of `0.1.0`.

Status key: ❌ open · 🔧 fixing · ✅ fixed

---

## Critical

### ❌ 1. `src_span` is wrong for repaired documents

`director()` reads the original bytes, applies the repair manifest **in memory**, then
scans the *repaired* stream for byte offsets — while `document.src_file` still names the
unmodified file. **166 of the 173 repaired files change length**, so every `src_span`
after the first patch site is shifted.

Demonstrated on `CTH 167_XML_TLH/KBo 9.43+.xml` (−1 byte): a word's span slices
`<w trans="ša" …>` from the repaired stream and ` <w trans="ša" …` from the original.

This also undermines the decision to store `raw` only when `parse_ok=0`: the argument
was that the verbatim `mrpN` string stays recoverable through `src_span`. For repaired
documents it does not.

**Fix:** keep an original↔repaired offset map, or emit both `src_span` and
`repaired_span` as the plan (§2.1) actually specifies. Needs an integration test with
insertions and deletions before several `<w>` nodes.

### ❌ 2. The damage model is not in the dataset

`otype.tf` contains: `analysis colon column document edit layout line paragraph sign
surface word`. There is **no `cluster` node type**.

`convert.py` builds a `brackets.Tracker`, feeds it, and calls `finish()` — then never
emits `tracker.clusters` as nodes. Three further integration defects sit behind that:

* **Marker offsets are discarded.** The tokeniser records `(tag, offset)` per sign and
  is tested on a `del_fin` after character 3, but the converter does
  `for tagname, _off in t.markers`, so every marker would land at offset 0.
* **The cross-line lookahead is unused.** `Tracker.start_line(line_no, continues=…)`
  implements the rule measured in plan §6, but the converter calls
  `start_line(self.line_no)` with no hint — so the 74,634 genuine cross-line ranges
  cannot survive as ranges.
* **Sign damage flags are stamped after all of a sign's markers are fed**, so a
  `del_in` mid-sign marks the whole sign damaged, a mid-sign `del_fin` can leave it
  unmarked, and an open+close inside one sign leaves it unmarked. Mid-sign markers were
  the main argument for sign slots, so this needs to be right.

---

## High

### ❌ 3. Contract B is only partly delivered

Missing node types: `cluster`, `note`, `fragment`, `lex`, `docgroup`. Missing edges:
`witness`, `joins`, `noteref`, `edition`, `lexeme`.

`<AO:Manuscripts>` is not processed at all, so the witness layer — publication sigla,
inventory numbers, 1,060 direct and 166 indirect joins — is absent.

Editorial history is partial: `_document()` uses `root.iterfind("AOHeader/meta/*")`,
which sees direct children only, missing the `<annotation>` wrapper that holds ~58,372
`<annot>` events and the nested `neu` structures.

### ❌ 4. Documents can vanish while the build reports success

The conversion loop has two silent `except: continue` paths (patch failure, parse
failure). **23,937 source files produce 23,884 document nodes** — 52 unaccounted for
beyond the one encrypted file, with no error raised.

**Fix:** make `sources = converted + explicitly excluded` an invariant and abort
otherwise.

### ❌ 5. The gates do not gate

* `check_morph.py` calls itself a gate and **returns 0 unconditionally**.
* `check_contract_a.py` has **zero references to the built dataset** — it validates the
  source corpus against itself, which is why it cannot catch issue 1.
* `build.py` runs **no gate at all**, and there is no CI workflow.

### ❌ 6. Duplicate `docid` makes section addressing ambiguous

`docid` is the level-1 section feature, and **141 values are shared by more than one
document node** (`KUB 26.71` covers 3). The planned `docgroup`/`edition` layer that
would keep record identity separate from manuscript identity is not implemented.

---

## Medium

### ❌ 7. Crossing-tag repairs make structural choices

The manifest's safeguards (SHA-256, exact bytes, unique target, post-repair parse) are
sound for lexical damage. But for `<w><AO:Akkgram>…</w>…</AO:Akkgram>` the algorithm
*chooses* to close the wrapper before `</w>` and delete the later close. That changes
which material lies inside the Akkadogram. XML validity cannot tell whether the intended
correction was to move the wrapper boundary or the word boundary.

**Fix:** categorise patches, mark this class as needing human review, and record a
confidence in the manifest. 74 of 632 patches are crossing-tag repairs.

### ❌ 8. The published files are not the files that were load-tested

`convert.build()` writes and loads the dataset; `build.py` then rewrites every node
feature in place with the compactor and **does not reload**. The reported counts come
from the pre-compaction API. The compactor's tests check its output through its own
parser, not through Text-Fabric.

**Fix:** reload with `Fabric(...).loadAll()` after compaction and run representative
queries, as a mandatory build step.

---

## What is sound

The sign tokeniser (100% byte round-trip, adversarial cases for wrappers, mid-sign
markers, separators), the morphology parser (`mrp0`, sparse indices, four separator
forms, literal `+` in data, field-4 classification, selector variants), and the
hash-pinned repair manifest are all in good shape. The problem is localised: components
were tested more thoroughly than they were connected.
