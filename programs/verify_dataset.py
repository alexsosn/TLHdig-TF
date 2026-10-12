#!/usr/bin/env python3
"""Verify a *downloaded* dataset directory against its own shipped manifest (#47).

``check_build_manifest.py`` verifies a repository checkout: it recomputes input,
executable/config and closed-world output identities, including the optional provenance
module. A user who acquired the data through Text-Fabric has none of that -- only
``tf/<version>/`` and the ``BUILD-MANIFEST.json`` shipped inside the release asset.

This tool answers the narrower question that copy can actually answer: are these the
bytes the manifest says they are? It is deliberately separate from
``check_build_manifest.py``, which is bound by the manifest's own code identity and must
not be edited for consumer tooling.

Usage::

    python programs/verify_dataset.py                     # the repo's current artifact
    python programs/verify_dataset.py ~/text-fabric-data/github/alexsosn/TLHdig-TF/tf/0.4.0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION  # noqa: E402
from tlhdig.build_manifest import _output_sha256  # noqa: E402
from tlhdig.paths import ROOT  # noqa: E402

#: Written by Text-Fabric after a download; never part of the artifact.
TF_ADDED = {"__checkout__.txt"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=ROOT / "tf" / TF_VERSION,
        help="dataset directory containing BUILD-MANIFEST.json",
    )
    return parser


def verify(directory: Path) -> tuple[bool, list[str]]:
    manifest_path = directory / "BUILD-MANIFEST.json"
    if not manifest_path.is_file():
        return False, [f"no BUILD-MANIFEST.json in {directory}"]

    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    declared = manifest.get("tfVersion")
    entries = manifest.get("outputs", {}).get("files", {})
    main = {
        name.split(":", 1)[1]: digest
        for name, digest in entries.items()
        if name.startswith("main:")
    }
    provenance = sorted(
        name.split(":", 1)[1] for name in entries if name.startswith("provenance:")
    )

    present = {
        path.name
        for path in directory.iterdir()
        if path.is_file()
        and path.name != "BUILD-MANIFEST.json"
        and path.name not in TF_ADDED
    }

    problems = []
    for name in sorted(set(main) - present):
        problems.append(f"missing: {name}")
    for name in sorted(present - set(main)):
        problems.append(f"unexpected: {name}")
    for name in sorted(set(main) & present):
        try:
            actual = _output_sha256(directory / name)
        except Exception as exc:  # unreadable, symlink, etc.
            problems.append(f"{name}: {exc}")
            continue
        if actual != main[name]:
            problems.append(f"{name}: bytes differ from the manifest")

    print(f"dataset        {directory}")
    print(f"declared       tf/{declared}")
    print(f"manifest files {len(main)} (main module)")
    print(f"present        {len(present)}")
    print(f"source commit  {manifest.get('codeCommit', '?')}")
    if provenance:
        print(
            f"note           the optional provenance module "
            f"({', '.join(provenance)}) is not part of the main dataset asset and is "
            f"not checked here"
        )
    return not problems, problems


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    ok, problems = verify(args.directory)
    if ok:
        print("OK: every main-module file matches BUILD-MANIFEST.json")
        return 0
    print(f"FAIL: {len(problems)} problem(s)", file=sys.stderr)
    for problem in problems[:20]:
        print(f"  {problem}", file=sys.stderr)
    if len(problems) > 20:
        print(f"  ... and {len(problems) - 20} more", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
