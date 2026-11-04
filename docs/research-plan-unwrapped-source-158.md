# #158 — Recover source transliteration without `<w>` wrappers

Status: research and narrow first-slice plan, **before conversion changes** (2026-10-12).
This targets missing user-queryable readings, not a new release/certification subsystem.

## Measured problem and primary-source evidence

The existing corpus inventory identifies 1,244 `cu`-visible, `no-sign-slots`
lines among 13,022 level-0 lines without lexical slots. These are candidate
losses, **not** 1,244 automatically recoverable documents. Other source
malformations, in particular `KBo 41.49+`'s nested `<w>` (#159), have
distinct failure mechanisms.

Pinned `corpus/TLHdig-0.3/CTH 170_XML_TLH/KBo 31.40.xml` has
`<P___Standard>` sections containing `<lb>` and unwrapped mixed text;
there are **zero literal `<w>` elements** in that record.
In `Vs. 2`, an actual line-level `cu` contains visible Unicode cuneiform
and the transliteration contains
`<d>URU</d>mi<del_fin/>-iz-za-ri <sGr>ŠEŠ</sGr><aGr>-IA</aGr> <aGr>QÍ-BÍ-MA</aGr>`.
In `Vs. 3` it contains
`<sGr>SI<del_fin/>G₅</sGr>-in e-eš-du <aGr>A-NA</aGr> <sGr>DAM</sGr><d>MEŠ</d>`.
Both lines also carry damage markers, `<space>` and text tails.

At present `convert._document` only calls `_State.word()` for `<w>`
elements. `signs.tokenise_word()` takes the literal inner bytes of a
recognized word span; it never encounters direct text and wrappers under
`P___Standard`. The pre-scan `_has_readable_sign(data, w_spans)`
likewise only examines `<w>` spans. When it sees no readable word it
allocates an **artificial anchor** on the first line, despite recoverable
text elsewhere. These are two distinct conversion barriers.

Existing top-level `<w>` conservation counts are intentionally exact.
Synthesized queryable lexical groups must be counted **separately** from
literal source words. We must not claim a fabricated `<w>` or a fabricated
source byte span.

## Frozen first-slice behavior

1. Source scope: first pilot is *only* the actual `KBo 31.40` source.
   Never infer readings from `lb@cu`; only tokenize source-present
   transliteration, byte-exactly, in lexical order.
2. Eligibility: a `<P___Standard>` text region with mixed text and no
   `<w>` descendants, bounded by the original `<lb>` and next
   `<lb>` / end of paragraph. Mixed explicit `<w>` plus raw
   content is a separate fail-closed follow-up until duplicate ownership
   and offset semantics are proved.
3. Preserve `<d>`, `<sGr>`, `<aGr>`, inline damage positions and
   `<space>`, including raw UTF-8 bytes of each recovered lexical unit.
   Do not serialize an XML tree and treat its new string offsets as
   source evidence. Keep the original XML immutable.
4. Distinguish **source-attested lexical bytes** from **derived word
   grouping**. Retain exact source `<w>` counts under the existing
   independent structure checks; report recovered groups separately.
   Do not count them as originally wrapped source words.
5. Correct synthetic-anchor preflight so it never adds a phantom slot
   *because* a document has no `<w>` when source-backed legible
   unwrapped readings are present. Preserve the documented empty-anchor
   semantics for truly blank/damage-only documents and lines.
6. This pilot must not regenerate the shared `tf/0.4.0` artifact while
   #155 is integrating alignment changes. Source-to-TF ID migration,
   global conservation and independent review come before production
   artifact replacement.

## TDD gates

- **RED 1:** build actual unmodified `KBo 31.40.xml` into a standalone
  throwaway TF directory. `Vs. 2` / `Vs. 3` must have nonempty sign
  readings sourced from the original XML; at least `URU`, `ŠEŠ`,
  `QÍ`, `BÍ`, `MA`, `DAM`, `MEŠ` must be queryable, with relevant
  determinative / Sumerogram / Akkadogram flags. Check source line IDs
  and individual glyphs independently of any alignment inference.
- **RED 2:** protect the zero literal `<w>` count while new inferred
  groups are explicitly distinguished from literal lexical nodes.
- **Negative controls:** blank `P___Standard`, genuine damage-only
  sequences, mixed wrapped-and-unwrapped text, nested apparatus and
  line-crossing markers cannot duplicate or invent readings.
- **Implementation:** after these tests fail for the expected **missing
  output**, add the smallest opt-in converter route. Require exact
  source/TF byte and marker conservation before expanding to other
  records. Existing `<w>` conversion must be unchanged.
- **Integration/review:** test full current source/sign/morphology/
  structure/alignment/reference gates and source-to-graph provenance;
  measure recovered lines versus remaining lost lines. Distinct
  adversarial review should inspect the raw XML, converter changes,
  before/after TF and adjacent mixed-content negative fixtures.

## Deferred

The population containing `KBo 28.72`, `DAAM 1.39`, and the malformed
nested-word class in #159 is **not** assumed to match the pilot. Inspect
each class on its own source bytes before widening any rule. No new
version directories, rebuilt historical artifacts, sidecars or general
TEI converter are needed.
