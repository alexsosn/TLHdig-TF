"""Fail-closed Git-ref validation for canonical certification publication."""
from __future__ import annotations

import argparse
import sys


_BRANCH_PREFIX = "refs/heads/"


class CertificationRefError(ValueError):
    """Raised when certification is asked to publish outside a branch ref."""


def certification_branch(ref_type: str, ref: str) -> str:
    """Return the branch name only for a validated fully-qualified branch ref."""
    if ref_type != "branch":
        raise CertificationRefError(
            f"certification publication requires ref_type=branch, got {ref_type!r}"
        )
    if not ref.startswith(_BRANCH_PREFIX):
        raise CertificationRefError(
            f"certification publication requires a {_BRANCH_PREFIX!r} ref, got {ref!r}"
        )
    branch = ref[len(_BRANCH_PREFIX) :]
    if not branch:
        raise CertificationRefError("certification publication branch is empty")
    return branch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a GitHub Actions ref for certification publication."
    )
    parser.add_argument("ref_type")
    parser.add_argument("ref")
    args = parser.parse_args(argv)
    try:
        branch = certification_branch(args.ref_type, args.ref)
    except CertificationRefError as exc:
        print(f"certification ref rejected: {exc}", file=sys.stderr)
        return 2
    print(branch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
