"""RED regressions: damage placeholders on both sides of compound signs (#21)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tlhdig import cuneiform

ME_SH = {"MEŠ": "𒈨𒌍"}


def test_mixed_alignment_drops_shades_on_both_sides_of_compound():
    result = cuneiform.align(
        "▒▒𒈨𒌍▒▒", ["x", "MEŠ", "x"],
        damaged=True, multi=ME_SH,
    )
    assert result is not None
    assert result.level == 3
    assert result.methods == ("damage", "compound")
    assert result.values == ["▒", "𒈨𒌍", "▒"]


def test_mixed_alignment_preserves_adjacent_legible_readings():
    result = cuneiform.align(
        "𒀀▒▒𒈨𒌍▒▒𒁀", ["a", "x", "MEŠ", "x", "ba"],
        damaged=True, multi=ME_SH,
    )
    assert result is not None
    assert result.values == ["𒀀", "▒", "𒈨𒌍", "▒", "𒁀"]


def test_ambiguous_compound_placement_must_not_guess_signs():
    result = cuneiform.align(
        "▒𒈨𒌍𒈨𒌍", ["MEŠ", "a", "MEŠ"],
        damaged=True, multi=ME_SH,
    )
    assert result is None or all(v is None for v in result.values)


def test_compound_entry_cannot_consume_a_damage_placeholder():
    result = cuneiform.align(
        "▒▒𒀀", ["x", "A"],
        damaged=True, multi={"A": "▒𒀀"},
    )
    assert result is None or all(
        "▒" not in value for value in result.values if value and len(value) > 1
    )


def test_mixed_only_not_equal_count_shortcut():
    result = cuneiform.align("𒀀𒁀", ["a", "ba"], damaged=True, multi=ME_SH)
    assert result is not None
    assert result.level == 1
    assert result.methods == ("zip",)


def test_unexplained_legible_point_remains_unaligned():
    result = cuneiform.align(
        "𒀀𒁀𒈨𒌍", ["x", "MEŠ"], damaged=True, multi=ME_SH
    )
    assert result is None
