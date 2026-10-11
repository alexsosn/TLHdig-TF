"""Current-validation regression for issue #18 manuscript graph conservation."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate_current


def test_manuscript_conservation_remains_required_by_current_validation():
    gates = {gate.name: gate.command for gate in validate_current.GATES}
    assert gates["manuscript-joins"] == (
        "python",
        "programs/check_manuscript_joins.py",
    )
    assert "manuscript-joins" in tuple(gate.name for gate in validate_current.GATES)
