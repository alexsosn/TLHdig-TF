"""Release-policy RED for issue #18 manuscript graph conservation."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import release_check


def test_manuscript_conservation_remains_required_by_current_release():
    assert release_check.release_policy.POLICY == "release-v4"
    gates = {gate.name: gate.command for gate in release_check.GATES}
    assert gates["manuscript-joins"] == (
        "python",
        "programs/check_manuscript_joins.py",
    )
    assert "manuscript-joins" in release_check.release_policy.REQUIRED_GATES
    assert tuple(gate.name for gate in release_check.GATES) == release_check.release_policy.REQUIRED_GATES
