#!/usr/bin/env python
"""Research-only live HFR presentation probe for issue #79.

Fetch representative public HFR pages and report the presentation-layer evidence around
its annotation-status legend without assigning semantic meaning to CSS itself.  The
semantic interpretation remains sourced from HFR's annotation documentation.
"""
from __future__ import annotations

from collections import Counter
from html import unescape
from html.parser import HTMLParser
from hashlib import sha256
import json
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

TARGETS = (
    "https://hethport.net/HFR/bascorp_xtx.php?d=KBo+35.208&lang=EN&o=CTH+500",
    "https://hethport.net/HFR/bascorp_xtx.php?d=KBo+37.62&lang=EN&o=CTH+741&z=5%E2%80%B2",
    "https://hethport.net/HFR/bascorp_xtx.php?d=KBo+38.103&lang=EN&o=CTH+670&z=Vs.+6%E2%80%B2",
)
NEEDLES = (
    "pre-validated",
    "not validated",
    "magenta",
    "gray",
    "grey",
    "vorvalidiert",
    "nicht validiert",
)
COLOR_RE = re.compile(r"(?:color\s*:|magenta|gr[ae]y)", re.I)
ATTR_RE = re.compile(r"\b(class|style)\s*=\s*([\"'])(.*?)\2", re.I | re.S)
STYLESHEET_RE = re.compile(
    r"<link\b[^>]*\brel\s*=\s*([\"'])stylesheet\1[^>]*\bhref\s*=\s*([\"'])(.*?)\2[^>]*>",
    re.I | re.S,
)
STYLESHEET_RE_REV = re.compile(
    r"<link\b[^>]*\bhref\s*=\s*([\"'])(.*?)\1[^>]*\brel\s*=\s*([\"'])stylesheet\3[^>]*>",
    re.I | re.S,
)


def fetch(url: str) -> tuple[str, str]:
    req = Request(url, headers={"User-Agent": "TLHdig-TF research probe/1.0"})
    with urlopen(req, timeout=30) as response:
        content_type = response.headers.get("Content-Type", "")
        raw = response.read()
    charset = "utf-8"
    m = re.search(r"charset=([\w.-]+)", content_type, re.I)
    if m:
        charset = m.group(1)
    return raw.decode(charset, errors="replace"), content_type


def snippets(text: str, needle: str, radius: int = 350) -> list[str]:
    low = text.lower()
    target = needle.lower()
    out = []
    start = 0
    while len(out) < 4:
        pos = low.find(target, start)
        if pos < 0:
            break
        lo = max(0, pos - radius)
        hi = min(len(text), pos + len(needle) + radius)
        out.append(re.sub(r"\s+", " ", text[lo:hi]).strip())
        start = pos + len(target)
    return out


def stylesheets(html: str, base: str) -> list[str]:
    hrefs = [m.group(3) for m in STYLESHEET_RE.finditer(html)]
    hrefs.extend(m.group(2) for m in STYLESHEET_RE_REV.finditer(html))
    return sorted({urljoin(base, unescape(h)) for h in hrefs})


def main() -> int:
    report: dict[str, object] = {"schema": 1, "targets": []}
    css_urls: set[str] = set()
    for url in TARGETS:
        html, content_type = fetch(url)
        css_urls.update(stylesheets(html, url))
        classes: Counter[str] = Counter()
        inline_styles: Counter[str] = Counter()
        for m in ATTR_RE.finditer(html):
            kind, value = m.group(1).lower(), unescape(m.group(3)).strip()
            if kind == "class":
                classes.update(value.split())
            elif value:
                inline_styles[value] += 1
        target = {
            "url": url,
            "contentType": content_type,
            "sha256": sha256(html.encode("utf-8")).hexdigest(),
            "bytesDecodedUtf8": len(html.encode("utf-8")),
            "legendSnippets": {
                needle: snippets(html, needle) for needle in NEEDLES if needle.lower() in html.lower()
            },
            "classes": dict(classes.most_common()),
            "colorInlineStyles": {
                style: count for style, count in inline_styles.most_common() if COLOR_RE.search(style)
            },
            "stylesheets": stylesheets(html, url),
        }
        report["targets"].append(target)

    css_report = []
    for url in sorted(css_urls):
        try:
            css, content_type = fetch(url)
        except Exception as e:  # research output must expose unavailable dependencies
            css_report.append({"url": url, "error": f"{type(e).__name__}: {e}"})
            continue
        rules = []
        for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", css, re.S):
            selector = re.sub(r"\s+", " ", block.group(1)).strip()
            body = re.sub(r"\s+", " ", block.group(2)).strip()
            if COLOR_RE.search(body) or COLOR_RE.search(selector):
                rules.append({"selector": selector, "body": body})
        css_report.append({
            "url": url,
            "contentType": content_type,
            "sha256": sha256(css.encode("utf-8")).hexdigest(),
            "colorRules": rules,
        })
    report["stylesheets"] = css_report
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
