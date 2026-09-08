# Plan: safe Text-Fabric links to TLHdig online

Issue: #41

Research: `docs/research-tlhdig-weblink.md`

## User contract

For nodes that belong to one unambiguous TF document, `A.webLink(node, urlOnly=True)` should return the authoritative TLHdig online text URL. Ambiguous records must have no external URL.

## Implementation architecture

### `app/config.yaml`

Add only globally true metadata:

```yaml
provenanceSpec:
  webBase: https://hethport.net/TLHdig
  webHint: Open this text in TLHdig
```

Do not configure stock `webUrl`: raw section-template substitution neither encodes values nor vetoes duplicate `docid` records.

### `app/app.py`

Create `TfApp(App)` as a thin integration adapter. After `super().__init__`, retain the stock TF `webLink`, install the corpus wrapper, and cache the set of duplicate document `docid` values. `reinit()` must reinstall the wrapper because TF `reuse()` runs `linksApi()` before `reinit()`.

Keep URL policy in pure helpers:

- `normalize_tlhdig_id(docid) -> str | None`: ordinary ID unchanged; one terminal direct `+` removed; terminal `(+)`, empty, and unsupported shapes fail closed.
- `tlhdig_url(docid) -> str | None`: uses `urllib.parse.urlencode({"d": value})`; never interpolates a TF node number.

## Owning-document resolution

For node `n`:

1. inspect `F.otype.v(n)`;
2. reject `lex` and `docgroup`;
3. `document` owns itself;
4. otherwise require exactly one `L.u(n, otype="document")` result;
5. require non-empty owner `docid`;
6. reject duplicate `docid` values;
7. construct the encoded URL.

Never fall back to `txtid`, fragment label, `src_file`, CTH, or raw TF node ID.

## Preserve TF behavior

The wrapper keeps the stock signature.

- `_noUrl=True`: delegate unchanged to stock TF behavior.
- unsupported/ambiguous + `urlOnly=True`: return `None`.
- supported + `urlOnly=True`: return TLHdig URL.
- rendered links: reuse TF link/text escaping machinery rather than hand-building unsafe HTML.

## RED gate

Tests are committed before production app changes and cover:

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

## Test gate

Run ticket-local tests, full `programs/tests`, the identity census with expected duplicate count 141, `check_app.py`, feature-doc check, a custom-app discovery/webLink smoke fixture under TF 13.1, and the full existing corpus CI gates. Required CI must not depend on TLHdig uptime.

## Artifact impact

None. No changes to `tf/0.3.0`, `tf-provenance/0.3.0`, source corpus data, or certification stamps.

## Independent review

A fresh context must challenge duplicate-record equivalence assumptions, over-broad composite normalization, query encoding (`+` in particular), cross-document ownership, lex/docgroup leakage, `_noUrl`, `reuse()`, tautological tests, hidden schema/version changes, and live-network CI coupling. Blocking findings restart implementation→test→review.
