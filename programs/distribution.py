"""Clean-user acquisition contract for the one current pre-alpha TF artifact (#47).

A clean user with an empty ``~/text-fabric-data`` cache and no local clone runs
``use("alexsosn/TLHdig-TF")`` or ``tf alexsosn/TLHdig-TF`` with no checkout specifier.
Pinned Text-Fabric 13.1.0 resolves that to *the GitHub latest release if one exists,
otherwise the head of the default branch* -- see ``docs/research-distribution-acquisition.md``
for the exact code path in ``tf/advanced/repo.py``.

This module owns only the resolution contract and its execution policy. It deliberately
does not download a dataset: an unreachable backend must stay distinguishable from an
artifact that resolves to the wrong version.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

PASSED = "passed"
FAILED = "failed"
SKIPPED_UNAVAILABLE = "skipped-unavailable"

ORG = "alexsosn"
REPO = "TLHdig-TF"

#: Resolution targets, as returned by ``tf.advanced.repo.fromString``.
BARE_SPECIFIER = ""
RELEASE_FIRST = "latest-release-then-default-branch-head"


class BackendUnavailable(RuntimeError):
    """The GitHub backend could not be consulted at all."""


@dataclass(frozen=True)
class LatestRelease:
    """The GitHub "latest release": most recent non-draft, non-prerelease release."""

    tag: str
    commit: str
    declared_tf_version: str | None
    version_dirs: tuple[str, ...]
    output_digest: str | None = None


@dataclass(frozen=True)
class Result:
    state: str
    resolves_to: str
    detail: str
    latest_release: LatestRelease | None = None

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "resolves_to": self.resolves_to,
            "detail": self.detail,
            "latest_release": asdict(self.latest_release) if self.latest_release else None,
        }


def bare_resolution_order(from_string) -> str:
    """Pin what the *installed* Text-Fabric does with a bare specifier.

    ``from_string`` is ``tf.advanced.repo.fromString``. It is injected so this stays a
    statement about the pinned dependency rather than a restatement of our own belief.
    """
    commit, release, local = from_string(BARE_SPECIFIER)
    if local is not None:
        raise ValueError(f"bare specifier unexpectedly selects a local copy: {local!r}")
    if release != "" or commit != "":
        raise ValueError(
            "bare specifier no longer requests 'latest release, else latest commit': "
            f"commit={commit!r} release={release!r}"
        )
    return RELEASE_FIRST


def evaluate(
    latest: LatestRelease | None, *, tf_version: str,
    current_output_digest: str | None = None,
) -> Result:
    """Decide whether bare acquisition reaches the current artifact.

    Either there is no latest release, so resolution falls through to the default-branch
    head and therefore to current main; or the latest release itself must declare and
    contain ``tf_version``. Both are acceptable. Silently resolving some other artifact
    is not.
    """
    if latest is None:
        return Result(
            state=PASSED,
            resolves_to="default-branch-head",
            detail=(
                "no GitHub latest release is published, so bare acquisition falls "
                "through to the default-branch head and tracks the current artifact"
            ),
        )

    problems = []
    if latest.declared_tf_version != tf_version:
        problems.append(
            f"its app/config.yaml declares provenanceSpec.version "
            f"{latest.declared_tf_version!r}, not {tf_version!r}"
        )
    if tf_version not in latest.version_dirs:
        present = ", ".join(latest.version_dirs) or "none"
        problems.append(f"it carries no tf/{tf_version} directory (present: {present})")

    # A mutable pre-alpha artifact can change without changing TF_VERSION.
    # A release declaring the right version but pointing at old data is stale.
    # Both fingerprints come from pinned GitHub commit trees, not a caller's
    # locally checked-out branch (which can itself be behind current main).
    import re
    valid = re.compile(r"^sha256:[0-9a-f]{64}$")
    if (not latest.output_digest or not valid.fullmatch(latest.output_digest)
            or not current_output_digest
            or not valid.fullmatch(current_output_digest)):
        problems.append("current/release artifact digest is missing or invalid")
    elif latest.output_digest != current_output_digest:
        problems.append(
            f"release artifact digest {latest.output_digest} does not match "
            f"current main artifact digest {current_output_digest}"
        )

    if problems:
        return Result(
            state=FAILED,
            resolves_to=f"release {latest.tag}",
            detail=(
                f"bare acquisition resolves release {latest.tag} "
                f"({latest.commit[:12]}) instead of the current artifact: "
                + "; ".join(problems)
            ),
            latest_release=latest,
        )

    return Result(
        state=PASSED,
        resolves_to=f"release {latest.tag}",
        detail=(
            f"the published latest release {latest.tag} declares and contains "
            f"tf/{tf_version} and matches current main output digest"
        ),
        latest_release=latest,
    )


def unavailable(reason: str) -> Result:
    return Result(state=SKIPPED_UNAVAILABLE, resolves_to="unknown", detail=reason)


def exit_code(state: str, *, mode: str) -> int:
    """Ordinary CI may skip on an unreachable backend; release mode may not."""
    if mode not in {"ordinary", "release"}:
        raise ValueError("mode must be 'ordinary' or 'release'")
    if state == FAILED:
        return 1
    if mode == "release" and state != PASSED:
        return 2
    return 0


def write_status(path: Path | str, result: Result, *, mode: str) -> None:
    output = {"mode": mode, **result.to_dict()}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
