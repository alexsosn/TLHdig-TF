from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "certify-dataset.yml"


def test_canonical_certification_is_ref_scoped_and_cancels_stale_runs():
    raw = WORKFLOW.read_text(encoding="utf8")
    config = yaml.safe_load(raw)

    concurrency = config.get("concurrency")
    assert isinstance(concurrency, dict), "canonical certification has no concurrency mapping"
    assert concurrency.get("cancel-in-progress") is True

    group = concurrency.get("group")
    assert isinstance(group, str)
    assert "github.ref" in group, "concurrency group must be scoped to the exact triggering ref"
    assert "github.workflow" in group, "concurrency group must include workflow identity"
