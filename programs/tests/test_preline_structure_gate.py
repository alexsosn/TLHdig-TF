"""#52 regression: restoring pre-line words retires every top-level word allowance."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_structure
from tlhdig import structure


def test_preline_fix_retires_known_top_level_word_deficit():
    assert structure.KNOWN_WORD_DEFICIT == 0


def test_structure_gate_requires_exact_word_accounting():
    assert check_structure.word_count_problem(10, 10) is None
    assert "deficit 1" in check_structure.word_count_problem(10, 9)
    assert "surplus 1" in check_structure.word_count_problem(10, 11)
