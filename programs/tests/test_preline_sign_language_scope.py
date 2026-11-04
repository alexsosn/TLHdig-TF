"""#52 RED: the independent sign-language gate must admit the 22 recovered source signs."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig.paths import PROGRAMS


def _checker_module():
    checker = PROGRAMS / "check_sign_language.py"
    spec = importlib.util.spec_from_file_location("check_sign_language_preline_test", checker)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_checker_frozen_source_population_includes_recovered_preline_signs():
    module = _checker_module()
    assert module.TARGET_SOURCE_SIGNS == 3_365_151


def test_checker_freezes_preline_population_explicitly():
    module = _checker_module()
    assert module.TARGET_PRELINE_SIGNS == 22


def test_preline_language_precedence_has_no_later_line_scope():
    module = _checker_module()
    assert module._choose("Akk", None, None, "Hit") == ("word", "Akk")
    assert module._choose(None, None, None, "Hit") == ("text", "Hit")
    assert module._choose(None, None, None, None) == ("absent", None)
