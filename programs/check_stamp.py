#!/usr/bin/env python
"""Gate: does BUILD-COMPLETE certify the bytes that are actually here?"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, stamp
from tlhdig.paths import ROOT


def main() -> int:
    out = ROOT / "tf" / TF_VERSION
    problem = stamp.check(out)
    if problem:
        print(f"refusing: {problem}")
        return 1
    fields = stamp.read(out)
    print(f"stamp verifies {fields.get('features')} features, digest {fields.get('digest', '')[:19]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
