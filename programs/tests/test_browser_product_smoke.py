"""Real Text-Fabric 13.1 browser/HTTP product smoke (#45).

The test is opt-in because building a fresh browser kernel loads the large
current corpus. It never contacts live TLHdig and imports Text-Fabric only in
a child whose HOME is isolated *before* process start.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "TLHDIG_BROWSER_SMOKE_JSON="

CHILD = r'''
import json
import os
from pathlib import Path
import resource
from time import perf_counter

home = Path(os.environ["HOME"]).resolve()
# HOME isolation must be verified before any first TF import.
from tf.core import files
assert Path(files._homeDir).resolve() == home, (
    "Text-Fabric cached another home", files._homeDir, str(home)
)

from tf.browser.web import setup
start = perf_counter()
webapp = setup(False, "alexsosn/TLHdig-TF:clone", "--checkout=clone")
assert webapp is not None, "real TF browser setup failed"
load_seconds = round(perf_counter() - start, 2)
# Inspect the actual pinned TF browser kernel rather than trusting a URL label.
# The stock route captures Web in a closure (pinned TF 13.1 factory(web)).
query_view = webapp.view_functions["serveQueryBare"]
route_cells = dict(zip(
    query_view.__code__.co_freevars,
    (cell.cell_contents for cell in query_view.__closure__),
))
web = route_cells["web"]
context = web.context
assert context.version == "0.4.0", ("wrong current TF version", context.version)
expected_app = home / "github" / "alexsosn" / "TLHdig-TF" / "app"
assert Path(context.appPath).resolve() == expected_app.resolve(), (
    "app did not come from isolated clone", context.appPath, str(expected_app)
)
provenance = web.kernelApi.app.isLoaded("srcxml src_span", pretty=False)
assert not any(provenance.values()), ("optional provenance loaded", provenance)
condense_type = context.condenseType
assert condense_type in web.kernelApi.app.api.N.otypeRank, (
    "invalid browser selection", condense_type
)
# #76: real source-attested, multi-candidate line rendered by the actual
# browser app. This line is the same one used by the current-corpus HTML
# research run 44381678054, but resolve by scholarly section, not node ID.
app = web.kernelApi.app
interlinear_line = app.api.T.nodeFromSection(("KUB 21.8", "Vs. II", "2′"))
assert interlinear_line is not None, "research fixture line could not be navigated"
pretty = app.pretty(interlinear_line, _asString=True)
assert "tlh-word-analyses" in pretty, "native word-owned candidate hook missing"
# Source-pinned DOM assertion: every candidate group must have exactly one
# word container ancestor, rather than wrapping as a line-level flex sibling.
from lxml import html as lxml_html
# Pinned TF 13.1 render._getNodePart() emits <a href="#" class="nd">
# inside the live browser, but <span class="nd"> in notebook/research
# pretty() mode. Select a direct label child without hardcoding its tag.
WORD_OWNER_XPATH = (
    'ancestor::div[contains(concat(" ", normalize-space(@class), " "), " contnr ")]'
    '[./div[contains(concat(" ", normalize-space(@class), " "), " lbl ")]'
    '/*[contains(concat(" ", normalize-space(@class), " "), " nd ")]'
    '[normalize-space()="word"]]'
)
tree = lxml_html.fromstring(pretty)
groups = tree.xpath(
    '//*[contains(concat(" ", normalize-space(@class), " "), " tlh-word-analyses ")]'
)
assert groups, "no word-owned candidate group in source-known pretty line"
for group in groups:
    word_ancestors = group.xpath(
        WORD_OWNER_XPATH
    )
    assert len(word_ancestors) == 1, (
        "candidate rows escaped their owning TF word container",
        group.get("class"),
    )
assert "Candidate 1" in pretty and "Candidate 2" in pretty, (
    "source morphological alternatives were lost"
)
assert "tlh-sign" in pretty, "sign-local Hittitological renderer regressed"
assert not tree.xpath(
    '//*[contains(concat(" ", normalize-space(@class), " "), " nd ")]'
    '[normalize-space()="analysis"]'
), "equal-slot analysis nodes were unsafely unhidden into the TF tree"
# Independently reconcile rendered candidate rows to the released source
# graph. Merely finding one visible candidate would miss dropped alternatives.
for line_label, expected_count in (("2′", 7), ("3′", 10)):
    line_node = app.api.T.nodeFromSection(("KUB 21.8", "Vs. II", line_label))
    assert line_node is not None, ("missing real interlinear line", line_label)
    graph_candidates = sum(
        len(app.api.E.analyses.f(word))
        for word in app.api.L.d(line_node, otype="word")
    )
    assert graph_candidates == expected_count, (
        "research fixture changed or source graph lost alternatives",
        line_label, graph_candidates
    )
    line_html = app.pretty(line_node, _asString=True)
    line_dom = lxml_html.fromstring(line_html)
    rendered_candidates = line_dom.xpath(
        '//*[contains(concat(" ", normalize-space(@class), " "), " tlh-analysis-candidate ")]'
    )
    assert len(rendered_candidates) == graph_candidates, (
        "real TF pretty silently omitted or duplicated source candidates",
        line_label, len(rendered_candidates), graph_candidates
    )
    for candidate in rendered_candidates:
        owners = candidate.xpath(
            WORD_OWNER_XPATH
        )
        assert len(owners) == 1, "a candidate is not owned by exactly one word"
client = webapp.test_client()

root = client.get("/")
assert root.status_code == 200, ("GET /", root.status_code, root.data[-500:])
assert b"TLHdig" in root.data, "homepage missing TLHdig corpus identity"

passage = client.post("/passage", data={
    "sec0": "KUB 21.8",
    "sec1": "Vs. II",
    "sec2": "1\u2032",
    "textFormat": "text-orig-plain",
})
assert passage.status_code == 200, (
    "POST /passage", passage.status_code, passage.data[-500:]
)
passage_data = passage.get_json()
assert isinstance(passage_data, dict)
assert passage_data.get("table"), ("empty passage", passage_data)

query = client.post("/query", data={
    "query": "analysis lemma=wed=a-",
    "condenseType": condense_type,
    "batch": "10",
    "position": "1",
    "textFormat": "text-orig-plain",
})
assert query.status_code == 200, (
    "POST /query", query.status_code, query.data[-500:]
)
query_data = query.get_json()
assert isinstance(query_data, dict) and query_data.get("status") is True, (
    "query error", query_data
)
assert query_data.get("nResults", 0) > 0, (
    "no attested morphology results", query_data
)
assert query_data.get("table"), "query returned no rendered table"

css = client.get("/data/static/display.css")
assert css.status_code == 200, ("app CSS", css.status_code)
assert b"tlh-sign" in css.data, "corpus-specific sign renderer CSS missing"

print("TLHDIG_BROWSER_SMOKE_JSON=" + json.dumps({
    "mode": "isolated-clone",
    "home": str(home),
    "app_path": str(Path(context.appPath).resolve()),
    "tf_version": context.version,
    "condense_type": condense_type,
    "provenance_loaded": False,
    "interlinear_word_candidates": pretty.count('class="tlh-analysis-candidate'),
    "load_seconds": load_seconds,
    "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    "root_status": root.status_code,
    "passage_status": passage.status_code,
    "query_status": query.status_code,
    "query_nresults": query_data["nResults"],
    "css_status": css.status_code,
}, sort_keys=True), flush=True)
'''


@pytest.mark.skipif(
    os.environ.get("TLHDIG_BROWSER_SMOKE") != "1",
    reason="real current-artifact browser integration is a dedicated opt-in gate",
)
def test_browser_root_passage_query_and_css_from_clean_home(tmp_path):
    home = tmp_path / "clean-home"
    home.mkdir()
    clone = home / "github" / "alexsosn" / "TLHdig-TF"
    clone.parent.mkdir(parents=True)
    clone.symlink_to(ROOT, target_is_directory=True)
    assert not (home / "text-fabric-data").exists()

    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_CACHE_HOME"] = str(home / ".cache")
    env.pop("PYTHONPATH", None)
    process = subprocess.run(
        [sys.executable, "-c", CHILD],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1200,
        check=False,
    )
    assert process.returncode == 0, (
        f"isolated browser process failed {process.returncode}\n"
        f"STDOUT:\n{process.stdout[-7000:]}\n"
        f"STDERR:\n{process.stderr[-7000:]}"
    )
    markers = [
        line.removeprefix(PREFIX)
        for line in process.stdout.splitlines()
        if line.startswith(PREFIX)
    ]
    assert len(markers) == 1, process.stdout[-5000:]
    result = json.loads(markers[0])
    assert result["home"] == str(home.resolve())
    assert result["tf_version"] == "0.4.0"
    assert result["provenance_loaded"] is False
    assert result["app_path"] == str((clone / "app").resolve())
    assert all(result[key] == 200 for key in (
        "root_status", "passage_status", "query_status", "css_status"
    ))
    assert result["query_nresults"] > 0
    print(json.dumps(result, indent=2))


def test_selective_research_comparison_rejects_equal_count_different_nodes():
    """Equal cardinality alone cannot establish identical research results."""
    full = {"analysis_nodes": [11, 19], "passage_text": "nu"}
    selective = {"analysis_nodes": [11, 23], "passage_text": "nu"}
    with pytest.raises(AssertionError, match="analysis nodes"):
        assert_same_research_result(full, selective)


def test_selective_research_comparison_rejects_passage_drift_and_empty_results():
    full = {"analysis_nodes": [11, 19], "passage_text": "nu"}
    assert_same_research_result(full, dict(full))
    with pytest.raises(AssertionError, match="passage"):
        assert_same_research_result(full, {**full, "passage_text": "ma"})
    empty = {"analysis_nodes": [], "passage_text": "nu"}
    with pytest.raises(AssertionError, match="analysis nodes"):
        assert_same_research_result(empty, empty)
