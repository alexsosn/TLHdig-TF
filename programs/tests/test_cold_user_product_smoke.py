"""Opt-in actual remote-release acquisition and live Text-Fabric CLI HTTP smoke.

This is a researcher product test, not a new download/distribution implementation.
Ordinary pytest never fetches the internet or allocates the full browser corpus.
#45 / #47 after #161/#162/#163.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.4.0"
TAG = "tlhdig-0.3_tf-0.4.0"
MARKER = "TLHDIG_COLD_USER_DOWNLOAD_JSON="

DOWNLOAD_CHILD = r'''
import json
import os
from pathlib import Path
import resource
from time import perf_counter

home = Path(os.environ["HOME"]).resolve()
assert not (home / "text-fabric-data").exists()
assert not (home / "github" / "alexsosn" / "TLHdig-TF").exists()
from tf.core import files
assert Path(files._homeDir).resolve() == home, "TF imported before isolated HOME"
from tf.app import use
from verify_dataset import verify

start = perf_counter()
A = use("alexsosn/TLHdig-TF", silent="deep")
assert A is not None and A.api is not None, "bare online use() could not load corpus"
assert A.context.version == "0.4.0", ("wrong app version", A.context.version)
cache = home / "text-fabric-data" / "github" / "alexsosn" / "TLHdig-TF" / "tf" / "0.4.0"
assert cache.is_dir(), ("no downloaded dataset", str(cache))
manifest_path = cache / "BUILD-MANIFEST.json"
assert manifest_path.is_file(), "downloaded release omitted BUILD-MANIFEST.json"
manifest = json.loads(manifest_path.read_text(encoding="utf8"))
expected = os.environ["TLHDIG_EXPECT_OUTPUT_DIGEST"]
assert manifest["outputs"]["digest"] == expected, (
    "stale same-version release", manifest["outputs"]["digest"], expected
)
ok, problems = verify(cache)
assert ok, ("downloaded data corrupt or incomplete", problems[:10])
assert A.load("src_file inferred sym lnr", silent="deep") is not False
F, L = A.api.F, A.api.L

def document_for(src_file):
    docs = [d for d in F.otype.s("document") if F.src_file.v(d) == src_file]
    assert len(docs) == 1, ("missing/ambiguous source file", src_file, docs[:4])
    return docs[0]

# #158's source-backed unwrapped transliteration, not synthesized from cuneiform.
doc31 = document_for("CTH 170_XML_TLH/KBo 31.40.xml")
inferred = [w for w in L.d(doc31, otype="word") if F.inferred.v(w) == 1]
assert len(inferred) == 41, ("lost KBo 31.40 recovery", len(inferred))
seen31 = {F.sym.v(s) for s in L.d(doc31, otype="sign")}
assert {"URU", "ŠEŠ", "QÍ", "BÍ", "MA", "DAM", "MEŠ"} <= seen31

# #159's actual original-source line recovered from malformed nested <w>.
doc41 = document_for("CTH 479_XML_BESRIT/KBo 41.49+.xml")
label = "{€1+2+3} Rs. III 2/2′"
lines = [n for n in L.d(doc41, otype="line") if F.lnr.v(n) == label]
assert len(lines) == 1, ("wrong repaired source section", lines)
signs = [F.sym.v(s) for s in L.d(lines[0], otype="sign") if F.sym.v(s)]
assert signs == ["pé", "e", "da", "an", "zi"], ("lost source reading", signs)

print("TLHDIG_COLD_USER_DOWNLOAD_JSON=" + json.dumps({
    "mode": "online-no-clone",
    "version": A.context.version,
    "manifest_digest": manifest["outputs"]["digest"],
    "tag_expected": "tlhdig-0.3_tf-0.4.0",
    "inferred_words_kbo31": len(inferred),
    "kbo41_signs": signs,
    "download_and_load_seconds": round(perf_counter() - start, 2),
    "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
}, sort_keys=True), flush=True)
'''


def _tail(path: Path, chars: int = 12000) -> str:
    if not path.is_file():
        return "(no process output)"
    return path.read_text(encoding="utf8", errors="replace")[-chars:]


def _json_request(url: str, data: dict[str, str]) -> dict:
    payload = urllib.parse.urlencode(data).encode("utf8")
    with urllib.request.urlopen(
        urllib.request.Request(url, data=payload, method="POST"),
        timeout=60,
    ) as response:
        assert response.status == 200, (url, response.status)
        return json.loads(response.read())


@pytest.mark.skipif(
    os.environ.get("TLHDIG_COLD_USER_SMOKE") != "1",
    reason="expensive opt-in online download + real CLI HTTP smoke",
)
def test_cold_online_release_then_real_cli_browser(tmp_path):
    # No symlink, clone, prior GitHub download, or repository cwd is visible
    # to TF's normal checkout resolver. Only the verification helper is on PYTHONPATH.
    home = tmp_path / "fresh-home"
    outside = tmp_path / "outside-repo"
    home.mkdir()
    outside.mkdir()
    assert not (home / "text-fabric-data").exists()
    assert not (home / "github").exists()
    local = ROOT / "tf" / VERSION / "BUILD-MANIFEST.json"
    expected = json.loads(local.read_text(encoding="utf8"))["outputs"]["digest"]
    assert expected.startswith("sha256:") and len(expected) == 71
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_CACHE_HOME"] = str(home / ".cache")
    env["PYTHONPATH"] = str(ROOT / "programs")
    env["TLHDIG_EXPECT_OUTPUT_DIGEST"] = expected
    download_log = tmp_path / "download.log"
    with download_log.open("w", encoding="utf8") as out:
        downloaded = subprocess.run(
            [sys.executable, "-c", DOWNLOAD_CHILD],
            cwd=outside, env=env, stdout=out, stderr=subprocess.STDOUT,
            timeout=1800, check=False,
        )
    assert downloaded.returncode == 0, (
        f"cold online use() failed ({downloaded.returncode})\n{_tail(download_log)}"
    )
    results = [
        line.split(MARKER, 1)[1]
        for line in download_log.read_text(encoding="utf8", errors="replace").splitlines()
        if MARKER in line
    ]
    assert len(results) == 1, _tail(download_log)
    identity = json.loads(results[0])
    assert identity["manifest_digest"] == expected
    assert identity["version"] == VERSION
    assert identity["inferred_words_kbo31"] == 41
    assert identity["kbo41_signs"] == ["pé", "e", "da", "an", "zi"]
    print("COLD_ACQUISITION", json.dumps(identity, sort_keys=True), flush=True)

    # The *actual* installed tf console entry point must start on the cached
    # remote corpus. No Flask factory/test-client shortcuts in this phase.
    binary = shutil.which("tf")
    assert binary is not None, "Text-Fabric CLI executable is not installed"
    from tf.browser.command import argApp, getPort
    from tf.parameters import HOST, PROTOCOL

    argv = ["alexsosn/TLHdig-TF", "-noweb"]
    port = getPort(argApp(argv, True))
    base = f"{PROTOCOL}{HOST}:{port}"
    cli_log = tmp_path / "cli.log"
    cli_start = time.monotonic()
    with cli_log.open("w", encoding="utf8") as out:
        process = subprocess.Popen(
            [binary, *argv],
            cwd=outside, env=env, stdout=out, stderr=subprocess.STDOUT,
        )
        try:
            root = None
            deadline = time.monotonic() + 900
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail(f"CLI exited early {process.returncode}: {_tail(cli_log)}")
                try:
                    with urllib.request.urlopen(base + "/", timeout=4) as response:
                        root = response.read()
                        assert response.status == 200
                        break
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                    time.sleep(3)
            assert root is not None, "CLI never exposed HTTP root: " + _tail(cli_log)
            assert b"TLHdig" in root, "no corpus identity on live CLI homepage"
            with urllib.request.urlopen(
                base + "/data/static/display.css", timeout=30
            ) as response:
                assert response.status == 200
                assert b"tlh-sign" in response.read()

            passage = _json_request(base + "/passage", {
                "sec0": "KUB 21.8", "sec1": "Vs. II",
                "sec2": "1′", "textFormat": "text-orig-plain",
            })
            assert passage.get("table"), ("no navigable text", passage)
            query = _json_request(base + "/query", {
                "query": "analysis lemma=wed=a-",
                "condenseType": "line",  # measured real UI setting, #163
                "batch": "10", "position": "1",
                "textFormat": "text-orig-plain",
            })
            assert query.get("status") is True, ("broken TF query", query)
            assert query.get("nResults", 0) > 0 and query.get("table"), (
                "no rendered query matches", query
            )
            print("COLD_USER_CLI_JSON=" + json.dumps({
                "http_root": 200,
                "http_passage": 200,
                "http_query": 200,
                "http_css": 200,
                "query_results": query["nResults"],
                "cli_startup_seconds": round(time.monotonic() - cli_start, 2),
                "cached_release_digest": expected,
                "children_max_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            }, sort_keys=True), flush=True)
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=15)
    # The child must not have populated a maintainer-local clone at any point.
    assert not (home / "github" / "alexsosn" / "TLHdig-TF").exists()
    assert (home / "text-fabric-data" / "github" / "alexsosn" / "TLHdig-TF"
            / "tf" / VERSION / "BUILD-MANIFEST.json").is_file()
