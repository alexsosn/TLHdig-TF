#!/usr/bin/env python3
"""Publish the current validated artifact as a downloadable GitHub release (#47).

Why a release at all, when pre-alpha policy (#115) keeps one mutable current artifact on
``main``? Because of how Text-Fabric acquires data. ``downloadRelease()`` looks for an
asset named ``tf-<version>.zip`` and fetches that single file; without it, TF falls back
to walking the GitHub contents API file by file, which for this 400 MB dataset is slow
enough to be unusable in practice.

So the release exists purely as a **download accelerator** for the current artifact. It is
not a compatibility promise and carries no certification: see ``docs/RELEASE.md``.

The invariant ``programs/check_distribution.py`` enforces is that a published release must
be *current*. Rebuilding the artifact therefore means re-running this script (one command)
or demoting the release to a prerelease. The gate tells you which is outstanding.

Usage::

    python programs/publish_release.py            # show what would happen
    python programs/publish_release.py --publish   # actually create/replace the release

Requires the ``gh`` CLI, authenticated.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import SOURCE_VERSION, TF_VERSION  # noqa: E402
from tlhdig.paths import ROOT  # noqa: E402

#: Must match Text-Fabric's expected asset name: `relative` ("/tf") flattened, plus
#: the version. See tf/advanced/repo.py::downloadRelease.
ASSET = f"tf-{TF_VERSION}.zip"
TAG = f"tlhdig-{SOURCE_VERSION}_tf-{TF_VERSION}"


def _run(args: list[str], **kwargs) -> str:
    return subprocess.run(
        args, check=True, capture_output=True, text=True, **kwargs
    ).stdout.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--publish",
        action="store_true",
        help="create or replace the release; without it, only report the plan",
    )
    parser.add_argument("--tag", default=TAG)
    parser.add_argument(
        "--notes",
        default=None,
        help="release notes; defaults to a generated pre-alpha notice",
    )
    return parser


def build_asset(dest: Path) -> tuple[Path, int, int]:
    """Zip the current artifact flat, the way Text-Fabric extracts it.

    TF extracts the asset with ``extractall()`` straight into
    ``~/text-fabric-data/.../tf/<version>/``, so members must sit at the zip root with no
    directory prefix. Unlike TF's own ``zipData``, this includes
    ``BUILD-MANIFEST.json``: a dataset that can verify itself is strictly better, and
    ``check_build_manifest.py`` is useless without it.
    """
    source = ROOT / "tf" / TF_VERSION
    if not source.is_dir():
        raise SystemExit(f"no current artifact at {source}")

    files = sorted(
        path
        for path in source.iterdir()
        if path.is_file() and not path.is_symlink()
    )
    if not files:
        raise SystemExit(f"{source} contains no regular files")

    target = dest / ASSET
    with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=6) as zf:
        for path in files:
            zf.write(path, arcname=path.name)

    raw = sum(path.stat().st_size for path in files)
    return target, len(files), raw


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    # Never publish bytes the manifest does not vouch for.
    subprocess.run(
        [sys.executable, str(ROOT / "programs" / "check_build_manifest.py")], check=True
    )

    manifest = json.loads(
        (ROOT / "tf" / TF_VERSION / "BUILD-MANIFEST.json").read_text(encoding="utf8")
    )
    code_commit = manifest["codeCommit"]
    head = _run(["git", "-C", str(ROOT), "rev-parse", "HEAD"])

    # A release must point at a commit the remote actually has, and at one that is on
    # the default branch: bare Text-Fabric acquisition takes app/config.yaml from the
    # release's own commit, so a release targeting an unpushed or side-branch commit
    # would hand clean users an app that does not exist upstream.
    probe = subprocess.run(
        ["gh", "repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"],
        capture_output=True,
        text=True,
    )
    default = probe.stdout.strip() if probe.returncode == 0 and probe.stdout.strip() else "main"
    _run(["git", "-C", str(ROOT), "fetch", "--quiet", "origin", default])
    on_default = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "merge-base",
            "--is-ancestor",
            head,
            f"origin/{default}",
        ]
    ).returncode == 0
    if not on_default:
        raise SystemExit(
            f"refusing: HEAD {head[:12]} is not an ancestor of origin/{default}. "
            f"Push and merge first, then publish the release from the merged commit."
        )

    tmp = Path(tempfile.mkdtemp(prefix="tlhdig-release-"))
    try:
        asset, count, raw = build_asset(tmp)
        packed = asset.stat().st_size

        print(f"tag            {args.tag}")
        print(f"asset          {ASSET}")
        print(f"files          {count}")
        print(f"raw            {raw / 1e6:.1f} MB")
        print(f"compressed     {packed / 1e6:.1f} MB")
        print(f"HEAD           {head}")
        print(f"manifest code  {code_commit}")

        if not args.publish:
            print("\ndry run; pass --publish to create or replace the release")
            return 0

        notes = args.notes or (
            f"Pre-alpha download snapshot of the current Text-Fabric artifact "
            f"`tf/{TF_VERSION}` for upstream TLHdig {SOURCE_VERSION}.\n\n"
            f"This release exists so Text-Fabric can fetch the dataset as a single "
            f"`{ASSET}` asset instead of walking the GitHub contents API. It is **not** "
            f"a compatibility promise and carries no certification; `main` holds one "
            f"mutable current artifact during pre-alpha.\n\n"
            f"Install and load instructions: `docs/install.md`.\n"
            f"Known limitations: `KNOWN-ISSUES.md`.\n\n"
            f"The asset unpacks flat into `tf/{TF_VERSION}/` and includes "
            f"`BUILD-MANIFEST.json`, so `python programs/check_build_manifest.py` can "
            f"verify it."
        )

        existing = subprocess.run(
            ["gh", "release", "view", args.tag, "--json", "tagName"],
            capture_output=True,
            text=True,
        )
        if existing.returncode == 0:
            print(f"\nreplacing existing release {args.tag}")
            _run(["gh", "release", "delete", args.tag, "--yes", "--cleanup-tag"])

        _run(
            [
                "gh",
                "release",
                "create",
                args.tag,
                str(asset),
                "--title",
                args.tag,
                "--notes",
                notes,
                "--latest",
                "--target",
                head,
            ]
        )
        print(f"published {args.tag} with {ASSET}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nverifying clean-user resolution")
    return subprocess.run(
        [sys.executable, str(ROOT / "programs" / "check_distribution.py"), "--mode", "release"]
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
