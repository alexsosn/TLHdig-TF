#!/usr/bin/env python3
"""Build or verify the generated app-facing Text-Fabric feature reference."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROGRAMS = Path(__file__).resolve().parent
ROOT = PROGRAMS.parent
sys.path.insert(0, str(PROGRAMS))

from tlhdig import PROVENANCE_DIR, TF_VERSION
from tlhdig.featuredocs import (
    FeatureDocsError,
    check_tree,
    discover_features,
    render_tree,
    write_tree,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if docs/features differs from the deterministic generated tree",
    )
    args = parser.parse_args(argv)

    core = ROOT / "tf" / TF_VERSION
    provenance = ROOT / PROVENANCE_DIR / TF_VERSION
    output = ROOT / "docs" / "features"

    try:
        features = discover_features(
            core,
            provenance_dir=provenance if provenance.is_dir() else None,
        )
        tree = render_tree(features, version=TF_VERSION)
    except FeatureDocsError as exc:
        print(f"feature docs: ERROR: {exc}", file=sys.stderr)
        return 1

    if args.check:
        problems = check_tree(output, tree)
        for problem in problems:
            print(f"feature docs: {problem}", file=sys.stderr)
        if problems:
            return 1
        print(f"feature docs: ok ({len(tree)} pages)")
        return 0

    write_tree(output, tree)
    print(f"feature docs: wrote {len(tree)} pages to {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
