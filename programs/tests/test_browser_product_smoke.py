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
    assert all(result[key] == 200 for key in (
        "root_status", "passage_status", "query_status", "css_status"
    ))
    assert result["query_nresults"] > 0
    print(json.dumps(result, indent=2))
