"""Beta 0.4 source morphology census gate; do not silently raise global tolerance."""
from collections import Counter
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check_morph import gate_problems


def baseline():
    stats = Counter(file_ok=24128, file_unparseable=3, analyses=1640230,
                    parse_failed=998, selector_dangling=47)
    reasons = Counter({"base has 2 field(s)":974,
                       "base has 6 fields":22, "base has 1 field(s)":2})
    return stats, reasons


def test_measured_source_anomalies_are_allowed():
    stats, reasons = baseline()
    assert gate_problems(stats, reasons) == []


def test_new_failure_shape_is_rejected_even_when_total_does_not_increase():
    stats, reasons = baseline()
    reasons["base has 2 field(s)"] -= 1
    reasons["clitic has 5 fields"] = 1
    assert gate_problems(stats, reasons)


def test_unknown_controls_and_additional_dangling_selectors_fail():
    stats, reasons = baseline()
    stats["unknown_control"] = 1
    assert gate_problems(stats, reasons)
    stats["unknown_control"] = 0
    stats["selector_dangling"] += 1
    assert gate_problems(stats, reasons)


def test_missing_document_or_analysis_is_not_a_pass():
    stats, reasons = baseline()
    stats["file_ok"] -= 1
    assert gate_problems(stats, reasons)
    stats, reasons = baseline()
    stats["analyses"] -= 1
    assert gate_problems(stats, reasons)


def test_class_improvement_is_allowed_when_coverage_is_unchanged():
    stats, reasons = baseline()
    reasons["base has 2 field(s)"] -= 1
    stats["parse_failed"] -= 1
    assert not gate_problems(stats, reasons)
