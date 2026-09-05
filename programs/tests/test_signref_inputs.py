"""TDD contract for reproducible acquisition of the external sign witnesses (#22)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import signref_inputs as I


def _git_hash(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _source(name="demo", data=b"an\t\xf0\x92\x80\xad\n", **overrides):
    values = dict(
        name=name,
        filename=f"{name}.tsv",
        kind="github",
        url=f"https://raw.githubusercontent.com/example/{name}/deadbeef/source.tsv",
        revision="deadbeef",
        hash_kind="git-blob-sha1",
        hash=_git_hash(data),
        license="CC0",
        lineage=name,
    )
    values.update(overrides)
    return I.SourceSpec(**values), data


def test_lock_rejects_a_source_without_an_immutable_revision_or_hash(tmp_path):
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"sources": [{
        "name": "x", "filename": "x.tsv", "kind": "github",
        "url": "https://raw.githubusercontent.com/a/b/main/x.tsv",
        "revision": "", "hash_kind": "git-blob-sha1", "hash": "",
        "license": "MIT", "lineage": "x",
    }]}), encoding="utf8")
    with pytest.raises(I.LockError):
        I.load_lock(lock)


def test_git_payload_is_verified_using_git_blob_hash_not_plain_sha1():
    source, data = _source()
    assert I.verify_payload(source, data) == source.hash


def test_wrong_git_blob_hash_is_a_hard_integrity_failure():
    source, data = _source(hash="0" * 40)
    with pytest.raises(I.IntegrityError):
        I.verify_payload(source, data)


def test_mediawiki_payload_requires_the_pinned_revision_and_revision_hash():
    data = b'export.sign_list = { ["x"] = {} }\n'
    expected = "693d826ad9076dca70d7f6c8db71e728fdb577b1"
    source, _ = _source(
        name="wiktionary",
        data=data,
        kind="mediawiki",
        revision="83078078",
        hash_kind="mediawiki-sha1",
        hash=expected,
        url="https://en.wiktionary.org/w/api.php",
    )
    assert I.verify_payload(source, data, upstream_revision="83078078", upstream_hash=expected) == expected
    with pytest.raises(I.IntegrityError):
        I.verify_payload(source, data, upstream_revision="83078079", upstream_hash=expected)
    with pytest.raises(I.IntegrityError):
        I.verify_payload(source, data, upstream_revision="83078078", upstream_hash="wrong")


def test_complete_local_set_is_passed(tmp_path):
    a, adata = _source("a")
    b, bdata = _source("b")
    (tmp_path / a.filename).write_bytes(adata)
    (tmp_path / b.filename).write_bytes(bdata)
    result = I.inspect_local([a, b], tmp_path)
    assert result.state == I.PASSED
    assert [s.state for s in result.sources] == ["verified", "verified"]


def test_one_missing_file_makes_the_set_skipped_unavailable_not_passed(tmp_path):
    a, adata = _source("a")
    b, _ = _source("b")
    (tmp_path / a.filename).write_bytes(adata)
    result = I.inspect_local([a, b], tmp_path)
    assert result.state == I.SKIPPED_UNAVAILABLE
    assert any(s.name == "b" and s.state == "missing" for s in result.sources)


def test_corrupt_local_file_is_failed_not_a_skip(tmp_path):
    source, _ = _source()
    (tmp_path / source.filename).write_bytes(b"tampered")
    result = I.inspect_local([source], tmp_path)
    assert result.state == I.FAILED


def test_network_failure_is_explicitly_unavailable_and_does_not_leave_partial_file(tmp_path):
    source, _ = _source()

    def broken(_source):
        raise I.FetchUnavailable("network down")

    result = I.acquire([source], tmp_path, fetcher=broken)
    assert result.state == I.SKIPPED_UNAVAILABLE
    assert not (tmp_path / source.filename).exists()


def test_integrity_failure_does_not_replace_a_previous_verified_file(tmp_path):
    source, good = _source()
    target = tmp_path / source.filename
    target.write_bytes(good)

    def tampered(_source):
        return I.Fetched(b"tampered")

    result = I.acquire([source], tmp_path, fetcher=tampered, refresh=True)
    assert result.state == I.FAILED
    assert target.read_bytes() == good


def test_partial_fetch_never_becomes_passed(tmp_path):
    a, adata = _source("a")
    b, _ = _source("b")

    def fetch(source):
        if source.name == "a":
            return I.Fetched(adata)
        raise I.FetchUnavailable("b unavailable")

    result = I.acquire([a, b], tmp_path, fetcher=fetch)
    assert result.state == I.SKIPPED_UNAVAILABLE


def test_policy_skip_is_explicit_when_network_is_disabled_and_inputs_are_incomplete(tmp_path):
    source, _ = _source()
    result = I.prepare([source], tmp_path, network=False)
    assert result.state == I.SKIPPED_POLICY


def test_ordinary_mode_allows_a_skip_but_release_mode_does_not():
    assert I.exit_code(I.SKIPPED_UNAVAILABLE, mode="ordinary") == 0
    assert I.exit_code(I.SKIPPED_POLICY, mode="ordinary") == 0
    assert I.exit_code(I.SKIPPED_UNAVAILABLE, mode="release") != 0
    assert I.exit_code(I.SKIPPED_POLICY, mode="release") != 0
    assert I.exit_code(I.PASSED, mode="release") == 0
    assert I.exit_code(I.FAILED, mode="ordinary") != 0


def test_empty_payload_is_malformed_before_it_can_be_used(tmp_path):
    source, _ = _source(data=b"")

    def empty(_source):
        return I.Fetched(b"")

    result = I.acquire([source], tmp_path, fetcher=empty)
    assert result.state == I.FAILED
    assert "empty" in result.sources[0].detail.lower()
