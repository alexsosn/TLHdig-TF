#!/usr/bin/env python3
"""Fail-closed checks for the researcher-facing documentation manual."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

PROGRAMS = Path(__file__).resolve().parent
ROOT = PROGRAMS.parent
sys.path.insert(0, str(PROGRAMS))

from tlhdig import TF_VERSION

PUBLIC_PAGES = (
    "index.md",
    "about.md",
    "data-model.md",
    "text-formats.md",
    "editorial.md",
    "identifiers.md",
    "morphology.md",
    "cuneiform.md",
    "provenance.md",
    "quality.md",
    "querying.md",
    "references.md",
)
OPTIONAL_OWNER_PAGES = ("browser.md", "distribution.md")
NAV_TARGETS = tuple(page for page in PUBLIC_PAGES if page != "index.md") + (
    "features/0_home.md",
)

_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
_CURRENT_VERSION_RE = re.compile(
    r"current\s+TF\s+version\s*:\s*`?([0-9]+\.[0-9]+\.[0-9]+)`?",
    re.IGNORECASE,
)
_NODE_MARKER_RE = re.compile(r"<!--\s*tf-node-types:\s*([^>]+?)\s*-->")
_FEATURE_MARKER_RE = re.compile(r"<!--\s*tf-features:\s*([^>]+?)\s*-->")


def _link_target(raw: str) -> str | None:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        raw = raw[1 : raw.index(">")]
    else:
        raw = raw.split(maxsplit=1)[0] if raw else ""
    raw = unquote(raw)
    if not raw or raw.startswith("#"):
        return None
    lower = raw.lower()
    if lower.startswith(("http://", "https://", "mailto:", "tel:")):
        return None
    return raw.split("#", 1)[0]


def markdown_targets(text: str) -> tuple[str, ...]:
    return tuple(
        target
        for match in _LINK_RE.finditer(text)
        if (target := _link_target(match.group(1))) is not None
    )


def _relative_target(root: Path, page: Path, target: str) -> Path:
    return root / target.lstrip("/") if target.startswith("/") else page.parent / target


def _target_exists(path: Path) -> bool:
    return path.exists() or (path.suffix == "" and path.with_suffix(".md").is_file())


def internal_link_problems(root: Path, pages: tuple[Path, ...]) -> list[str]:
    problems: list[str] = []
    for page in pages:
        if not page.is_file():
            continue
        text = page.read_text(encoding="utf8")
        for target in markdown_targets(text):
            resolved = _relative_target(root, page, target)
            if not _target_exists(resolved):
                problems.append(
                    f"{page.relative_to(root)}: broken internal link {target!r}"
                )
    return problems


def _tf_body_values(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    values: set[str] = set()
    body = False
    for raw in path.read_text(encoding="utf8").splitlines():
        if not body:
            if raw == "":
                body = True
            continue
        if not raw:
            continue
        _spec, sep, value = raw.partition("\t")
        if sep and value:
            values.add(value)
    return values


def current_schema(root: Path, tf_version: str) -> tuple[set[str], set[str]]:
    tf_dir = root / "tf" / tf_version
    node_types = _tf_body_values(tf_dir / "otype.tf")
    features = {
        path.stem
        for path in tf_dir.glob("*.tf")
        if path.is_file() and path.stem not in {"otype", "oslots", "otext"}
    }
    provenance = root / "tf-provenance" / tf_version
    if provenance.is_dir():
        features.update(path.stem for path in provenance.glob("*.tf") if path.is_file())
    return node_types, features


def _marker_values(pattern: re.Pattern[str], text: str) -> set[str]:
    values: set[str] = set()
    for match in pattern.finditer(text):
        values.update(part for part in match.group(1).split() if part)
    return values


def check_manual(
    root: Path = ROOT,
    *,
    tf_version: str = TF_VERSION,
    run_feature_check: bool = True,
) -> list[str]:
    root = Path(root)
    docs = root / "docs"
    problems: list[str] = []

    missing = [page for page in PUBLIC_PAGES if not (docs / page).is_file()]
    if missing:
        problems.append("missing public manual pages: " + ", ".join(missing))

    index = docs / "index.md"
    if index.is_file():
        targets = set(markdown_targets(index.read_text(encoding="utf8")))
        absent_nav = [target for target in NAV_TARGETS if target not in targets]
        if absent_nav:
            problems.append("docs/index.md missing navigation: " + ", ".join(absent_nav))

    readme = root / "README.md"
    if not readme.is_file() or "docs/index.md" not in readme.read_text(encoding="utf8"):
        problems.append("README.md does not route readers to docs/index.md")

    pages = tuple(docs / page for page in PUBLIC_PAGES + OPTIONAL_OWNER_PAGES)
    problems.extend(internal_link_problems(root, pages))

    node_types, features = current_schema(root, tf_version)
    for page in pages:
        if not page.is_file():
            continue
        text = page.read_text(encoding="utf8")
        for claimed in _CURRENT_VERSION_RE.findall(text):
            if claimed != tf_version:
                problems.append(
                    f"{page.relative_to(root)}: current TF version {claimed} != {tf_version}"
                )
        bad_nodes = sorted(_marker_values(_NODE_MARKER_RE, text) - node_types)
        if bad_nodes:
            problems.append(
                f"{page.relative_to(root)}: unknown TF node types: " + ", ".join(bad_nodes)
            )
        bad_features = sorted(_marker_values(_FEATURE_MARKER_RE, text) - features)
        if bad_features:
            problems.append(
                f"{page.relative_to(root)}: unknown TF features: " + ", ".join(bad_features)
            )

    data_model = docs / "data-model.md"
    if data_model.is_file() and not _NODE_MARKER_RE.search(data_model.read_text(encoding="utf8")):
        problems.append("docs/data-model.md has no machine-checked tf-node-types marker")
    querying = docs / "querying.md"
    if querying.is_file() and not _FEATURE_MARKER_RE.search(querying.read_text(encoding="utf8")):
        problems.append("docs/querying.md has no machine-checked tf-features marker")

    if run_feature_check and root.resolve() == ROOT.resolve():
        result = subprocess.run(
            [sys.executable, str(PROGRAMS / "build_feature_docs.py"), "--check"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode:
            detail = result.stdout.strip().splitlines()
            suffix = f": {detail[-1]}" if detail else ""
            problems.append("generated feature reference is stale" + suffix)

    return problems


def main() -> int:
    problems = check_manual()
    if problems:
        for problem in problems:
            print(f"docs: ERROR: {problem}")
        return 1
    print(f"documentation manual verified for TF {TF_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
