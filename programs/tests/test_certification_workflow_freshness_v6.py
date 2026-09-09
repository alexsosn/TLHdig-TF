"""Workflow defense-in-depth contract for release-v6 freshness (#69)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "certify-dataset.yml"

EXPECTED_PATHS = (
    "tf/**/*.tf",
    "tf-provenance/**/*.tf",
    "corpus/**",
    "app/**",
    "programs/**",
    "programs/tests/**",
    "!programs/research_*.py",
    "!programs/shard.txt",
    "requirements.txt",
    ".github/workflows/certify-dataset.yml",
    ".github/workflows/build-final-*.yml",
    ".github/workflows/finalize-issue*.yml",
    ".github/workflows/sync-*.yml",
)


def _push_paths(text: str) -> tuple[str, ...]:
    lines = text.splitlines()
    in_paths = False
    paths_indent = None
    result = []
    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if not in_paths and stripped == "paths:":
            in_paths = True
            paths_indent = indent
            continue
        if not in_paths:
            continue
        if stripped and indent <= int(paths_indent):
            break
        if stripped.startswith("- "):
            result.append(stripped[2:].strip().strip('"').strip("'"))
    return tuple(result)


def test_canonical_certifier_paths_follow_v6_protected_profile_without_regressing_ref_safety():
    text = WORKFLOW.read_text(encoding="utf8")
    assert _push_paths(text) == EXPECTED_PATHS

    # Preserve the independently reviewed #68/#87 safety contracts while broadening
    # freshness scheduling. These are semantic sentinels, not a second YAML parser.
    assert 'branches:\n      - "**"' in text
    assert "group: certify-dataset-${{ github.ref }}" in text
    assert "cancel-in-progress: true" in text
    assert 'tlhdig.certification_ref "$GITHUB_REF_TYPE" "$GITHUB_REF"' in text
    assert 'git push origin "HEAD:refs/heads/${CERT_BRANCH}"' in text
