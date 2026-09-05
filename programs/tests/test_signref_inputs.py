"""TDD contract for reproducible acquisition of the external sign witnesses (#22)."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import sys
from pathlib import Path

import pytest

PROGRAMS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAMS))

import check_signrefs as gate
from tlhdig import signref_inputs as I
from tlhdig import signrefs as R


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


def _locked_source(name: str, filename: str, data: bytes) -> I.SourceSpec:
    revision = "a" * 40
    return I.SourceSpec(
        name=name,
        filename=filename,
        kind="github",
        url=f"https://raw.githubusercontent.com/example/repo/{revision}/{filename}",
        revision=revision,
        hash_kind="git-blob-sha1",
        hash=_git_hash(data),
        license="CC0",
        lineage=name,
    )


def _write_lock(path: Path, *sources: I.SourceSpec) -> None:
    path.write_text(
        json.dumps({"sources": [asdict(source) for source in sources]}),
        encoding="utf8",
    )


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


def test_lock_rejects_an_abbreviated_git_revision(tmp_path):
    source, data = _source()
    _write_lock(tmp_path / "lock.json", source)
    with pytest.raises(I.LockError):
        I.load_lock(tmp_path / "lock.json")


def test_repository_lock_covers_every_scholarly_loader():
    sources = I.load_lock(PROGRAMS / "signrefs.lock.json")
    assert {source.filename for source in sources} == set(R.LOADERS)
    assert {source.name for source in sources} == set(R.LINEAGE)


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


def test_mediawiki_fetch_path_binds_revision_metadata_to_returned_bytes(monkeypatch):
    data = b'export.sign_list = { ["x"] = {} }\n'
    digest = hashlib.sha1(data).hexdigest()
    source, _ = _source(
        name="wiktionary",
        data=data,
        kind="mediawiki",
        revision="83078078",
        hash_kind="mediawiki-sha1",
        hash=digest,
        url="https://en.wiktionary.org/w/api.php",
    )
    payload = {
        "query": {"pages": [{"revisions": [{
            "revid": 83078078,
            "sha1": digest,
            "slots": {"main": {"sha1": digest, "content": data.decode("utf8")}},
        }]}]}
    }
    monkeypatch.setattr(I, "_http_bytes", lambda _url: json.dumps(payload).encode("utf8"))
    fetched = I.fetch_source(source)
    assert fetched.data == data
    assert fetched.upstream_revision == "83078078"
    assert fetched.upstream_hash == digest


def test_mediawiki_fetch_rejects_metadata_for_different_bytes(monkeypatch):
    data = b'export.sign_list = { ["x"] = {} }\n'
    digest = hashlib.sha1(data).hexdigest()
    source, _ = _source(
        name="wiktionary",
        data=data,
        kind="mediawiki",
        revision="83078078",
        hash_kind="mediawiki-sha1",
        hash=digest,
        url="https://en.wiktionary.org/w/api.php",
    )
    payload = {
        "query": {"pages": [{"revisions": [{
            "revid": 83078078,
            "sha1": "0" * 40,
            "slots": {"main": {"sha1": "0" * 40, "content": data.decode("utf8")}},
        }]}]}
    }
    monkeypatch.setattr(I, "_http_bytes", lambda _url: json.dumps(payload).encode("utf8"))
    with pytest.raises(I.IntegrityError):
        I.fetch_source(source)


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


def test_verified_but_semantically_empty_source_fails_checker(tmp_path):
    refs = tmp_path / "refs"
    refs.mkdir()
    data = b"# valid bytes, but no Hittite sign mappings\n"
    source = _locked_source("potnia", "potnia-hittite.yaml", data)
    (refs / source.filename).write_bytes(data)
    lock = tmp_path / "lock.json"
    status = tmp_path / "status.json"
    _write_lock(lock, source)

    assert gate.main(["--lock", str(lock), "--refs", str(refs), "--status", str(status)]) == 1
    assert json.loads(status.read_text(encoding="utf8"))["state"] == I.FAILED


def test_unpinned_extra_loader_cannot_enter_the_vote(tmp_path):
    refs = tmp_path / "refs"
    refs.mkdir()
    data = '"an": "𒀭"\n'.encode("utf8")
    source = _locked_source("potnia", "potnia-hittite.yaml", data)
    (refs / source.filename).write_bytes(data)
    (refs / "nuolenna-signlist.tsv").write_text("an\t𒀭\n", encoding="utf8")
    lock = tmp_path / "lock.json"
    status = tmp_path / "status.json"
    _write_lock(lock, source)

    assert gate.main(["--lock", str(lock), "--refs", str(refs), "--status", str(status)]) == 1
    assert json.loads(status.read_text(encoding="utf8"))["state"] == I.FAILED


def test_checker_release_mode_rejects_missing_locked_input(tmp_path):
    source = _locked_source("potnia", "potnia-hittite.yaml", b'x')
    lock = tmp_path / "lock.json"
    refs = tmp_path / "refs"
    refs.mkdir()
    status = tmp_path / "status.json"
    _write_lock(lock, source)

    ordinary = gate.main([
        "--mode", "ordinary", "--lock", str(lock), "--refs", str(refs), "--status", str(status)
    ])
    assert ordinary == 0
    assert json.loads(status.read_text(encoding="utf8"))["state"] == I.SKIPPED_UNAVAILABLE

    release = gate.main([
        "--mode", "release", "--lock", str(lock), "--refs", str(refs), "--status", str(status)
    ])
    assert release != 0
