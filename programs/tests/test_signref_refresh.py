"""Independent-review regression for #22 refresh semantics."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PROGRAMS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAMS))

from tlhdig import signref_inputs as I


def _git_hash(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def test_prepare_refresh_refetches_even_a_verified_cache(tmp_path):
    data = b"an\t\xf0\x92\x80\xad\n"
    revision = "a" * 40
    source = I.SourceSpec(
        name="demo",
        filename="demo.tsv",
        kind="github",
        url=f"https://raw.githubusercontent.com/example/repo/{revision}/demo.tsv",
        revision=revision,
        hash_kind="git-blob-sha1",
        hash=_git_hash(data),
        license="CC0",
        lineage="demo",
    )
    target = tmp_path / source.filename
    target.write_bytes(data)
    calls = []

    def fetch(spec):
        calls.append(spec.name)
        return I.Fetched(data)

    result = I.prepare([source], tmp_path, refresh=True, fetcher=fetch)

    assert result.state == I.PASSED
    assert calls == ["demo"]
    assert result.sources[0].detail == "fetched"
