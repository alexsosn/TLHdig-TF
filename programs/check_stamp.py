#!/usr/bin/env python
"""Gate: does BUILD-COMPLETE certify the bytes and, optionally, the full gate run?"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION, stamp
from tlhdig.paths import ROOT


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-full",
        action="store_true",
        help="reject historical digest-only/census-only stamps",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    out = ROOT / "tf" / TF_VERSION
    problem = stamp.check(out, require_full=args.require_full)
    if problem:
        print(f"refusing: {problem}")
        return 1
    fields = stamp.read(out)
    kind = "full release" if fields.get("certification") else "legacy digest-only"
    print(
        f"{kind} stamp verifies {fields.get('features')} features, "
        f"digest {fields.get('digest', '')[:19]}..."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
