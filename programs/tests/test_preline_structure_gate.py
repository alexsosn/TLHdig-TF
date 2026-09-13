"""#52 RED: restoring all readable pre-line words retires the old word-loss allowance."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import structure


def test_preline_fix_retires_known_top_level_word_deficit():
    assert structure.KNOWN_WORD_DEFICIT == 0
