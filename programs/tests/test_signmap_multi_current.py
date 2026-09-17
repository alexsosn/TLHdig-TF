"""Regression: the checked-in compound map must satisfy #126 strict preflight."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import cuneiform


PROGRAMS = Path(__file__).resolve().parents[1]


def test_checked_in_compound_map_passes_strict_preflight() -> None:
    problems = cuneiform.validate_multi(PROGRAMS / "signmap-multi.tsv")
    assert problems == [], "\n".join(problems)
