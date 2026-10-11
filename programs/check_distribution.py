#!/usr/bin/env python3
"""Gate: bare clean-user acquisition must resolve the current TF artifact (#47).

Asserts the repository-side resolution contract documented in
``docs/research-distribution-acquisition.md``: a clean user with no checkout specifier
must not silently receive a stale generated artifact.

This queries the GitHub REST API directly rather than through Text-Fabric's optional
``[github]`` backend, so the gate runs under the pinned ``requirements.txt`` and keeps
"backend not installed" from masking "resolves the wrong version".
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import TF_VERSION  # noqa: E402
import distribution  # noqa: E402
from tlhdig.paths import REPORTS  # noqa: E402

API = "https://api.github.com"
STATUS = REPORTS / "distribution-status.json"
UA = "TLHdig-TF distribution gate/1"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("ordinary", "release"), default="ordinary")
    parser.add_argument("--org", default=distribution.ORG)
    parser.add_argument("--repo", default=distribution.REPO)
    parser.add_argument("--status", type=Path, default=STATUS)
    parser.add_argument(
        "--tf-version",
        default=TF_VERSION,
        help="the current artifact version bare acquisition must reach",
    )
    return parser


def _get(url: str, *, timeout: float = 30.0) -> bytes:
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        if exc.code == 404:
            raise FileNotFoundError(url) from exc
        raise distribution.BackendUnavailable(f"{url}: {exc}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise distribution.BackendUnavailable(f"{url}: {exc}") from exc


def _json(url: str) -> dict:
    return json.loads(_get(url).decode("utf8"))


def _pin_installed_tf_semantics() -> str | None:
    """Fail loudly if the pinned Text-Fabric stops resolving bare the way we assume."""
    try:
        from tf.advanced.repo import fromString
    except Exception:
        return None
    return distribution.bare_resolution_order(fromString)


def manifest_output_digest(data: bytes) -> str:
    """Read an existing BUILD-MANIFEST output fingerprint, fail closed."""
    import re
    try:
        value = json.loads(data.decode("utf8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("malformed current artifact BUILD-MANIFEST") from exc
    if not isinstance(value, dict):
        raise ValueError("current artifact BUILD-MANIFEST must be an object")
    outputs = value.get("outputs")
    if (not isinstance(outputs, dict)
            or outputs.get("algorithm") != "tlhdig-current-tree-v2"):
        raise ValueError("missing or unsupported current output identity")
    digest = outputs.get("digest")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("current output digest is missing or malformed")
    return digest


def current_artifact_digest(org: str, repo: str, version: str) -> str:
    """Pin remote default-branch SHA before reading its current artifact."""
    info = _json(f"{API}/repos/{org}/{repo}")
    default = info.get("default_branch")
    if not isinstance(default, str) or not default:
        raise ValueError("repository has no default branch")
    from urllib.parse import quote
    branch = _json(f"{API}/repos/{org}/{repo}/branches/{quote(default, safe='')}")
    sha = (branch.get("commit") or {}).get("sha")
    if not isinstance(sha, str) or len(sha) != 40:
        raise ValueError("cannot pin current default branch")
    url = f"https://raw.githubusercontent.com/{org}/{repo}/{sha}/tf/{version}/BUILD-MANIFEST.json"
    try:
        manifest = _get(url)
    except FileNotFoundError as exc:
        raise ValueError("current default branch lacks the expected BUILD-MANIFEST") from exc
    return manifest_output_digest(manifest)


def latest_release(org: str, repo: str) -> distribution.LatestRelease | None:
    """The GitHub latest release, or None when none is published.

    GitHub defines this endpoint as the most recent non-draft, non-prerelease release,
    so a prerelease-only repository correctly reports none.
    """
    try:
        release = _json(f"{API}/repos/{org}/{repo}/releases/latest")
    except FileNotFoundError:
        return None

    tag = release["tag_name"]
    commit = _json(f"{API}/repos/{org}/{repo}/git/ref/tags/{tag}")["object"]
    sha = commit["sha"]
    if commit.get("type") == "tag":  # annotated tag: dereference to the commit
        sha = _json(f"{API}/repos/{org}/{repo}/git/tags/{sha}")["object"]["sha"]

    declared = None
    try:
        config = _get(
            f"https://raw.githubusercontent.com/{org}/{repo}/{sha}/app/config.yaml"
        ).decode("utf8")
    except FileNotFoundError:
        config = None
    if config is not None:
        import yaml

        parsed = yaml.safe_load(config) or {}
        declared = (parsed.get("provenanceSpec") or {}).get("version")

    try:
        listing = _json(f"{API}/repos/{org}/{repo}/contents/tf?ref={sha}")
        dirs = tuple(
            sorted(item["name"] for item in listing if item.get("type") == "dir")
        )
    except FileNotFoundError:
        dirs = ()

    # Read the tagged artifact's identity from its immutable Git commit.
    # A release asset's bytes are not established by this Git-tree check;
    # publish_release must separately verify the uploaded ZIP.
    output_digest = None
    if isinstance(declared, str) and declared in dirs:
        url = (
            f"https://raw.githubusercontent.com/{org}/{repo}/{sha}"
            f"/tf/{declared}/BUILD-MANIFEST.json"
        )
        try:
            output_digest = manifest_output_digest(_get(url))
        except (ValueError, FileNotFoundError):
            pass  # Missing/corrupt manifest -> explicit nonmatching release.

    return distribution.LatestRelease(
        tag=tag, commit=sha, declared_tf_version=declared,
        version_dirs=dirs, output_digest=output_digest,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    order = _pin_installed_tf_semantics()
    if order is not None and order != distribution.RELEASE_FIRST:
        print(f"FAIL: unexpected bare resolution order {order!r}", file=sys.stderr)
        return 1

    try:
        latest = latest_release(args.org, args.repo)
        # Do not hide a proven wrong-version release behind a network skip:
        # current identity is needed only for an otherwise plausible release.
        current_digest = None
        if (latest is not None
                and latest.declared_tf_version == args.tf_version
                and args.tf_version in latest.version_dirs):
            current_digest = current_artifact_digest(
                args.org, args.repo, args.tf_version
            )
        result = distribution.evaluate(
            latest, tf_version=args.tf_version,
            current_output_digest=current_digest,
        )
    except distribution.BackendUnavailable as exc:
        result = distribution.unavailable(str(exc))
    except ValueError as exc:
        result = distribution.Result(
            state=distribution.FAILED, resolves_to="unknown",
            detail=f"artifact identity cannot be established: {exc}",
        )

    distribution.write_status(args.status, result, mode=args.mode)

    label = {
        distribution.PASSED: "OK",
        distribution.FAILED: "FAIL",
        distribution.SKIPPED_UNAVAILABLE: "SKIP",
    }[result.state]
    print(f"{label}: bare acquisition -> {result.resolves_to}: {result.detail}")

    code = distribution.exit_code(result.state, mode=args.mode)
    if code == 2:
        print(
            "release mode does not accept an availability skip",
            file=sys.stderr,
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
