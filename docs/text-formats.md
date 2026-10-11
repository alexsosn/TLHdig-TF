# Text formats and rendering

TLHdig-TF separates textual data from presentation. Text-Fabric formats and the corpus app render features already present in the graph; display code is not a second parser and should not manufacture linguistic or editorial state.

## Transliteration

Readable sign slots preserve the transliterated source stream and separators needed to reconstruct words and lines. Features such as `sym`, `after` and `trans` support different reading and query contexts. The generated [feature reference](features/0_home.md) gives the exact current definitions.

For ordinary reading, prefer the configured Text-Fabric text formats over concatenating `sym` values manually: separators, editorial representation and layout can matter.

## Hittitological display

The app adds semantic presentation for distinctions already represented in TF, including writing-system and editorial states such as Sumerograms, Akkadograms, determinatives and damage-related markup. Styling is a convenience layer. Query code should use the underlying features rather than infer semantics from HTML classes, font style or colour.

If a visual distinction is absent, that does not by itself prove the corresponding source information is absent; inspect the feature reference and graph.

## Cuneiform-facing formats

Line-level source cuneiform and sign-level aligned cuneiform have different contracts. A line can contain source cuneiform while individual signs remain unaligned. Sign-level display must therefore respect the alignment/status features rather than fill gaps by guesswork.

See [Cuneiform and alignment](cuneiform.md) for the confidence boundary.

## Layout and empty-looking material

Some source structures carry layout or annotation information without ordinary readable signs. They are not safe to treat as missing data solely because a plain-text rendering looks empty. Conversely, the converter must not fabricate readable signs simply to attach an annotation.

For questions about source recovery or zero-width structures, consult [Provenance](provenance.md) and the current [known-issues register](../KNOWN-ISSUES.md).
