"""RED contract for safe recovery of corrupt sign-reference caches (#36)."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PROGRAMS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAMS))

from tlhdig import signref_inputs as I


def _git_hash(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _source(name: str = "demo", data: bytes = b"an\tvalue\n") -> I.SourceSpec:
    revision = "a" * 40
    return I.SourceSpec(
        name=name,
        filename=f"{name}.tsv",
        kind="github",
        url=f"https://raw.githubusercontent.com/example/repo/{revision}/{name}.tsv",
        revision=revision,
        hash_kind="git-blob-sha1",
        hash=_git_hash(data),
        license="CC0",
        lineage=name,
    )


def test_prepare_recovers_corrupt_cache_without_explicit_refresh(tmp_path):
    good = b"an\tvalue\n"
    source = _source(data=good)
    target = tmp_path / source.filename
    target.write_bytes(b"corrupt")
    calls = []

    def fetch(spec):
        calls.append(spec.name)
        return I.Fetched(good)

    result = I.prepare([source], tmp_path, fetcher=fetch)

    assert result.state == I.PASSED
    assert calls == ["demo"]
    assert result.sources[0].state == "verified"
    assert result.sources[0].detail == "fetched"
    assert target.read_bytes() == good


def test_prepare_refresh_recovers_corrupt_cache(tmp_path):
    good = b"an\tvalue\n"
    source = _source(data=good)
    target = tmp_path / source.filename
    target.write_bytes(b"corrupt")
    calls = []

    def fetch(spec):
        calls.append(spec.name)
        return I.Fetched(good)

    result = I.prepare([source], tmp_path, refresh=True, fetcher=fetch)

    assert result.state == I.PASSED
    assert calls == ["demo"]
    assert target.read_bytes() == good


def test_prepare_offline_corrupt_cache_remains_hard_failure(tmp_path):
    source = _source()
    target = tmp_path / source.filename
    target.write_bytes(b"corrupt")
    calls = []

    def fetch(spec):
        calls.append(spec.name)
        raise AssertionError("offline prepare must not fetch")

    result = I.prepare([source], tmp_path, network=False, refresh=True, fetcher=fetch)

    assert result.state == I.FAILED
    assert calls == []
    assert target.read_bytes() == b"corrupt"


def test_unavailable_recovery_does_not_downgrade_known_corruption_to_skip(tmp_path):
    source = _source()
    target = tmp_path / source.filename
    target.write_bytes(b"corrupt")
    calls = []

    def fetch(spec):
        calls.append(spec.name)
        raise I.FetchUnavailable("network down")

    result = I.prepare([source], tmp_path, fetcher=fetch)

    assert calls == ["demo"]
    assert result.state == I.FAILED
    assert result.sources[0].state == "failed"
    assert target.read_bytes() == b"corrupt"


def test_invalid_replacement_does_not_overwrite_corrupt_cache(tmp_path):
    source = _source()
    target = tmp_path / source.filename
    target.write_bytes(b"corrupt")
    calls = []

    def fetch(spec):
        calls.append(spec.name)
        return I.Fetched(b"different-invalid-bytes")

    result = I.prepare([source], tmp_path, fetcher=fetch)

    assert calls == ["demo"]
    assert result.state == I.FAILED
    assert target.read_bytes() == b"corrupt"


def test_targeted_recovery_does_not_refresh_valid_cached_siblings(tmp_path):
    good_a = b"a\tvalue\n"
    good_b = b"b\tvalue\n"
    a = _source("a", good_a)
    b = _source("b", good_b)
    (tmp_path / a.filename).write_bytes(good_a)
    (tmp_path / b.filename).write_bytes(b"corrupt")
    calls = []

    def fetch(spec):
        calls.append(spec.name)
        assert spec.name == "b"
        return I.Fetched(good_b)

    result = I.prepare([a, b], tmp_path, fetcher=fetch)

    assert result.state == I.PASSED
    assert calls == ["b"]
    assert (tmp_path / a.filename).read_bytes() == good_a
    assert (tmp_path / b.filename).read_bytes() == good_b
