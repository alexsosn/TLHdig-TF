#!/usr/bin/env python
"""#92 gate: HFR/TLHdig analysis controls must not contaminate TF lexical identity."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tf.fabric import Fabric

from tlhdig import TF_VERSION, morph
from tlhdig.paths import ROOT

# Frozen independently from the pre-build source/TF census in
# reports/research-mrp-markers.json for pinned TLHdig 0.3. Do not derive this from
# morph.CONTROL_FAMILIES: this gate must catch accidental production-grammar drift.
EXPECTED_CONTROL_COUNTS = {
    "①": 403_553,
    "②Ⓐ": 73_523,
    "②Ⓑ": 4_950,
    "②Ⓒⓐ": 115,
    "②Ⓒⓑ": 16,
    "②ⓐⒸ": 1_472,
    "②ⓐⒸⓐ": 34,
    "②ⓐⒸⓢⓣ": 402,
    "②ⓑⒸ": 44,
    "Ⓑ": 2,
    "ⓐⒸ": 44_068,
    "ⓢⓣ": 29,
    "⓶": 334,
    "⓶Ⓒⓐ": 355,
    "⓶Ⓒⓑ": 32,
    "⓶ⓐⒸ": 112,
    "⓶ⓑⒸ": 7_136,
    "⓷": 323,
    "⓷Ⓐ": 5_823,
    "⓷Ⓑ": 303,
    "⓷ⓐⒸ": 52,
}
EXPECTED_CONTROL_ANALYSES = sum(EXPECTED_CONTROL_COUNTS.values())
EXPECTED_CONTROL_VALUES = frozenset(EXPECTED_CONTROL_COUNTS)

# The old-artifact key projection yields 15,853 normalized (lemma, gloss) pairs, but
# six of those have an empty normalized lemma (control-only first fields). convert.py
# intentionally creates lex nodes only for non-empty lemmas, so the independently
# projected emitted count and clean rebuild are 15,847.
EXPECTED_LEX_NODES = 15_847


def main() -> int:
    tf_dir = ROOT / "tf" / TF_VERSION
    TF = Fabric(locations=str(tf_dir), silent="deep")
    api = TF.load(
        "otype lemma mrp_control raw parse_ok lexeme",
        silent="deep",
    )
    if api is False or api is None:
        print(f"morphology-control gate: cannot load {tf_dir}")
        return 1

    F, E = api.F, api.E
    controls = Counter()
    missing_raw = []
    contaminated_analysis = []
    contaminated_lex = []
    unknown_control_values = []

    analyses = F.otype.s("analysis")
    for an in analyses:
        control = F.mrp_control.v(an) or ""
        lemma = F.lemma.v(an) or ""
        if control:
            controls[control] += 1
            if control not in EXPECTED_CONTROL_VALUES and len(unknown_control_values) < 20:
                unknown_control_values.append((an, control))
            if not F.raw.v(an) and len(missing_raw) < 20:
                missing_raw.append(an)

        known, _, unknown = morph.split_control_prefix(lemma)
        if (known or unknown) and len(contaminated_analysis) < 20:
            contaminated_analysis.append((an, lemma, known, unknown))

    lex_nodes = F.otype.s("lex")
    for lex in lex_nodes:
        lemma = F.lemma.v(lex) or ""
        known, _, unknown = morph.split_control_prefix(lemma)
        if (known or unknown) and len(contaminated_lex) < 20:
            contaminated_lex.append((lex, lemma, known, unknown))

    problems = []
    ncontrols = sum(controls.values())
    if ncontrols != EXPECTED_CONTROL_ANALYSES:
        problems.append(
            f"mrp_control assignments {ncontrols:,} != expected "
            f"{EXPECTED_CONTROL_ANALYSES:,}"
        )
    got_values = frozenset(controls)
    if got_values != EXPECTED_CONTROL_VALUES:
        problems.append(
            "mrp_control vocabulary differs: "
            f"missing={sorted(EXPECTED_CONTROL_VALUES - got_values)!r} "
            f"extra={sorted(got_values - EXPECTED_CONTROL_VALUES)!r}"
        )
    expected_counts = Counter(EXPECTED_CONTROL_COUNTS)
    if controls != expected_counts:
        deltas = {
            key: controls[key] - expected_counts[key]
            for key in sorted(got_values | EXPECTED_CONTROL_VALUES)
            if controls[key] != expected_counts[key]
        }
        problems.append(f"mrp_control family counts differ: {deltas!r}")
    if len(lex_nodes) != EXPECTED_LEX_NODES:
        problems.append(
            f"lex nodes {len(lex_nodes):,} != expected {EXPECTED_LEX_NODES:,}"
        )
    if missing_raw:
        problems.append(
            f"control-normalized analyses without raw recovery: {missing_raw!r}"
        )
    if unknown_control_values:
        problems.append(
            f"unknown mrp_control values: {unknown_control_values!r}"
        )
    if contaminated_analysis:
        problems.append(
            f"control-like syntax remains in analysis lemma: {contaminated_analysis!r}"
        )
    if contaminated_lex:
        problems.append(
            f"control-like syntax remains in lex lemma: {contaminated_lex!r}"
        )

    print(f"analysis nodes       : {len(analyses):,}")
    print(f"mrp_control values   : {ncontrols:,} across {len(controls)} families")
    print(f"lex nodes            : {len(lex_nodes):,}")
    if problems:
        for problem in problems:
            print(f"GATE FAIL: {problem}")
        return 1

    print("morphology-control gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
