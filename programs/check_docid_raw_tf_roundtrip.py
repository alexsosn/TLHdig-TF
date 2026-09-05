#!/usr/bin/env python
"""Empirically test Text-Fabric 13.1.0 string-value whitespace preservation.

Research-only companion to analyze_docid_raw.py for issue #10.
"""
from pathlib import Path
import tempfile

from tf.convert.walker import CV
from tf.fabric import Fabric


VALUE = "KBo 50.89 "


def director(cv):
    doc = cv.node("document")
    slot = cv.slot()
    cv.feature(slot, sym="x")
    cv.feature(doc, docid="KBo 50.89", docid_raw=VALUE)
    cv.terminate(doc)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tf = Fabric(locations=tmp, silent="deep")
        cv = CV(tf, silent="deep")
        good = cv.walk(
            director,
            "sign",
            otext={
                "fmt:text-orig-full": "{sym}",
                "sectionTypes": "document",
                "sectionFeatures": "docid",
            },
            generic={"name": "docid-raw-roundtrip"},
            intFeatures=set(),
            featureMeta={
                "sym": {"description": "synthetic slot"},
                "docid": {"description": "normalized id"},
                "docid_raw": {"description": "raw id"},
            },
            warn=False,
        )
        if not good:
            raise RuntimeError("CV.walk failed")

        fresh = Fabric(locations=tmp, silent="deep")
        api = fresh.load("docid docid_raw sym")
        if api is None:
            raise RuntimeError("fresh Fabric.load failed")
        docs = api.F.otype.s("document")
        if len(docs) != 1:
            raise AssertionError(f"expected one document, got {docs}")
        reloaded = api.F.docid_raw.v(docs[0])

    preserved = reloaded == VALUE
    report_path = Path("docs/research-docid-raw.md")
    text = report_path.read_text(encoding="utf8").rstrip()
    section = "\n".join(
        (
            "",
            "## Text-Fabric 13.1.0 whitespace round-trip",
            "",
            "Because all three real differences are trailing spaces, a separate synthetic",
            "`CV.walk` -> fresh `Fabric.load` experiment tested the storage layer itself.",
            "",
            f"- input `docid_raw` Python value: `{VALUE!r}`",
            f"- value after fresh reload: `{reloaded!r}`",
            f"- exact equality: **{preserved}**",
            "",
            "This tests the pinned Text-Fabric 13.1.0 writer and reader, not merely the",
            "converter's in-memory feature dictionary.",
            "",
        )
    )
    report_path.write_text(text + "\n" + section, encoding="utf8")
    print(f"input={VALUE!r} reloaded={reloaded!r} preserved={preserved}")
    if not preserved:
        raise SystemExit("Text-Fabric did not preserve the trailing space")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
