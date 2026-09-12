#!/usr/bin/env python
"""Research-only probe: can a source slot live in a document before any column/line?"""
from __future__ import annotations

from pathlib import Path
import tempfile

from tf.convert.walker import CV
from tf.fabric import Fabric


def director(cv):
    doc = cv.node("document")
    cv.feature(doc, docid="D")

    pre = cv.slot()
    cv.feature(pre, sym="pre", after=" ")

    col = cv.node("column")
    cv.feature(col, collabel="I")
    line = cv.node("line")
    cv.feature(line, lnno="1")
    body = cv.slot()
    cv.feature(body, sym="body", after="")
    cv.terminate(line)
    cv.terminate(col)
    cv.terminate(doc)


def main() -> int:
    out = Path(tempfile.mkdtemp(prefix="tlhdig-preline-section-"))
    TF = Fabric(locations=str(out), silent="deep")
    cv = CV(TF, silent="deep")
    good = cv.walk(
        director,
        "sign",
        otext={
            "fmt:text-orig-full": "{sym}{after}",
            "sectionTypes": "document,column,line",
            "sectionFeatures": "docid,collabel,lnno",
        },
        generic={"name": "preline-research"},
        intFeatures=set(),
        featureMeta={
            "sym": {"description": "symbol"},
            "after": {"description": "separator"},
            "docid": {"description": "document"},
            "collabel": {"description": "column"},
            "lnno": {"description": "line"},
        },
        warn=False,
    )
    print("walk:", good)
    if not good:
        return 1

    api = Fabric(locations=str(out), silent="deep").loadAll(silent="deep")
    if api is True:
        raise RuntimeError("loadAll returned bool without api")
    if not api:
        print("load: failed")
        return 1

    signs = api.F.otype.s("sign")
    print("signs:", signs)
    for sign in signs:
        print(
            "sign", sign,
            "sym=", api.F.sym.v(sign),
            "section=", api.T.sectionFromNode(sign),
            "up=", [(n, api.F.otype.v(n)) for n in api.L.u(sign)],
        )

    pre, body = signs
    pre_sec = api.T.sectionFromNode(pre)
    body_sec = api.T.sectionFromNode(body)
    problems = []
    # Text-Fabric pads configured missing section levels with None. These values are
    # presentation, not graph ownership: ancestry below is the structural assertion.
    if pre_sec != ("D", None, None):
        problems.append(
            f"pre-line section unexpectedly {pre_sec!r}, expected ('D', None, None)"
        )
    if body_sec != ("D", "I", "1"):
        problems.append(f"normal line section unexpectedly {body_sec!r}")
    pre_types = {api.F.otype.v(n) for n in api.L.u(pre)}
    if "document" not in pre_types:
        problems.append("pre-line slot is not owned by document")
    if "column" in pre_types or "line" in pre_types:
        problems.append(f"pre-line slot was spuriously placed in {pre_types}")

    if problems:
        print("FAIL")
        for problem in problems:
            print("-", problem)
        return 1
    print("PASS: document-only source slot needs no invented column or line")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
