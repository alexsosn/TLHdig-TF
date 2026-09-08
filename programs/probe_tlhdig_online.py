#!/usr/bin/env python
"""Research-only probe of TLHdig online rendering for issue #15.

The source XML has real text on blank-lnr lines in KUB 50.123.  Print the rendered HTML
around distinctive readings so we can determine whether the web application synthesizes
a line label that is absent upstream.  This file is temporary research evidence, not a
runtime dependency.
"""
from __future__ import annotations

from html import unescape
import re
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

CASES = {
    "KUB 50.123": ["SIG₅-in", "ki-nu-un", "TE-RA-A-NU"],
    "DAAM 5.61": ["1′"],
    "DAAM 5.77": ["1′"],
}


def plain(html: str) -> str:
    html = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(html)).strip()


def main() -> int:
    for doc, needles in CASES.items():
        url = "https://www.hethport.uni-wuerzburg.de/TLHdig/tlh_xtx.php?d=" + quote_plus(doc)
        req = Request(url, headers={"User-Agent": "TLHdig-TF section-addressing research/1"})
        try:
            with urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf8", "replace")
        except Exception as exc:
            print(f"DOC {doc}: FETCH ERROR {exc}")
            continue
        text = plain(raw)
        print(f"DOC {doc}: HTTP OK bytes={len(raw)} title_present={doc in text}")
        for needle in needles:
            variants = (needle, needle.replace("₅", "5"), needle.replace("-", "-"))
            hit = next((v for v in variants if v and v in text), None)
            if hit is None:
                print(f"  NEEDLE {needle!r}: not found")
                continue
            at = text.index(hit)
            print(f"  NEEDLE {needle!r}: ...{text[max(0, at-160):at+len(hit)+160]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
