"""Contract for issue #41: safe links from TF nodes to TLHdig online."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml
from tf.advanced.find import findAppClass

ROOT = Path(__file__).resolve().parents[2]
APP_FILE = ROOT / "app" / "app.py"
PROGRAMS = ROOT / "programs"
sys.path.insert(0, str(PROGRAMS))

from research_weblink_ids import report
from tlhdig import TF_VERSION


def load_app_module():
    assert APP_FILE.exists(), "RED: app/app.py must provide the corpus web-link adapter"
    spec = importlib.util.spec_from_file_location("tlhdig_tf_app", APP_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_released_identity_census_has_all_duplicate_groups():
    data = report(ROOT / "tf" / TF_VERSION)
    assert data["tf_version"] == "0.3.0"
    assert data["duplicate_docid_count"] == 141
    assert data["documents_in_duplicate_groups"] > data["duplicate_docid_count"]


def test_normalize_tlhdig_id_is_conservative():
    appmod = load_app_module()
    assert appmod.normalize_tlhdig_id("KUB 3.74") == "KUB 3.74"
    assert appmod.normalize_tlhdig_id("IBoT 4.229+") == "IBoT 4.229"
    assert appmod.normalize_tlhdig_id("KBo 12.30(+)") is None
    assert appmod.normalize_tlhdig_id("IBoT 4.229++") is None
    assert appmod.normalize_tlhdig_id("") is None


def test_tlhdig_url_encodes_query_values_without_using_node_ids():
    appmod = load_app_module()
    assert appmod.tlhdig_url("KUB 3.74") == "https://hethport.net/TLHdig/tlh_xtx.php?d=KUB+3.74"
    assert appmod.tlhdig_url("Bo 12/34′") == "https://hethport.net/TLHdig/tlh_xtx.php?d=Bo+12%2F34%E2%80%B2"
    # A literal plus inside the identifier must not be reinterpreted as query-space.
    assert appmod.tlhdig_url("A+B") == "https://hethport.net/TLHdig/tlh_xtx.php?d=A%2BB"
    assert appmod.tlhdig_url("KBo 12.30(+)") is None
    assert "5834842" not in appmod.tlhdig_url("KUB 3.74")


def test_config_exposes_hint_but_not_unsafe_stock_url_template():
    cfg = yaml.safe_load((ROOT / "app" / "config.yaml").read_text(encoding="utf8"))
    provenance = cfg["provenanceSpec"]
    assert provenance["webBase"] == "https://hethport.net/TLHdig"
    assert provenance["webHint"] == "Open this text in TLHdig"
    assert "webUrl" not in provenance


def test_text_fabric_discovers_the_custom_app_class():
    cls = findAppClass("tlhdig-weblink-test", str(ROOT / "app"))
    assert cls is not None
    assert cls.__name__ == "TfApp"


class _Feature:
    def __init__(self, values): self.values = values
    def v(self, node): return self.values.get(node)


class _Otype:
    def __init__(self, types, documents): self.types, self.documents = types, tuple(documents)
    def v(self, node): return self.types[node]
    def s(self, node_type):
        assert node_type == "document"
        return self.documents


class _F:
    def __init__(self, types, docids, documents):
        self.otype = _Otype(types, documents)
        self.docid = _Feature(docids)


class _L:
    def __init__(self, owners): self.owners = owners
    def u(self, node, otype=None):
        assert otype == "document"
        return tuple(self.owners.get(node, ()))


class _Api:
    def __init__(self, types, docids, owners, documents):
        self.F = _F(types, docids, documents)
        self.L = _L(owners)


class _FakeApp: pass


def _fake_app():
    app = _FakeApp()
    app.api = _Api(
        types={1:"sign",10:"line",100:"document",101:"document",102:"document",900:"lex",901:"docgroup",902:"sign",903:"sign"},
        docids={100:"KUB 3.74",101:"KUB 26.71",102:"KUB 26.71"},
        owners={1:(100,),10:(100,),902:(),903:(100,101)},
        documents=(100,101,102),
    )
    return app


def test_document_resolution_rejects_ambiguous_and_aggregate_nodes():
    appmod = load_app_module()
    app = _fake_app()
    duplicates = appmod.duplicate_docids(app)
    assert duplicates == {"KUB 26.71"}
    assert appmod.url_for_node(app, 100, duplicates) == "https://hethport.net/TLHdig/tlh_xtx.php?d=KUB+3.74"
    assert appmod.url_for_node(app, 1, duplicates).endswith("d=KUB+3.74")
    assert appmod.url_for_node(app, 101, duplicates) is None
    assert appmod.url_for_node(app, 900, duplicates) is None
    assert appmod.url_for_node(app, 901, duplicates) is None
    assert appmod.url_for_node(app, 902, duplicates) is None
    assert appmod.url_for_node(app, 903, duplicates) is None


def test_duplicate_guard_rejects_post_normalization_lookup_collisions():
    appmod = load_app_module()
    app = _FakeApp()
    app.api = _Api(
        types={103:"document",104:"document"},
        docids={103:"IBoT 4.229+",104:"IBoT 4.229"},
        owners={},
        documents=(103,104),
    )
    unsafe = appmod.duplicate_docids(app)
    assert unsafe == {"IBoT 4.229+", "IBoT 4.229"}
    assert appmod.url_for_node(app, 103, unsafe) is None
    assert appmod.url_for_node(app, 104, unsafe) is None


def test_browser_keeps_internal_navigation_and_adds_source_action(monkeypatch):
    appmod = load_app_module()
    app = _fake_app()
    app._tlhdig_duplicate_docids = {"KUB 26.71"}
    app._browse = True
    app.context = SimpleNamespace(webHint="Open this text in TLHdig")
    calls = []

    def stock(n, **kwargs):
        calls.append((n, kwargs))
        return None if kwargs.get("urlOnly") else f"stock:{n}"

    def fake_out_link(text, href, **kwargs):
        assert text == "TLHdig ↗"
        assert kwargs["title"] == "Open this text in TLHdig"
        assert kwargs["asHtml"] is True
        return f"source:{href}"

    app._tf_stock_web_link = stock
    monkeypatch.setattr(appmod, "outLink", fake_out_link)

    result = appmod.tlhdig_web_link(app, 1, _noUrl=True, _asString=True)
    assert result == "stock:1 source:https://hethport.net/TLHdig/tlh_xtx.php?d=KUB+3.74"
    assert calls[-1][1]["_noUrl"] is True

    # The browser must not add a source action for an ambiguous manuscript identity.
    assert appmod.tlhdig_web_link(app, 101, _noUrl=True, _asString=True) == "stock:101"


def test_unsupported_url_only_fails_closed():
    appmod = load_app_module()
    app = _fake_app()
    app._tlhdig_duplicate_docids = {"KUB 26.71"}
    app._tf_stock_web_link = lambda n, **kwargs: None
    assert appmod.tlhdig_web_link(app, 101, urlOnly=True) is None


def test_reinit_contract_reinstalls_custom_wrapper():
    appmod = load_app_module()
    assert hasattr(appmod.TfApp, "reinit")
    assert hasattr(appmod.TfApp, "_install_tlhdig_weblink")
