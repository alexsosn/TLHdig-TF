#!/usr/bin/env python
"""Fetch the locked external sign-reference inputs into git-ignored ``refs/``.

Ordinary mode may report an explicit availability/policy skip without failing the whole
hosted CI job. Release mode treats either skip as failure. Integrity failures always
fail in both modes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import signref_inputs as inputs
from tlhdig.paths import PROGRAMS, REPORTS, ROOT

DEFAULT_LOCK = PROGRAMS / "signrefs.lock.json"
DEFAULT_REFS = ROOT / "refs"
DEFAULT_STATUS = REPORTS / "signrefs-status.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("ordinary", "release"), default="ordinary")
    parser.add_argument("--offline", action="store_true", help="do not attempt network acquisition")
    parser.add_argument("--refresh", action="store_true", help="re-fetch even verified cached files")
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--refs", type=Path, default=DEFAULT_REFS)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        sources = inputs.load_lock(args.lock)
    except inputs.LockError as exc:
        print(f"SIGNREFS INPUT LOCK FAILED: {exc}")
        return 1

    result = inputs.prepare(
        sources,
        args.refs,
        network=not args.offline,
        refresh=args.refresh,
    )
    inputs.write_status(args.status, result, mode=args.mode)
    print(f"SIGNREFS_FETCH_STATUS={result.state}")
    for source in result.sources:
        detail = f" ({source.detail})" if source.detail else ""
        print(f"  {source.name}: {source.state} @ {source.revision} {source.expected_hash}{detail}")
    return inputs.exit_code(result.state, mode=args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
