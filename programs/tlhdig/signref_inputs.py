"""Reproducible acquisition and integrity checks for external sign witnesses.

The scholarly loaders live in :mod:`tlhdig.signrefs`. This module deliberately owns
only provenance, fetching, completeness and execution policy so network failures cannot
be confused with a corpus/sign-list disagreement.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PASSED = "passed"
FAILED = "failed"
SKIPPED_UNAVAILABLE = "skipped-unavailable"
SKIPPED_POLICY = "skipped-policy"


class LockError(ValueError):
    pass


class IntegrityError(ValueError):
    pass


class FetchUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceSpec:
    name: str
    filename: str
    kind: str
    url: str
    revision: str
    hash_kind: str
    hash: str
    license: str
    lineage: str


@dataclass(frozen=True)
class Fetched:
    data: bytes
    upstream_revision: str | None = None
    upstream_hash: str | None = None


@dataclass(frozen=True)
class SourceResult:
    name: str
    filename: str
    state: str
    revision: str
    expected_hash: str
    actual_hash: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class Result:
    state: str
    sources: tuple[SourceResult, ...]

    def to_dict(self) -> dict:
        return {"state": self.state, "sources": [asdict(item) for item in self.sources]}


def _required_text(item: dict, key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LockError(f"source {item.get('name', '<unnamed>')!r}: missing {key}")
    return value.strip()


def _is_hex_sha1(value: str) -> bool:
    if len(value) != 40:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def load_lock(path: Path | str) -> list[SourceSpec]:
    """Load and strictly validate the source lock before any network access."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LockError(f"cannot read sign-reference lock: {exc}") from exc
    raw_sources = payload.get("sources") if isinstance(payload, dict) else None
    if not isinstance(raw_sources, list) or not raw_sources:
        raise LockError("sign-reference lock needs a non-empty sources list")

    result: list[SourceSpec] = []
    names: set[str] = set()
    filenames: set[str] = set()
    for item in raw_sources:
        if not isinstance(item, dict):
            raise LockError("each source lock entry must be an object")
        values = {key: _required_text(item, key) for key in SourceSpec.__dataclass_fields__}
        spec = SourceSpec(**values)
        if spec.name in names or spec.filename in filenames:
            raise LockError(f"duplicate source name/filename: {spec.name}/{spec.filename}")
        if Path(spec.filename).name != spec.filename:
            raise LockError(f"source {spec.name}: filename must not contain a path")
        if spec.kind not in {"github", "mediawiki"}:
            raise LockError(f"source {spec.name}: unsupported kind {spec.kind!r}")
        if spec.kind == "github":
            if spec.hash_kind != "git-blob-sha1" or not _is_hex_sha1(spec.hash):
                raise LockError(f"source {spec.name}: GitHub sources require a 40-char git blob SHA-1")
            if not _is_hex_sha1(spec.revision):
                raise LockError(f"source {spec.name}: GitHub revision must be a full 40-char commit SHA")
            if spec.revision not in spec.url:
                raise LockError(f"source {spec.name}: raw URL does not contain pinned revision")
        else:
            if spec.hash_kind != "mediawiki-sha1" or not _is_hex_sha1(spec.hash):
                raise LockError(f"source {spec.name}: MediaWiki sources require a 40-char SHA-1")
            if not spec.revision.isdigit():
                raise LockError(f"source {spec.name}: MediaWiki revision must be a numeric revid")
        names.add(spec.name)
        filenames.add(spec.filename)
        result.append(spec)
    return result


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def mediawiki_sha1(data: bytes) -> str:
    """Return the hex SHA-1 emitted by the revisions API for slot content."""
    return hashlib.sha1(data).hexdigest()


def verify_payload(
    source: SourceSpec,
    data: bytes,
    *,
    upstream_revision: str | None = None,
    upstream_hash: str | None = None,
) -> str:
    if not data:
        raise IntegrityError(f"{source.name}: empty payload")

    if source.kind == "github":
        actual = git_blob_sha1(data)
    elif source.kind == "mediawiki":
        if upstream_revision is not None and str(upstream_revision) != source.revision:
            raise IntegrityError(
                f"{source.name}: expected revision {source.revision}, got {upstream_revision}"
            )
        computed = mediawiki_sha1(data)
        if upstream_hash is not None and upstream_hash != computed:
            raise IntegrityError(
                f"{source.name}: MediaWiki metadata hash {upstream_hash} does not match bytes {computed}"
            )
        actual = upstream_hash or computed
    else:  # SourceSpec normally comes from load_lock; keep direct construction safe.
        raise IntegrityError(f"{source.name}: unsupported source kind {source.kind!r}")

    if actual != source.hash:
        raise IntegrityError(f"{source.name}: expected {source.hash}, got {actual}")
    return actual


def _source_result(source: SourceSpec, state: str, *, actual_hash=None, detail="") -> SourceResult:
    return SourceResult(
        name=source.name,
        filename=source.filename,
        state=state,
        revision=source.revision,
        expected_hash=source.hash,
        actual_hash=actual_hash,
        detail=detail,
    )


def inspect_local(sources: Iterable[SourceSpec], directory: Path | str) -> Result:
    directory = Path(directory)
    rows: list[SourceResult] = []
    missing = False
    failed = False
    for source in sources:
        path = directory / source.filename
        if not path.is_file():
            missing = True
            rows.append(_source_result(source, "missing", detail="file is absent"))
            continue
        try:
            actual = verify_payload(source, path.read_bytes())
        except (OSError, IntegrityError) as exc:
            failed = True
            rows.append(_source_result(source, "failed", detail=str(exc)))
        else:
            rows.append(_source_result(source, "verified", actual_hash=actual))
    state = FAILED if failed else SKIPPED_UNAVAILABLE if missing else PASSED
    return Result(state, tuple(rows))


def _http_bytes(url: str, *, timeout: float = 30.0) -> bytes:
    request = Request(url, headers={"User-Agent": "TLHdig-TF signref validator/1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise FetchUnavailable(f"fetch failed for {url}: {exc}") from exc


def fetch_source(source: SourceSpec) -> Fetched:
    if source.kind == "github":
        return Fetched(_http_bytes(source.url))

    if source.kind == "mediawiki":
        query = urlencode(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "revisions",
                "revids": source.revision,
                "rvprop": "ids|sha1|slotsha1|content",
                "rvslots": "main",
            }
        )
        raw = _http_bytes(f"{source.url}?{query}")
        try:
            payload = json.loads(raw.decode("utf8"))
            page = payload["query"]["pages"][0]
            revision = page["revisions"][0]
            revid = str(revision["revid"])
            revision_sha1 = revision["sha1"]
            slot = revision["slots"]["main"]
            slot_sha1 = slot["sha1"]
            content = slot.get("content", slot.get("*"))
            if not isinstance(content, str):
                raise KeyError("revision content")
        except (KeyError, IndexError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise IntegrityError(f"{source.name}: malformed MediaWiki response") from exc
        data = content.encode("utf8")
        computed = mediawiki_sha1(data)
        if revision_sha1 != computed or slot_sha1 != computed:
            raise IntegrityError(
                f"{source.name}: MediaWiki metadata hashes do not match returned bytes {computed}"
            )
        return Fetched(data, upstream_revision=revid, upstream_hash=slot_sha1)

    raise IntegrityError(f"{source.name}: unsupported source kind {source.kind!r}")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def acquire(
    sources: Iterable[SourceSpec],
    directory: Path | str,
    *,
    fetcher: Callable[[SourceSpec], Fetched] = fetch_source,
    refresh: bool = False,
) -> Result:
    directory = Path(directory)
    source_list = list(sources)
    rows: list[SourceResult] = []
    unavailable = False
    failed = False

    for source in source_list:
        target = directory / source.filename
        if target.is_file() and not refresh:
            try:
                actual = verify_payload(source, target.read_bytes())
            except (OSError, IntegrityError) as exc:
                failed = True
                rows.append(_source_result(source, "failed", detail=str(exc)))
            else:
                rows.append(_source_result(source, "verified", actual_hash=actual, detail="cached"))
            continue

        try:
            fetched = fetcher(source)
            actual = verify_payload(
                source,
                fetched.data,
                upstream_revision=fetched.upstream_revision,
                upstream_hash=fetched.upstream_hash,
            )
            _atomic_write(target, fetched.data)
        except FetchUnavailable as exc:
            unavailable = True
            rows.append(_source_result(source, "unavailable", detail=str(exc)))
        except (OSError, IntegrityError) as exc:
            failed = True
            rows.append(_source_result(source, "failed", detail=str(exc)))
        else:
            rows.append(_source_result(source, "verified", actual_hash=actual, detail="fetched"))

    state = FAILED if failed else SKIPPED_UNAVAILABLE if unavailable else PASSED
    return Result(state, tuple(rows))


def prepare(
    sources: Iterable[SourceSpec],
    directory: Path | str,
    *,
    network: bool = True,
    refresh: bool = False,
    fetcher: Callable[[SourceSpec], Fetched] = fetch_source,
) -> Result:
    source_list = list(sources)
    local = inspect_local(source_list, directory)
    if local.state in {PASSED, FAILED}:
        return local
    if not network:
        return Result(SKIPPED_POLICY, local.sources)
    return acquire(source_list, directory, fetcher=fetcher, refresh=refresh)


def exit_code(state: str, *, mode: str) -> int:
    if mode not in {"ordinary", "release"}:
        raise ValueError("mode must be 'ordinary' or 'release'")
    if state == FAILED:
        return 1
    if mode == "release" and state != PASSED:
        return 2
    return 0


def write_status(path: Path | str, result: Result, *, mode: str) -> None:
    output = {"mode": mode, **result.to_dict()}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
