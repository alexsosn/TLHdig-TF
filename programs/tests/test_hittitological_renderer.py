"""RED contract for issue #42: sign-local Hittitological rendering."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
APP_FILE = ROOT / "app" / "app.py"
CSS_FILE = ROOT / "app" / "static" / "display.css"

SEMANTIC_CLASSES = {
    "tlh-sgr",
    "tlh-agr",
    "tlh-det",
    "tlh-num",
    "tlh-missing",
    "tlh-laes",
    "tlh-ras",
    "tlh-add",
    "tlh-corr",
    "tlh-subscr",
    "tlh-materlect",
    "tlh-surplus",
}


def load_app_module():
    spec = importlib.util.spec_from_file_location("tlhdig_tf_renderer_app", APP_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Feature:
    def __init__(self, values=None):
        self.values = values or {}

    def v(self, node):
        return self.values.get(node)


class _F:
    pass


class _Text:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def text(self, node, fmt=None, **kwargs):
        self.calls.append((node, fmt, kwargs))
        return self.values.get((node, fmt), "")


class _RendererApp:
    pass


def fake_renderer_app(feature_values=None, text_values=None, missing_features=()):
    feature_values = feature_values or {}
    F = _F()
    for feature in (
        "sgr",
        "agr",
        "det",
        "num",
        "missing",
        "laes",
        "ras",
        "add",
        "corr",
        "subscr",
        "materlect",
        "surplus",
    ):
        if feature not in missing_features:
            setattr(F, feature, _Feature(feature_values.get(feature, {})))

    app = _RendererApp()
    app.api = SimpleNamespace(F=F, T=_Text(text_values or {}))
    app.context = SimpleNamespace(
        formatCls={
            "text-orig-plain": "txtu",
            "text-orig-full": "txtu",
            "text-trans-test": "txtt",
            "text-cuneiform": "txtn",
        },
        defaultClsOrig="txtu",
    )
    return app


def options(fmt):
    return SimpleNamespace(fmt=fmt)


def test_renderer_api_exists_without_replacing_weblink_adapter():
    appmod = load_app_module()
    assert hasattr(appmod, "sign_state_classes")
    assert hasattr(appmod, "plain_sign")
    assert hasattr(appmod, "pretty_sign")
    assert hasattr(appmod.TfApp, "_install_renderer")
    assert hasattr(appmod.TfApp, "_install_tlhdig_weblink")
    assert hasattr(appmod.TfApp, "reinit")


def test_explicit_zero_flags_are_false_but_nonzero_flags_layer():
    appmod = load_app_module()
    app = fake_renderer_app(
        {
            "sgr": {1: 0, 2: 1},
            "agr": {1: "0", 2: "1"},
            "det": {1: 0, 2: 1},
            "num": {1: "0", 2: "1"},
        }
    )
    assert appmod.sign_state_classes(app, 1) == ()
    assert set(appmod.sign_state_classes(app, 2)) == {
        "tlh-sgr",
        "tlh-agr",
        "tlh-det",
        "tlh-num",
    }


def test_sparse_damage_editorial_and_annotation_states_layer():
    appmod = load_app_module()
    app = fake_renderer_app(
        {
            "missing": {3: "1"},
            "laes": {3: "1"},
            "ras": {3: "1"},
            "add": {3: "1"},
            "corr": {3: "corr <unsafe>"},
            "subscr": {3: "a<b"},
            "materlect": {3: "&lt;del_in/&gt;ḪUR"},
            "surplus": {3: "1"},
        }
    )
    assert set(appmod.sign_state_classes(app, 3)) == {
        "tlh-missing",
        "tlh-laes",
        "tlh-ras",
        "tlh-add",
        "tlh-corr",
        "tlh-subscr",
        "tlh-materlect",
        "tlh-surplus",
    }


def test_missing_feature_apis_fail_gracefully():
    appmod = load_app_module()
    app = fake_renderer_app(
        {"missing": {4: "1"}},
        missing_features=("agr", "det", "corr", "subscr", "materlect", "surplus"),
    )
    assert appmod.sign_state_classes(app, 4) == ("tlh-missing",)


def test_plain_transliteration_uses_requested_stock_text_escapes_and_preserves_separator():
    appmod = load_app_module()
    app = fake_renderer_app(
        {"sgr": {5: 1}, "missing": {5: "1"}},
        {(5, "text-orig-plain"): "<DINGIR>-"},
    )
    html = appmod.plain_sign(app, options("text-orig-plain"), (5, (5, 5)), "sign", False)
    assert "&lt;DINGIR&gt;-" in html
    assert "<DINGIR>" not in html
    assert 'class="txtu tlh-sign tlh-sgr tlh-missing"' in html
    assert app.api.T.calls == [(5, "text-orig-plain", {})]


def test_annotation_values_never_become_classes_or_unescaped_html():
    appmod = load_app_module()
    raw = '<script>alert("x")</script>'
    app = fake_renderer_app(
        {"subscr": {6: raw}, "corr": {6: "class-breakout\" onclick=bad"}},
        {(6, "text-orig-full"): "ku-"},
    )
    html = appmod.plain_sign(app, options("text-orig-full"), (6, (6, 6)), "sign", False)
    assert "tlh-subscr" in html and "tlh-corr" in html
    assert raw not in html
    assert "class-breakout" not in html
    assert "onclick" not in html


def test_non_transliteration_format_is_not_replaced_with_transliteration_semantics():
    appmod = load_app_module()
    app = fake_renderer_app(
        {"sgr": {7: 1}, "missing": {7: "1"}},
        {(7, "text-cuneiform"): "𒀭"},
    )
    html = appmod.plain_sign(app, options("text-cuneiform"), (7, (7, 7)), "sign", False)
    assert "𒀭" in html
    assert 'class="txtn tlh-sign"' in html
    assert "tlh-sgr" not in html
    assert "tlh-missing" not in html


def test_pretty_hook_adds_fixed_classes_without_replacing_text():
    appmod = load_app_module()
    app = fake_renderer_app({"det": {8: 1}, "laes": {8: "1"}})
    cls = {"container": "contnr c0", "label": "lbl c0", "children": ""}
    result = appmod.pretty_sign(app, 8, "sign", cls)
    assert result is None
    assert "tlh-sign" in cls["container"]
    assert "tlh-det" in cls["container"]
    assert "tlh-laes" in cls["container"]
    assert cls["label"] == "lbl c0"


def test_renderer_installer_scopes_hooks_to_sign_only():
    appmod = load_app_module()
    app = fake_renderer_app()
    app.customMethods = SimpleNamespace(plainCustom={}, prettyCustom={})
    appmod.install_renderer(app)
    assert set(app.customMethods.plainCustom) == {"sign"}
    assert set(app.customMethods.prettyCustom) == {"sign"}
    assert app.customMethods.plainCustom["sign"].__self__ is app
    assert app.customMethods.prettyCustom["sign"].__self__ is app


def test_css_has_a_selector_for_every_renderer_semantic_class():
    css = CSS_FILE.read_text(encoding="utf8")
    for cls in SEMANTIC_CLASSES | {"tlh-sign"}:
        assert f".{cls}" in css, f"RED: stylesheet has no selector for {cls}"
    assert "That is not written yet" not in css
