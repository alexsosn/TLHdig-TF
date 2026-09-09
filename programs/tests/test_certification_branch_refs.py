"""#82: canonical certification publication is branch-only and fail-closed."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "certify-dataset.yml"
HELPER = ROOT / "programs" / "tlhdig" / "certification_ref.py"


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf8")


def _helper():
    assert HELPER.is_file(), "branch-ref validator must exist before publication is trusted"
    spec = importlib.util.spec_from_file_location("certification_ref_under_test", HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("ref_type", "ref", "expected"),
    [
        ("branch", "refs/heads/main", "main"),
        ("branch", "refs/heads/release/candidate", "release/candidate"),
        ("branch", "refs/heads/same-name", "same-name"),
    ],
)
def test_branch_refs_are_accepted_without_losing_identity(ref_type, ref, expected):
    assert _helper().certification_branch(ref_type, ref) == expected


@pytest.mark.parametrize(
    ("ref_type", "ref"),
    [
        ("tag", "refs/tags/v1"),
        ("tag", "refs/tags/same-name"),
        ("branch", "refs/tags/same-name"),
        ("branch", "refs/heads/"),
        ("branch", "main"),
        ("", "refs/heads/main"),
    ],
)
def test_non_branch_or_malformed_refs_fail_closed(ref_type, ref):
    module = _helper()
    with pytest.raises(module.CertificationRefError):
        module.certification_branch(ref_type, ref)


def test_push_trigger_is_declaratively_branch_only_and_keeps_paths():
    text = _workflow()
    trigger = text.split("on:\n", 1)[1].split("\n# Only the newest certification", 1)[0]
    assert "  workflow_dispatch:\n" in trigger
    push = trigger.split("  push:\n", 1)[1]
    assert "    branches:\n" in push
    assert '      - "**"\n' in push or "      - '**'\n" in push
    assert "    paths:\n" in push


def test_runtime_ref_validation_precedes_certification_and_publication():
    text = _workflow()
    validate = text.index("- name: Validate certification publication ref")
    certify = text.index("- name: Full release certification of committed artifact")
    publish = text.index("- name: Commit certification evidence")
    assert validate < certify < publish
    block = text[validate:certify]
    assert "GITHUB_REF_TYPE" in block
    assert "GITHUB_REF" in block
    assert "certification_ref" in block
    assert "GITHUB_ENV" in block


def test_publication_targets_only_the_validated_fully_qualified_branch():
    text = _workflow()
    publish = text.split("- name: Commit certification evidence", 1)[1]
    assert 'git push origin "HEAD:refs/heads/${CERT_BRANCH}"' in publish
    assert "HEAD:${GITHUB_REF_NAME}" not in publish
