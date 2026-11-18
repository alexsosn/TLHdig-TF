"""TDD RED: word-owned interlinear candidate rows in the native TF browser (#76).

Run these fast, hermetic tests before the full-corpus browser smoke. Real corpus
HTML research is pinned in docs/plan-interlinear-76.md.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app" / "app.py"
CSS = ROOT / "app" / "static" / "display.css"


def app_module():
    spec = importlib.util.spec_from_file_location("interlinear_tlh_app", APP)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Feature:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def v(self, node):
        self.calls.append(node)
        return self.values.get(node)


class Edge:
    def __init__(self, words):
        self.words = words
        self.calls = []

    def f(self, word):
        self.calls.append(word)
        return tuple(self.words.get(word, ()))


def fake_app(
    words=None, indices=None, lemmas=None, glosses=None, morphs=None,
    statuses=None, missing=(),
):
    words = words or {}
    nodes = set(words)
    otypes = {w: "word" for w in nodes}
    otypes[999] = "line"
    features = {
        "otype": Feature(otypes),
        "index": Feature(indices or {}),
        "lemma": Feature(lemmas or {}),
        "gloss": Feature(glosses or {}),
        "morph": Feature(morphs or {}),
        "parse_ok": Feature(statuses or {}),
    }
    F = SimpleNamespace(**{
        name: feature for name, feature in features.items()
        if name not in missing
    })
    E = SimpleNamespace(analyses=Edge(words)) if "analyses" not in missing else SimpleNamespace()
    app = SimpleNamespace(
        api=SimpleNamespace(F=F, E=E),
        customMethods=SimpleNamespace(plainCustom={}, prettyCustom={}, afterChild={}),
    )
    return app, features, getattr(E, "analyses", None)


def test_after_child_is_registered_for_line_with_existing_sign_hooks():
    mod = app_module()
    app, _, _ = fake_app(words={1: [9]})
    mod.install_renderer(app)
    assert set(app.customMethods.plainCustom) == {"sign"}
    assert set(app.customMethods.prettyCustom) == {"sign"}
    assert set(app.customMethods.afterChild) == {"line"}
    callback = app.customMethods.afterChild["line"]
    assert callback.__self__ is app


def test_zero_analysis_and_nonword_children_produce_no_invented_candidate():
    mod = app_module()
    app, features, edge = fake_app(words={1: []})
    assert mod.after_line_child(app, 1) == ""
    assert mod.after_line_child(app, 999) == ""
    assert edge.calls == [1]
    assert features["index"].calls == []


def test_all_alternatives_sorted_by_source_indices_preserve_gaps_and_stable_ties():
    mod = app_module()
    app, features, edge = fake_app(
        words={1: [12, 13, 14, 15]},
        indices={12: 5, 13: 1, 14: 3, 15: 3},
        lemmas={12: "five", 13: "one", 14: "three-A", 15: "three-B"},
        morphs={12: "M5", 13: "M1", 14: "M3A", 15: "M3B"},
    )
    result = mod.after_line_child(app, 1)
    assert result.count('class="tlh-analysis-candidate') == 4
    assert result.index("one") < result.index("three-A") < result.index("three-B") < result.index("five")
    assert result.count("Candidate 3") == 2
    assert "Candidate 2" not in result and "Candidate 4" not in result
    assert edge.calls == [1]
    assert len(features["index"].calls) == 4
    assert len(features["lemma"].calls) == 4


def test_hostile_lemma_gloss_morphology_and_index_are_html_escaped():
    mod = app_module()
    app, _, _ = fake_app(
        words={1: [6]}, indices={6: 2},
        lemmas={6: '<script>alert("x")</script>'},
        glosses={6: 'less & "more"'},
        morphs={6: '<img src=x onerror=alert(1)>'},
    )
    rendered = mod.after_line_child(app, 1)
    assert "<script>" not in rendered and "<img " not in rendered
    assert "&lt;script&gt;" in rendered
    assert "&lt;img" in rendered
    assert "less &amp; &quot;more&quot;" in rendered
    assert 'onerror=' not in rendered.split("<span")[0]


def test_parse_failed_is_explicit_not_hidden_or_automatically_disambiguated():
    mod = app_module()
    app, _, _ = fake_app(
        words={1: [11, 12]},
        indices={11: 1, 12: 2},
        lemmas={11: "first", 12: "second"},
        statuses={11: 0, 12: 1},
    )
    rendered = mod.after_line_child(app, 1)
    assert "first" in rendered and "second" in rendered
    assert rendered.count("Unparsed") == 1
    assert "source selected" not in rendered.lower()
    assert 'aria-label="Morphological candidates"' in rendered


def test_missing_optional_feature_or_edge_api_fails_closed_without_dropping_others():
    mod = app_module()
    app, _, _ = fake_app(
        words={1: [11]},
        indices={11: 7},
        lemmas={11: "lemma"},
        missing=("morph", "gloss", "parse_ok"),
    )
    rendered = mod.after_line_child(app, 1)
    assert "lemma" in rendered and "Candidate 7" in rendered
    no_edge, _, _ = fake_app(words={1: [11]}, missing=("analyses",))
    assert mod.after_line_child(no_edge, 1) == ""


def test_hook_remains_local_and_does_not_iterate_corpus():
    mod = app_module()
    app, features, edge = fake_app(
        words={1: [11, 12]}, indices={11: 1, 12: 2},
        lemmas={11: "one", 12: "two"},
    )
    for _ in range(5):
        assert mod.after_line_child(app, 1)
    assert edge.calls == [1] * 5
    assert features["otype"].calls == [1] * 5
    assert len(features["lemma"].calls) == 10


def test_css_styles_interlinear_structure_and_unparsed_warning_without_only_color():
    css = CSS.read_text(encoding="utf8")
    for cls in ("tlh-word-analyses", "tlh-analysis-candidate", "tlh-analysis-unparsed"):
        assert f".{cls}" in css
    assert "font" in css and "border" in css
