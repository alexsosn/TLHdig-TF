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


def test_two_genuinely_valid_compound_placements_withhold_both_readings():
    """Unlike a merely impossible arrangement, *both* parse paths really exist.

    With one discarded leading shade, three identical glyphs can be consumed
    as either (two, one) or (one, two); an arbitrary greedy choice would be
    a false source assertion for both readings.
    """
    glyph = "𒀀"
    raw = "▒" + glyph * 3
    readings = ["PAIR", "PAIR"]
    compounds = {"PAIR": glyph * 2}
    assert _tiny_exhaustive_oracle(raw, readings, compounds) == [None, None]
    assert cuneiform._absorb_compound(
        cuneiform.split_points(raw), readings, compounds
    ) == [None, None]
    assert cuneiform.align(raw, readings, damaged=True, multi=compounds) is None


def test_new_real_case_rs18115_compound_prefix_bleed_is_withheld():
    """#157 RED: source-addressed changed-sign case from run 38158200358.

    RS 18.115 Rs. 22′ (line 6485022): candidate gives MEŠ 𒈨
    immediately followed by ša 𒌍, though 𒈨𒌍 is the attested
    compound MEŠ; structural uniqueness did NOT certify the reading.
    A different MEŠ earlier on this same line is correctly compound.
    """
    readings = ["DUMU", "MEŠ", "KUR", "URU", "LÚ", "MEŠ", "ša", "…"]
    values = ["𒌉", "𒈨𒌍", "𒆳", "𒌷", "𒇽", "𒈨", "𒌍", "𒊭"]
    result = cuneiform._withhold_split_compounds(values, readings, ME_SH)
    assert result == ["𒌉", "𒈨𒌍", "𒆳", "𒌷", "𒇽", None, None, None]


def test_split_compound_prefix_not_withheld_without_full_suffix():
    """A merely shared prefix is not evidence of a wrongly split compound."""
    values = ["𒈨", "𒊭", "𒀀"]
    assert cuneiform._withhold_split_compounds(
        values, ["MEŠ", "ša", "a"], ME_SH
    ) == values


def test_three_character_compound_split_over_multiple_slots_withheld():
    readings = ["SAGI", "ša", "a", "ba"]
    values = ["𒋡", "𒋗", "𒂃", "𒁀"]
    assert cuneiform._withhold_split_compounds(
        values, readings, {"SAGI": "𒋡𒋗𒂃"}
    ) == [None, None, None, None]  # no hard anchor; ba may also be shifted


def test_complete_later_compound_is_independent_resynchronization_anchor():
    """RED #157: a *full* unrelated compound can anchor a safe trailing span."""
    values = ["𒈨", "𒌍", "𒋡𒋗𒂃", "𒁀"]
    readings = ["MEŠ", "ša", "SAGI", "ba"]
    compounds = {"MEŠ": "𒈨𒌍", "SAGI": "𒋡𒋗𒂃"}
    assert cuneiform._withhold_split_compounds(values, readings, compounds) == [
        None, None, "𒋡𒋗𒂃", "𒁀"
    ]


def test_prefix_safety_only_runs_in_mixed_damage_compound_path(monkeypatch):
    """RED: even when original DP returns a unique but suspect assignment."""
    monkeypatch.setattr(cuneiform, "_absorb", lambda points, syms: None)
    monkeypatch.setattr(
        cuneiform, "_absorb_compound",
        lambda points, syms, multi: ["𒈨", "𒌍", "𒀀𒁀"],
    )
    got = cuneiform.align(
        "▒𒈨𒌍𒀀𒁀", ["MEŠ", "ša", "PAIR"], damaged=True,
        multi={"MEŠ": "𒈨𒌍", "PAIR": "𒀀𒁀"},
    )
    assert got is not None and got.level == 3
    assert got.values == [None, None, "𒀀𒁀"]


def test_compound_split_withholds_until_next_explicit_damage_anchor():
    """#157 RED: nearby post-split sign slots can be systematically shifted."""
    values = ["𒈨", "𒌍", "𒅆", "𒁍", "▒", "𒌉", "𒈨𒌍"]
    readings = ["MEŠ", "ši", "bu", "ti", "x", "DUMU", "MEŠ"]
    assert cuneiform._withhold_split_compounds(values, readings, ME_SH) == [
        None, None, None, None, "▒", "𒌉", "𒈨𒌍"
    ]


def test_source_rs18115_rs22_end_to_end_compound_prefix_shift():
    """Real published XML, line 6485022: no MEŠ→𒈨, ša→𒌍 assertion.

    The line and readings are taken from RS 18.115.xml, reverse 22′, and
    the ordered sign nodes 1069..1081 in hosted #155 candidate JSONL.
    The source spells BOTH DUMU.MEŠ and LÚ.MEŠ with 𒈨𒌍.
    """
    cu = "𒌉𒈨𒌍𒆳𒌷𒋼𒀀𒂵𒈩𒋡𒁺𒇽𒈨𒌍𒊭▒▒▒"
    readings = [
        "DUMU", "MEŠ", "KUR", "URU", "Kar", "ga", "miš",
        "ka₄", "du", "LÚ", "MEŠ", "ša", "…",
    ]
    result = cuneiform.align(
        cu, readings, damaged=True,
        multi={"MEŠ": "𒈨𒌍", "Kar": "𒋼𒀀"},
    )
    assert result is not None
    assert result.level == 3
    assert result.values[1] == "𒈨𒌍"  # earlier, correctly anchored compound
    assert result.values[9] == "𒇽"
    assert result.values[10:] == [None, None, None]


def test_source_rs18115_rs34_end_to_end_damaged_shift():
    """Real published RS 18.115 reverse 34′, line 6485034."""
    cu = "𒅇𒇽𒈨𒌍𒁮𒃼𒀀𒈾𒇽𒈨𒌍𒅆𒁍𒋾▒▒▒"
    readings = [
        "ù", "LÚ", "MEŠ", "DAM", "GÀR", "a", "na",
        "LÚ", "MEŠ", "ši", "bu", "ti", "…",
    ]
    result = cuneiform.align(
        cu, readings, damaged=True, multi=ME_SH,
    )
    assert result is not None
    assert result.level == 3
    assert result.values[2] == "𒈨𒌍"  # trustworthy earlier compound
    assert result.values[7] == "𒇽"
    assert result.values[8:] == [None] * 5
