"""#68: canonical certification must cancel obsolete runs on the same Git ref."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "certify-dataset.yml"


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf8")


def test_canonical_certification_is_ref_scoped_and_cancellable():
    text = _text()
    marker = "\nconcurrency:\n"
    assert marker in text, "canonical certification needs a top-level concurrency block"
    start = text.index(marker)
    end = text.index("\npermissions:", start)
    block = text[start:end]
    assert "group:" in block
    assert "github.ref" in block, "concurrency must be stable across commits on one ref"
    assert "github.sha" not in block, "SHA-scoped groups cannot cancel obsolete commits"
    assert "cancel-in-progress: true" in block


def test_evidence_publication_remains_non_force_and_non_rebasing():
    text = _text()
    publish = text.split("- name: Commit certification evidence", 1)[1]
    assert 'git push origin "HEAD:refs/heads/${CERT_BRANCH}"' in publish
    assert "HEAD:${GITHUB_REF_NAME}" not in publish
    assert "--force" not in publish
    assert "--force-with-lease" not in publish
    assert "git pull" not in publish
    assert "git rebase" not in publish
