#!/usr/bin/env python3
"""Read-only census for #126: generated compound sign-map integrity."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from learn_signmap import MAX_SEQ, MIN_CONF, MIN_OBS
from tlhdig import cuneiform
from tlhdig.paths import PROGRAMS


def census(path: Path) -> dict[str, object]:
    rows: list[tuple[int, list[str]]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf8").splitlines(), 1):
        if not raw or raw.startswith("#"):
            continue
        rows.append((lineno, raw.split("\t")))

    problems: list[dict[str, object]] = []
    readings: list[str] = []
    for lineno, parts in rows:
        row_problems: list[str] = []
        if len(parts) != 6:
            row_problems.append(f"expected 6 TSV fields, got {len(parts)}")
            reading = parts[0] if parts else ""
            seq = parts[1] if len(parts) > 1 else ""
        else:
            reading, seq, conf_raw, top_raw, total_raw, _name = parts
            try:
                conf = float(conf_raw)
            except ValueError:
                conf = -1.0
                row_problems.append("confidence is not a float")
            try:
                top = int(top_raw)
                total = int(total_raw)
            except ValueError:
                top = total = -1
                row_problems.append("observation counts are not integers")
            else:
                if total < MIN_OBS:
                    row_problems.append(f"total observations {total} < MIN_OBS {MIN_OBS}")
                if top < 0 or top > total:
                    row_problems.append("top observations outside 0..total")
                if total > 0 and abs(conf - top / total) > 0.0015:
                    row_problems.append("rounded confidence disagrees with top/total")
            if conf < MIN_CONF:
                row_problems.append(f"confidence {conf} < MIN_CONF {MIN_CONF}")

        if not reading:
            row_problems.append("empty reading")
        if len(seq) < 2:
            row_problems.append("sequence has fewer than 2 codepoints")
        if len(seq) > MAX_SEQ:
            row_problems.append(f"sequence has more than MAX_SEQ {MAX_SEQ} codepoints")
        if cuneiform.PLACEHOLDER in seq:
            row_problems.append("sequence contains damage placeholder")
        if not cuneiform.is_sign(seq):
            row_problems.append("sequence contains a non-sign codepoint")

        readings.append(reading)
        if row_problems:
            problems.append({"line": lineno, "reading": reading, "problems": row_problems})

    loaded = cuneiform.load_multi(path)
    duplicate_readings = sorted(k for k, n in Counter(readings).items() if n > 1)
    row_readings = {reading for reading in readings if reading}
    silently_ignored = sorted(row_readings - set(loaded))
    unexpected_loaded = sorted(set(loaded) - row_readings)

    return {
        "path": path.as_posix(),
        "dataRows": len(rows),
        "loaderEntries": len(loaded),
        "duplicateReadings": duplicate_readings,
        "silentlyIgnoredReadings": silently_ignored,
        "unexpectedLoadedReadings": unexpected_loaded,
        "strictProblems": problems,
        "generatorThresholds": {
            "minObservations": MIN_OBS,
            "minConfidence": MIN_CONF,
            "maxSequenceCodepoints": MAX_SEQ,
        },
    }


def main() -> int:
    result = census(PROGRAMS / "signmap-multi.tsv")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
