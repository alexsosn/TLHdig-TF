"""TDD for native TF word-owned interlinear morphology (#76).

A candidate block must be a *descendant* of its word: pinned TF 13.1
afterChild['word'] executes after direct rendered sign children, whereas
afterChild['line'] creates wrapping siblings that can detach from words.
See docs/plan-interlinear-76.md and independent PR review #5963971391.
"""
from __future__ import annotations

import importlib.util
from html.parser import HTMLParser
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
    def __init__(self, values):
        self.values = values
        self.calls = []

    def f(self, word):
        self.calls.append(word)
        return tuple(self.values.get(word, ()))


class Slots:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def s(self, word):
        self.calls.append(word)
        return tuple(self.values.get(word, ()))


class Owners:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def u(self, sign, otype=None):
        assert otype == "word"
        self.calls.append(sign)
        return tuple(self.values.get(sign, ()))


def fake_app(
    words=None, slots=None, owners=None, indices=None, lemmas=None,
    glosses=None, morphs=None, statuses=None, missing=(),
):
    words = words if words is not None else {1: [11, 12]}
    slots = slots if slots is not None else {word: [100 + word] for word in words}
    if owners is None:
        owners = {}
        for word, signs in slots.items():
            for sign in signs:
                owners.setdefault(sign, []).append(word)
    otypes = {word: "word" for word in words}
    otypes.update({sign: "sign" for signs in slots.values() for sign in signs})
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
        name: feature for name, feature in features.items() if name not in missing
    })
    edge = Edge(words)
    oslots = Slots(slots)
    E = SimpleNamespace(**{
        name: value for name, value in (("analyses", edge), ("oslots", oslots))
        if name not in missing
    })
    link = Owners(owners)
    api = SimpleNamespace(F=F, E=E)
    if "L" not in missing:
        api.L = link
    app = SimpleNamespace(
        api=api,
        customMethods=SimpleNamespace(plainCustom={}, prettyCustom={}, afterChild={}),
    )
    return app, features, edge, oslots, link


def test_word_hook_registered_without_changing_sign_hooks():
    mod = app_module()
    app, *_ = fake_app()
    mod.install_renderer(app)
    assert set(app.customMethods.plainCustom) == {"sign"}
    assert set(app.customMethods.prettyCustom) == {"sign"}
    assert set(app.customMethods.afterChild) == {"word"}
    callback = app.customMethods.afterChild["word"]
    assert callback.__self__ is app


def test_only_final_direct_sign_emits_inside_word_and_non_sign_is_skipped():
    mod = app_module()
    app, features, edge, oslots, link = fake_app(
        words={1: [11, 12]}, slots={1: [101, 102, 103]},
        indices={11: 1, 12: 2},
    )
    assert mod.after_word_child(app, 101) == ""
    assert mod.after_word_child(app, 102) == ""
    result = mod.after_word_child(app, 103)
    assert result.count("tlh-word-analyses") == 1
    assert mod.after_word_child(app, 999) == ""
    assert edge.calls == [1], "no candidate scan on every sign"
    assert oslots.calls == [1, 1, 1]
    assert link.calls == [101, 102, 103]
    assert len(features["index"].calls) == 2


def test_zero_analysis_nonword_and_ambiguous_owner_are_never_fabricated():
    mod = app_module()
    app, _, edge, _, _ = fake_app(words={1: []})
    assert mod.after_word_child(app, 101) == ""
    assert edge.calls == [1]
    other, _, other_edge, _, _ = fake_app(
        words={1: [11], 2: [12]},
        slots={1: [101], 2: [102]},
        owners={101: [1, 2]},
    )
    assert mod.after_word_child(other, 101) == ""
    assert other_edge.calls == []


def test_all_alternatives_are_sorted_by_source_index_preserving_gaps_and_ties():
    mod = app_module()
    app, features, edge, _, _ = fake_app(
        words={1: [12, 13, 14, 15]},
        indices={12: 5, 13: 1, 14: 3, 15: 3},
        lemmas={12: "five", 13: "one", 14: "three-A", 15: "three-B"},
        morphs={12: "M5", 13: "M1", 14: "M3A", 15: "M3B"},
    )
    result = mod.after_word_child(app, 101)
    assert result.count('class="tlh-analysis-candidate') == 4
    assert result.index("one") < result.index("three-A") < result.index("three-B") < result.index("five")
    assert result.count("Candidate 3") == 2
    assert "Candidate 2" not in result and "Candidate 4" not in result
    assert edge.calls == [1]
    assert len(features["index"].calls) == 4
    assert len(features["lemma"].calls) == 4


class _Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)


def test_hostile_lemma_gloss_and_morphology_are_escaped_in_actual_html():
    mod = app_module()
    app, *_ = fake_app(
        words={1: [6]}, indices={6: 2},
        lemmas={6: '<script>alert("x")</script>'},
        glosses={6: 'less & "more"'},
        morphs={6: '<img src=x onerror=alert(1)>'},
    )
    rendered = mod.after_word_child(app, 101)
    parser = _Tags()
    parser.feed(rendered)
    assert "script" not in parser.tags and "img" not in parser.tags
    assert "&lt;script&gt;" in rendered
    assert "&lt;img" in rendered
    assert "less &amp; &quot;more&quot;" in rendered


def test_parse_failed_candidate_is_explicit_and_no_preferred_guessing():
    mod = app_module()
    app, *_ = fake_app(
        words={1: [11, 12]}, indices={11: 1, 12: 2},
        lemmas={11: "first", 12: "second"},
        statuses={11: 0, 12: 1},
    )
    rendered = mod.after_word_child(app, 101)
    assert "first" in rendered and "second" in rendered
    assert rendered.count("Unparsed") == 1
    assert "source selected" not in rendered.lower()
    assert 'aria-label="Morphological candidates"' in rendered


def test_missing_optional_apis_fail_closed_but_keep_attested_candidate():
    mod = app_module()
    app, *_ = fake_app(
        words={1: [11]}, indices={11: 7}, lemmas={11: "lemma"},
        missing=("morph", "gloss", "parse_ok"),
    )
    assert "Candidate 7" in mod.after_word_child(app, 101)
    for absent in ("analyses", "oslots", "L"):
        no_api, *_ = fake_app(words={1: [11]}, missing=(absent,))
        assert mod.after_word_child(no_api, 101) == ""


def test_per_sign_graph_lookups_are_bounded_by_one_owning_word():
    mod = app_module()
    app, features, edge, oslots, link = fake_app(
        words={1: [11, 12]}, indices={11: 1, 12: 2},
        lemmas={11: "one", 12: "two"},
    )
    for _ in range(5):
        assert mod.after_word_child(app, 101)
    assert edge.calls == [1] * 5
    assert oslots.calls == [1] * 5
    assert link.calls == [101] * 5
    assert features["otype"].calls == [101] * 5
    assert len(features["lemma"].calls) == 10


def test_css_styles_inline_word_owned_rows_and_unparsed_text_without_only_color():
    css = CSS.read_text(encoding="utf8")
    for cls in ("tlh-word-analyses", "tlh-analysis-candidate", "tlh-analysis-unparsed"):
        assert f".{cls}" in css
    assert "flex-basis: 100%" in css, "rows must stay inside the TF word container"
    assert "font" in css and "border" in css
