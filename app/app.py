"""Corpus-specific Text-Fabric app hooks for TLHdig-TF.

The corpus graph remains authoritative for semantics.  This module only adapts the
high-level TF app to TLHdig's public text-page URL contract.
"""

from __future__ import annotations

import types
from collections import defaultdict
from urllib.parse import urlencode

from tf.advanced.app import App
from tf.advanced.helpers import dh
from tf.advanced.links import outLink

TLHDIG_BASE = "https://hethport.net/TLHdig"
TLHDIG_TEXT = f"{TLHDIG_BASE}/tlh_xtx.php"
_NO_EXTERNAL_LINK_TYPES = {"lex", "docgroup"}


def normalize_tlhdig_id(docid: str | None) -> str | None:
    """Return the evidenced TLHdig lookup key for a source document identifier.

    TLHdig displays a terminal direct-join ``+`` on composite identifiers while its
    text lookup accepts the identifier without that display marker.  No corresponding
    corpus-wide contract has been established for terminal ``(+)`` or ``++`` shapes,
    so those fail closed instead of being guessed.
    """

    if not isinstance(docid, str) or not docid:
        return None
    if docid.endswith("(+)") or docid.endswith("++"):
        return None
    if docid.endswith("+"):
        docid = docid[:-1]
    return docid or None


def tlhdig_url(docid: str | None, base: str = TLHDIG_TEXT) -> str | None:
    """Build an encoded TLHdig text URL, or ``None`` for an unsupported identifier."""

    lookup = normalize_tlhdig_id(docid)
    if lookup is None:
        return None
    return f"{base}?{urlencode({'d': lookup})}"


def duplicate_docids(app) -> set[str]:
    """Return raw docids whose TLHdig lookup identity is not one-to-one.

    Ambiguity is defined *after* the evidenced TLHdig normalization.  This rejects
    both repeated raw identifiers and distinct raw values such as ``X+`` and ``X``
    that would otherwise collapse onto the same upstream ``d=X`` page.
    """

    F = app.api.F
    by_lookup: dict[str, list[str]] = defaultdict(list)
    for node in F.otype.s("document"):
        raw = F.docid.v(node)
        lookup = normalize_tlhdig_id(raw)
        if raw and lookup is not None:
            by_lookup[lookup].append(raw)

    return {
        raw
        for raw_values in by_lookup.values()
        if len(raw_values) > 1
        for raw in raw_values
    }


def owning_document(app, node: int) -> int | None:
    """Resolve exactly one owning document without using slot-anchor accidents."""

    F = app.api.F
    n_type = F.otype.v(node)
    if n_type in _NO_EXTERNAL_LINK_TYPES:
        return None
    if n_type == "document":
        return node
    owners = tuple(app.api.L.u(node, otype="document"))
    return owners[0] if len(owners) == 1 else None


def url_for_node(app, node: int, duplicates: set[str] | None = None) -> str | None:
    """Return the TLHdig document-page URL only for an unambiguous TF record."""

    owner = owning_document(app, node)
    if owner is None:
        return None
    docid = app.api.F.docid.v(owner)
    if not docid:
        return None
    duplicate_values = duplicate_docids(app) if duplicates is None else duplicates
    if docid in duplicate_values:
        return None
    return tlhdig_url(docid)


def _plain_result(app, node: int, text=None):
    """Derive the same human-facing label TF uses when there is no external URL."""

    n_type = app.api.F.otype.v(node)
    if text is not None:
        return text, None
    if n_type in app.context.lexTypes:
        return (
            app.getText(False, node, n_type, False, True, True, "", None, None),
            None,
        )
    passage = app.sectionStrFromNode(node)
    return passage, passage


def _browser_source_action(app, node: int) -> str | None:
    """Render the separate upstream action used beside browser-internal navigation."""

    href = url_for_node(app, node, app._tlhdig_duplicate_docids)
    if href is None:
        return None
    return outLink(
        "TLHdig ↗",
        href,
        clsName="tlhdig-source",
        title=app.context.webHint,
        asHtml=True,
    )


def tlhdig_web_link(
    app,
    n,
    text=None,
    clsName=None,
    urlOnly=False,
    _asString=False,
    _noUrl=False,
):
    """Text-Fabric ``webLink`` compatible wrapper with TLHdig ambiguity checks."""

    stock = app._tf_stock_web_link
    if _noUrl:
        internal = stock(
            n,
            text=text,
            clsName=clsName,
            urlOnly=urlOnly,
            _asString=_asString,
            _noUrl=True,
        )
        # TF passage headings intentionally use _noUrl=True for their own internal
        # navigation. Keep that link intact and add a distinct upstream action rather
        # than replacing it. Other callers retain stock behavior exactly.
        if not (app._browse and _asString and not urlOnly):
            return internal
        source = _browser_source_action(app, n)
        if source is None:
            return internal
        return f"{internal} {source}" if internal else source

    href = url_for_node(app, n, app._tlhdig_duplicate_docids)
    if href is None:
        if urlOnly:
            return None
        result, _ = _plain_result(app, n, text=text)
        if _asString:
            return result
        dh(result, inNb=app.inNb)
        return None

    if urlOnly:
        return href

    n_type = app.api.F.otype.v(n)
    passage = app.sectionStrFromNode(n)
    if text is None:
        text = passage
    style = app.context.styles.get(n_type)
    if style:
        clsName = f"{clsName or ''} {style}"
    result = outLink(
        text,
        href,
        clsName=clsName,
        passage=passage,
        title=app.context.webHint,
        asHtml=app.inNb is not None or app._browse,
    )
    if _asString:
        return result
    dh(result, inNb=app.inNb)
    return None


class TfApp(App):
    """TLHdig-TF high-level app with conservative upstream text links."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._install_tlhdig_weblink()

    def _install_tlhdig_weblink(self):
        if not self.api:
            return
        current = getattr(self, "webLink", None)
        if current is not None and getattr(current, "__func__", None) is not tlhdig_web_link:
            self._tf_stock_web_link = current
        if not hasattr(self, "_tf_stock_web_link"):
            return
        self._tlhdig_duplicate_docids = duplicate_docids(self)
        self.webLink = types.MethodType(tlhdig_web_link, self)

    def reinit(self):
        # App.reuse() has just rebound Text-Fabric's stock link API before calling us.
        self._install_tlhdig_weblink()
