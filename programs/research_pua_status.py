#!/usr/bin/env python
"""Issue #20 research-only mapping-status layer over the measured PUA inventory.

This deliberately distinguishes direct external mapping evidence from corpus-internal
alignment evidence.  A legacy PUA code point is *not* called mapped merely because the
current TF graph overwhelmingly aligns it with a known reading.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SOURCE = REPORTS / "research-pua-inventory.json"
OUT = REPORTS / "research-pua-mapping.json"

HITTYPE_PACKAGE = "https://ctan.org/pkg/hittype"
HITTYPE_SIGN_LIST = "https://tug.ctan.org/fonts/hittype/Documentation/hittitesignlist.pdf"
HITTYPE_VERSION = "2.3 (2026-06-09)"

# Current HitType/HPM evidence.  Only U+100000 is directly named by the current sign
# list as a PUA code point.  For the others, the 2021 update names a *new standard
# Unicode code point* for the sign that our structurally derived corpus alignment sees
# at the old PUA value.  That is strong migration evidence, but it is not a direct
# historical crosswalk and therefore remains ambiguous at the research gate.
EVIDENCE = {
    "U+100000": {
        "researchStatus": "mapped-deliberate-pua",
        "sign": "SI×SÁ",
        "hzl": "28",
        "standardUnicode": None,
        "externalEvidence": "Current HitType sign list explicitly retains U+100000 as SI×SÁ (HZL 28) in Supplementary Private Use Area B.",
    },
    "U+100001": {
        "researchStatus": "ambiguous-legacy-pua",
        "sign": "KA×ÚR",
        "hzl": "137",
        "standardUnicode": "U+12387",
        "externalEvidence": "HitType Update 2021 assigns standard U+12387 to KA×ÚR (HZL 137), but the current list does not explicitly state that historical U+100001 was KA×ÚR.",
    },
    "U+100003": {
        "researchStatus": "ambiguous-legacy-pua",
        "sign": "KA×GIŠ",
        "hzl": "139",
        "standardUnicode": "U+12380",
        "externalEvidence": "HitType Update 2021 assigns standard U+12380 to KA×GIŠ (HZL 139), but the current list does not explicitly state that historical U+100003 was KA×GIŠ.",
    },
    "U+100005": {
        "researchStatus": "ambiguous-legacy-pua",
        "sign": "KA×ÀŠ",
        "hzl": "150",
        "standardUnicode": "U+1237F",
        "externalEvidence": "HitType Update 2021 assigns standard U+1237F to KA×ÀŠ (HZL 150), but the current list does not explicitly state that historical U+100005 was KA×ÀŠ.",
    },
    "U+100006": {
        "researchStatus": "ambiguous-legacy-pua",
        "sign": "AMAR×KU₆",
        "hzl": "276",
        "standardUnicode": "U+12372",
        "externalEvidence": "HitType Update 2021 assigns standard U+12372 to AMAR×KU₆ (HZL 276), but the current list does not explicitly state that historical U+100006 was AMAR×KU₆.",
    },
    "U+100009": {
        "researchStatus": "ambiguous-legacy-pua",
        "sign": "EZEN₄",
        "hzl": "107",
        "standardUnicode": "U+12378",
        "externalEvidence": "HitType Update 2021 assigns standard U+12378 to EZEN₄ (EZEN×ŠE, HZL 107); U+100009 is absent from the current sign list, so the old-PUA crosswalk is not directly documented there.",
    },
}


def _dominant(row: dict) -> dict | None:
    rows = row.get("topAssignedReadings") or []
    if not rows:
        return None
    top = rows[0]
    total = int(row.get("alignedAssignments") or 0)
    count = int(top.get("count") or 0)
    return {
        "reading": top.get("reading"),
        "count": count,
        "alignedAssignments": total,
        "share": round(count / total, 6) if total else None,
    }


def main() -> int:
    raw = json.loads(SOURCE.read_text(encoding="utf8"))
    codepoints = raw.get("codepoints") or {}
    enriched = {}
    for cp, row in sorted(codepoints.items()):
        evidence = EVIDENCE.get(cp)
        if evidence is None:
            evidence = {
                "researchStatus": "unknown-pua",
                "sign": None,
                "hzl": None,
                "standardUnicode": None,
                "externalEvidence": "No current pinned external mapping evidence recorded by issue #20 research.",
            }
        enriched[cp] = {
            "codepoint": cp,
            "occurrencesInSourceCu": row.get("occurrencesInSourceCu", 0),
            "occurrencesInTfCu": row.get("occurrencesInTfCu", 0),
            "linesInTfCu": row.get("linesInTfCu", 0),
            "alignedAssignments": row.get("alignedAssignments", 0),
            "level0Occurrences": (row.get("alignmentLevelOccurrences") or {}).get("0", 0),
            "mixedAssignedValues": row.get("mixedAssignedValues") or [],
            "dominantAlignedReading": _dominant(row),
            "learnedSignmap": row.get("learnedSignmap") or [],
            **evidence,
            "evidenceSources": {
                "measurement": "reports/research-pua-inventory.json",
                "externalPackage": HITTYPE_PACKAGE,
                "externalSignList": HITTYPE_SIGN_LIST,
                "externalVersion": HITTYPE_VERSION,
            },
        }

    payload = {
        "schema": 1,
        "issue": 20,
        "tfVersion": raw.get("tfVersion"),
        "statusVocabulary": {
            "mapped-deliberate-pua": "Current pinned external source directly maps this PUA code point to a sign and intentionally retains it as PUA.",
            "ambiguous-legacy-pua": "Corpus evidence strongly identifies a sign and the current external source gives that sign a standard Unicode code point, but no direct historical PUA crosswalk was found in the pinned current source.",
            "unknown-pua": "No pinned mapping evidence currently identifies the PUA value.",
        },
        "codepoints": enriched,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print("PUA RESEARCH STATUS")
    for cp, row in enriched.items():
        dominant = row["dominantAlignedReading"]
        suffix = ""
        if dominant:
            suffix = f"; graph={dominant['reading']} {dominant['count']}/{dominant['alignedAssignments']}"
        print(f"{cp}: {row['researchStatus']}; sign={row['sign'] or '-'}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
