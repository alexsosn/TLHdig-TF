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


def _tiny_exhaustive_oracle(cu, readings, compounds):
    """Independent recursive enumeration of every short legal interpretation.

    Deliberately no reuse of _fits(), _expand(), _absorb(), or production DP.
    For these test inputs one cuneiform point is a Python character.
    """
    interpretations = []

    def recurse(position, index, assigned, removed, compounded):
        if position == len(cu) and index == len(readings):
            if removed and compounded:
                interpretations.append(tuple(assigned))
            return
        if position >= len(cu):
            return
        if cu[position] == "▒":
            recurse(position + 1, index, assigned, True, compounded)
        if index >= len(readings):
            return
        reading = readings[index]
        point = cu[position]
        if (reading == "x") == (point == "▒"):
            recurse(position + 1, index + 1, assigned + [point], removed, compounded)
        longer = compounds.get(reading)
        if longer and len(longer) > 1 and "▒" not in longer and cu.startswith(longer, position):
            recurse(position + len(longer), index + 1,
                    assigned + [longer], removed, True)

    recurse(0, 0, [], False, False)
    if not interpretations:
        return None
    return [
        values[0] if len(set(values)) == 1 else None
        for values in zip(*interpretations)
    ]


def test_production_dp_agrees_with_independent_exhaustive_oracle_on_short_cases():
    cases = [
        ("▒▒𒈨𒌍▒▒", ["x", "MEŠ", "x"]),
        ("▒𒈨𒌍𒈨𒌍", ["MEŠ", "a", "MEŠ"]),
        ("𒀀▒𒈨𒌍", ["a", "MEŠ"]),
        ("▒𒀀𒈨𒌍", ["a", "MEŠ"]),
        ("▒𒈨𒌍▒𒀀", ["MEŠ", "a"]),
        ("𒀀▒𒈨𒌍▒𒁀", ["a", "MEŠ", "ba"]),
        ("𒀀𒁀𒈨𒌍", ["x", "MEŠ"]),
        ("▒▒𒈨𒌍", ["x", "MEŠ"]),
        ("𒈨𒌍▒▒", ["MEŠ", "x"]),
    ]
    for cu, readings in cases:
        expected = _tiny_exhaustive_oracle(cu, readings, ME_SH)
        actual = cuneiform._absorb_compound(
            cuneiform.split_points(cu), readings, ME_SH
        )
        assert actual == expected, (cu, readings, expected, actual)
