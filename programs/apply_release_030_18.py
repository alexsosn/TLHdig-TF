#!/usr/bin/env python
"""One-shot mechanical release-version update for issue #18.

The RED in test_release_version.py is already demonstrated.  This script changes only
current-release pointers; historical references to immutable 0.2.0 remain untouched.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str, *, expected: int | None = None) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf8")
    found = text.count(old)
    if expected is not None and found != expected:
        raise SystemExit(f"{path}: expected {expected} occurrences of {old!r}, found {found}")
    if not found:
        raise SystemExit(f"{path}: missing {old!r}")
    p.write_text(text.replace(old, new), encoding="utf8")


def main() -> int:
    replace(
        "programs/tlhdig/__init__.py",
        'TF_VERSION = "0.2.0"',
        'TF_VERSION = "0.3.0"',
        expected=1,
    )
    replace(
        "app/config.yaml",
        '  version: "0.1.0"',
        '  version: "0.3.0"',
        expected=1,
    )

    # Every 0.2.0 mention in these two documents is a current loading/path pointer.
    replace("README.md", "0.2.0", "0.3.0")
    replace("docs/AGORA-INTEGRATION.md", "0.2.0", "0.3.0")

    # KNOWN-ISSUES also documents the historical 0.2.0 release, so change only its
    # current-artifact heading here.  Content-level join/status updates are a later
    # documentation gate after the new artifact has real measured counts.
    replace(
        "KNOWN-ISSUES.md",
        "# Known issues in `tf/0.2.0`",
        "# Known issues in `tf/0.3.0`",
        expected=1,
    )

    replace("CITATION.cff", 'version: "0.2.0"', 'version: "0.3.0"', expected=1)
    replace(
        "CITATION.cff",
        "current tf/0.2.0 build",
        "current tf/0.3.0 build",
        expected=1,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
