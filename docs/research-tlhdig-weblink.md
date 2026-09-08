# Research: Text-Fabric links to TLHdig online

Issue: #41

This document freezes the research gate before production app changes and records the browser-specific finding discovered during independent review.

## Question

Can TLHdig-TF expose `A.webLink()` / browser links back to the authoritative TLHdig online text pages without conflating TF record identity with TLHdig manuscript/publication identity?

## Current corpus facts

The released app is pinned to TF artifact `0.3.0`. Its level-1 section feature is `docid`, but `docid` is explicitly **not** a unique TF-record key: 141 values are shared by more than one `document` node. Existing conversion research shows that many duplicates are legitimate corpus records for the same manuscript/publication in distinct CTH/sub-corpus contexts (for example `KUB 26.71`). `docgroup` records this relationship without asserting edition equivalence.

`programs/research_weblink_ids.py` reproduces the identity-risk census directly from the committed `otype.tf` and `docid.tf` headers/data. It deliberately does not load `oslots` or the multi-gigabyte graph. It emits the complete duplicate groups plus URL-sensitive identifier classes (spaces, slashes, plus signs, parentheses, underscores, primes/apostrophes and non-ASCII values).

The research command is:

```bash
python programs/research_weblink_ids.py \
  --tf-dir tf/0.3.0 \
  --expect-duplicate-count 141
```

The duplicate count is an invariant of the current released artifact, not a permanent corpus constant; a future identity redesign under #16 may change the public addressing contract.

## TLHdig online endpoint

The current public text interface uses the observed shape `https://hethport.net/TLHdig/tlh_xtx.php?d=<text identifier>`.

Representative checks show both ordinary and composite behavior: ordinary manuscript/publication identifiers resolve to text pages; a member/publication identifier can resolve to a composite online edition; TLHdig display headings can include a trailing `+` while the `d=` query omits that display/join marker; existing repository research records `IBoT 4.41+` and `IBoT 4.229+` being queried as `IBoT 4.41` and `IBoT 4.229`; and `KBo 57.113` demonstrates that TLHdig may additionally use an `o=` context parameter, but there is no corpus-wide evidence that such a parameter is required or derivable for every TF record.

A successful HTTP response is not by itself proof of a one-to-one TF-record mapping. A composite page may legitimately aggregate several publication/manuscript identifiers.

## Key selection

`docid` is the best available upstream lookup value because it is sourced from AOHeader `<docID>` and denotes manuscript/publication identity. It is suitable for URL construction only when the owning TF document is unambiguous under the current release policy.

`txtid` is line-level source metadata and can vary with manuscript/witness context. It is not a safer record key and would couple link behavior to line/witness addressing. It is not selected as the public upstream-link key.

Manuscript apparatus publication/inventory labels are occurrence-level graph data, not substitutes for document upstream identity. A fragment may link to its owning document page; it must not synthesize a separate URL from its fragment label without an evidenced endpoint contract.

## Text-Fabric 13.1 behavior

The pinned Text-Fabric `webLink()` first tries `webFeature`; otherwise it substitutes section headings into `webUrl`. A config-only solution is unsafe because section substitutions are not URL-encoded and stock TF has no corpus-specific veto for duplicate `docid` records. `webFeature` also reads the feature on the node itself rather than climbing to the owning document.

Text-Fabric binds stock `webLink()` dynamically during `App.__init__`. A corpus-specific wrapper must therefore be installed after the base initializer and restored by `reinit()` on app reuse.

## Node ownership policy

The smallest safe contract is document-page linking:

- `document`: link if its `docid` occurs on exactly one TF document;
- textual/structural descendants: link to the unique owning document page;
- `lex`: no link; lex nodes span documents and TLHdig exposes no evidenced lexeme endpoint;
- `docgroup`: no link; it intentionally aggregates multiple TF records;
- zero or multiple owning documents: no link;
- owner with duplicated `docid`: no link under #41. #16 owns record-identity redesign.

This fails closed instead of silently conflating TF records.

## URL encoding and normalization

The app must use a standard URL-query encoder. Spaces, plus signs, slashes, parentheses, primes and non-ASCII values must never be interpolated raw.

Repository/live evidence supports treating one terminal direct join display marker `+` as display/join notation rather than part of the `d` lookup key. No general deletion of internal `+`, parentheses or other punctuation is justified. A terminal `(+)` or other unevidenced unusual shape remains unsupported/fail-closed.

## Line-level deep links

No stable, documented line-anchor/parameter contract was found that can be derived reliably from `(docid, collabel, lnno)`. Line-level linking is out of scope, avoiding invention of policy for #15's missing line labels.

## Browser semantics

Text-Fabric 13.1 uses `app.webLink(..., _noUrl=True, _asString=True)` in `_sectionLink()` so passage headings remain browser-internal navigation. An independent post-implementation review searched the pinned upstream source and found this is the sole production call site using `_noUrl=True`.

Therefore the corpus wrapper must **not replace** that internal anchor. For a safely mapped record it may append a separate `TLHdig ↗` external action beside the stock browser link. For an ambiguous/unsupported record it must return the stock browser link unchanged. Non-browser/private callers retain the stock `_noUrl` behavior.

This review finding closed a usability gap in the first green implementation: `A.webLink(..., urlOnly=True)` worked, but browser users otherwise had no visible way to open the authoritative TLHdig page.

## Architecture conclusion

#41 adds a small `app/app.py` adapter and globally true `webBase`/`webHint` metadata. The adapter owns unique owning-document resolution, duplicate-`docid` rejection, conservative terminal-join normalization, URL encoding, preservation of stock browser navigation, and the adjacent browser source action for safely mapped records.

It must not change corpus schema, document IDs, section keys, join semantics, or optional provenance loading. Live TLHdig availability may be used for controlled evidence but must not become an ordinary CI dependency.
