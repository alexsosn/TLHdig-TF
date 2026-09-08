# Plan: safe Text-Fabric links to TLHdig online

Issue: #41

Research: `docs/research-tlhdig-weblink.md`

## User contract

For nodes that belong to one unambiguous TF document, `A.webLink(node, urlOnly=True)` should return the authoritative TLHdig online text URL. In the TF browser, normal internal passage navigation remains intact and a separate `TLHdig ↗` action is shown beside it. Ambiguous records must have no external URL or source action.

## Implementation architecture

### `app/config.yaml`

Add only globally true metadata:

```yaml
provenanceSpec:
  webBase: https://hethport.net/TLHdig
  webHint: Open this text in TLHdig
```

Do not configure stock `webUrl`: raw section-template substitution neither encodes values nor vetoes ambiguous document identities.

### `app/app.py`

Create `TfApp(App)` as a thin integration adapter. After `super().__init__`, retain the stock TF `webLink`, install the corpus wrapper, and cache the set of raw document `docid` values whose **normalized TLHdig lookup identity is not one-to-one**. `reinit()` must reinstall the wrapper because TF `reuse()` runs `linksApi()` before `reinit()`.

Keep URL policy in pure helpers:

- `normalize_tlhdig_id(docid) -> str | None`: ordinary ID unchanged; one terminal direct `+` removed; terminal `(+)`, empty, and unsupported shapes fail closed.
- `tlhdig_url(docid) -> str | None`: uses `urllib.parse.urlencode({"d": value})`; never interpolates a TF node number.
- browser source-action rendering may use the same already-vetted `url_for_node()` result but must not alter the stock internal passage anchor.

## Owning-document resolution

For node `n`:

1. inspect `F.otype.v(n)`;
2. reject `lex` and `docgroup`;
3. `document` owns itself;
4. otherwise require exactly one `L.u(n, otype="document")` result;
5. require non-empty owner `docid`;
6. normalize the `docid` with the evidenced TLHdig lookup policy;
7. reject the record if that normalized lookup identity belongs to more than one TF document;
8. construct the encoded URL.

Never fall back to `txtid`, fragment label, `src_file`, CTH, or raw TF node ID.

For release `0.3.0`, CI pins both the historical 141 raw duplicate groups and the additional 25 normalization-only collision groups. The latter were discovered by independent review and prove that duplicate checking cannot safely happen before normalization.

## Preserve TF behavior

The wrapper keeps the stock signature.

- ordinary `_noUrl=True` calls: delegate to stock TF behavior;
- browser `_noUrl=True, _asString=True`: retain the stock internal navigation and append a separate `TLHdig ↗` action only when `url_for_node()` succeeds;
- ambiguous/unsupported browser passage: return the stock internal navigation unchanged;
- unsupported/ambiguous + `urlOnly=True`: return `None`;
- supported + `urlOnly=True`: return TLHdig URL;
- rendered links: reuse TF `outLink` machinery rather than hand-building unsafe HTML.

The browser action is intentionally adjacent to the internal TF anchor, never a replacement or nested anchor.

## RED gates

The initial RED tests were committed before production app changes and covered:

1. ordinary identifier;
2. URL-sensitive identifier;
3. terminal `+` normalization;
4. terminal `(+)` fail closed;
5. direct document;
6. descendant owner;
7. duplicate owner;
8. lex/docgroup;
9. zero/multiple owners;
10. no raw node ID in URL;
11. `_noUrl` stock delegation;
12. `reinit()` reinstall contract;
13. current release duplicate census without graph load.

After the first full-green implementation, independent review identified that Python `A.webLink()` worked but TF browser passage headings still exposed no upstream action because `_sectionLink()` always calls `_noUrl=True`. A review-driven RED regression then required:

14. browser internal navigation remains present;
15. an adjacent `TLHdig ↗` action appears only for an unambiguous record;
16. ambiguous browser records retain only the stock internal link.

That RED run had 533 passing tests and exactly one failure: the missing browser source action.

A second logically independent pass challenged ambiguity **after normalization**. A new RED case used two distinct raw IDs (`IBoT 4.229+` and `IBoT 4.229`) that collapse to one lookup key. The RED run had 534 passing tests and exactly that one failure. After GREEN, the full release census showed 25 normalization-only collision groups, so the safety fix protects real records rather than a hypothetical edge case.

## Test gate

Run ticket-local tests, full `programs/tests`, the identity census with expected raw duplicate count 141 and expected normalization-only collision count 25, `check_app.py`, feature-doc check, a custom-app discovery/webLink smoke fixture under TF 13.1, and the full existing corpus CI gates. Required CI must not depend on TLHdig uptime.

## Artifact impact

None. No changes to `tf/0.3.0`, `tf-provenance/0.3.0`, source corpus data, or certification stamps.

## Independent review

A fresh context must challenge raw-vs-normalized identity assumptions, over-broad composite normalization, query encoding (`+` in particular), cross-document ownership, lex/docgroup leakage, `_noUrl`, `reuse()`, nested/duplicated browser links, tautological tests, hidden schema/version changes, documentation drift, and live-network CI coupling. Blocking findings restart implementation→test→review.
