"""Release certification must retrigger when protected test code changes."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_certification_watches_protected_test_tree():
    workflow = (ROOT / ".github" / "workflows" / "certify-dataset.yml").read_text(
        encoding="utf8"
    )
    assert '- "programs/tests/**"' in workflow, (
        "programs/tests is part of the protected executable/test tree, so a test-only "
        "change must invalidate and retrigger canonical release certification"
    )
