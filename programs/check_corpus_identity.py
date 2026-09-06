#!/usr/bin/env python
"""Gate: the frozen source corpus matches its checked-in SHA-256 manifest."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import corpusid
from tlhdig.paths import CORPUS, PROGRAMS


def main() -> int:
    manifest = corpusid.read_manifest(PROGRAMS / "corpus.sha256")
    problems = corpusid.verify(CORPUS, manifest)
    for problem in problems[:20]:
        print(problem)
    if problems:
        print(f"CORPUS IDENTITY FAILED: {len(problems)} problem(s)")
        return 1
    print(f"corpus identity verified: {len(manifest):,} manifest entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
