#!/usr/bin/env python
"""Measure the current Contract-A exception allowlist against real source + graph.

Research instrument for #142. It does not mutate conversion semantics or decide which
exceptions to remove; it records the evidence needed for the TDD gate.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tf.fabric import Fabric

from tlhdig import PROVENANCE_DIR, TF_VERSION, repair, signs, source
from tlhdig.paths import CORPUS, PATCHES, PROGRAMS, REPORTS, ROOT


ALLOWLIST = PROGRAMS / "contract_a_known.txt"
LOSSY = PROGRAMS / "known_lossy.txt"
CROSSING_INVENTORY = REPORTS / "source-recovery-inventory.json"
OUTPUT = REPORTS / "contract-a-exception-census.json"
NEEDED = "otype oslots src_span src_file srcxml after"


def _paths(path: Path) -> list[str]:
    return sorted(
        line.partition("\t")[0]
        for line in path.read_text(encoding="utf8").splitlines()
        if line.strip() and not line.startswith("#")
    )


def _short(data: bytes, limit: int = 120) -> str:
    return repr(data[:limit])


def _repair_class(patch: repair.Patch) -> str:
    reason = patch.reason
    if reason.startswith("crossing tags:"):
        return "crossing"
    if reason == "stray close tag, nothing open":
        if b"SP___Page_20_Number" in patch.old:
            return "stray_odf_close"
        if b"</w>" in patch.old:
            return "stray_word_close"
        return "stray_close"
    if "attribute value" in reason:
        return "attribute_escape"
    if reason == "stray unterminated <w fragment":
        return "malformed_word_fragment"
    return "other"


def _visible_word_spans(spans: list[source.Span]) -> list[source.Span]:
    """Mirror convert._document's source-span selection without importing internals."""
    text_span = next(
        (sp for sp in spans if sp.tag == "text" and sp.inner_start is not None),
        None,
    )
    words = [sp for sp in spans if sp.tag == "w"]
    if text_span is not None:
        words = [
            sp
            for sp in words
            if text_span.inner_start <= sp.outer_start < text_span.inner_end
        ]
    return [
        sp
        for sp in words
        if not any(
            outer is not sp
            and outer.outer_start <= sp.outer_start
            and sp.outer_end <= outer.outer_end
            for outer in words
        )
    ]


def _graph_measure(api, rel: str, raw: bytes, lossy: bool) -> dict:
    F, L = api.F, api.L
    docs = [d for d in F.otype.s("document") if F.src_file.v(d) == rel]
    if len(docs) != 1:
        raise RuntimeError(f"{rel}: expected one graph document, got {len(docs)}")

    words = list(L.d(docs[0], otype="word"))
    stats = Counter()
    examples: list[dict] = []

    for word in words:
        span = F.src_span.v(word)
        if not span:
            stats["missing_span"] += 1
            if len(examples) < 8:
                examples.append({"kind": "missing_span", "word": word})
            continue
        try:
            a, b = (int(x) for x in span.split("-", 1))
        except (ValueError, AttributeError):
            stats["unparseable_span"] += 1
            if len(examples) < 8:
                examples.append(
                    {"kind": "unparseable_span", "word": word, "span": span}
                )
            continue

        if not (0 <= a < b <= len(raw)):
            stats["invalid_bounds"] += 1
            if len(examples) < 8:
                examples.append(
                    {
                        "kind": "invalid_bounds",
                        "word": word,
                        "span": span,
                        "source_length": len(raw),
                    }
                )
            continue

        chunk = raw[a:b]
        is_word = chunk.startswith(b"<w") and chunk.rstrip().endswith(b">")
        if not is_word:
            stats["invalid_word_slice"] += 1
            if len(examples) < 8:
                examples.append(
                    {
                        "kind": "invalid_word_slice",
                        "word": word,
                        "span": span,
                        "source": _short(chunk),
                    }
                )
            continue

        stats["valid_word_slice"] += 1
        slots = L.d(word, otype="sign")
        graph = "".join((F.srcxml.v(s) or "") + (F.after.v(s) or "") for s in slots)

        if b"</w>" in chunk:
            inner = chunk[chunk.index(b">") + 1 : chunk.rindex(b"</w>")]
        else:
            inner = b""
        kept = "".join(
            token.srcxml + token.after
            for token in signs.tokenise_word(inner)
            if token.type != "empty"
        )
        if graph == kept:
            stats["graph_identical"] += 1
        else:
            stats["graph_mismatch"] += 1
            if len(examples) < 8:
                examples.append(
                    {
                        "kind": "graph_mismatch",
                        "word": word,
                        "span": span,
                        "source_tokens": kept[:160],
                        "graph_tokens": graph[:160],
                    }
                )

    provenance_failure = (
        stats["missing_span"]
        + stats["unparseable_span"]
        + stats["invalid_bounds"]
        + stats["invalid_word_slice"]
    )
    content_failure = 0 if lossy else stats["graph_mismatch"]

    return {
        "document_nodes": docs,
        "word_count": len(words),
        "missing_span": stats["missing_span"],
        "unparseable_span": stats["unparseable_span"],
        "invalid_bounds": stats["invalid_bounds"],
        "invalid_word_slice": stats["invalid_word_slice"],
        "valid_word_slice": stats["valid_word_slice"],
        "graph_identical": stats["graph_identical"],
        "graph_mismatch": stats["graph_mismatch"],
        "known_lossy": lossy,
        "contract_a_failures": provenance_failure + content_failure,
        "examples": examples,
    }


def _source_measure(raw: bytes, patches: list[repair.Patch]) -> dict:
    repaired = repair.apply(raw, patches, expect_sha=sha256(raw).hexdigest())
    spans = source.scan(repaired)
    words = _visible_word_spans(spans)
    omap = repair.OffsetMap(raw, patches)

    inexact_start = 0
    inexact_end = 0
    bad_mapped_slice = 0
    examples: list[dict] = []

    for sp in words:
        start_exact = omap.is_exact(sp.outer_start)
        end_exact = omap.is_exact(sp.outer_end)
        if not start_exact:
            inexact_start += 1
        if not end_exact:
            inexact_end += 1

        a, b = omap.span_to_original(sp.outer_start, sp.outer_end)
        chunk = raw[a:b]
        mapped_is_word = (
            0 <= a < b <= len(raw)
            and chunk.startswith(b"<w")
            and chunk.rstrip().endswith(b">")
        )
        if not mapped_is_word:
            bad_mapped_slice += 1

        if (not start_exact or not end_exact or not mapped_is_word) and len(examples) < 8:
            examples.append(
                {
                    "repaired_span": [sp.outer_start, sp.outer_end],
                    "start_exact": start_exact,
                    "end_exact": end_exact,
                    "mapped_span": [a, b],
                    "mapped_source": _short(chunk),
                }
            )

    return {
        "repaired_length": len(repaired),
        "converter_visible_word_spans": len(words),
        "inexact_start_boundaries": inexact_start,
        "inexact_end_boundaries": inexact_end,
        "bad_mapped_word_slices": bad_mapped_slice,
        "examples": examples,
    }


def main() -> int:
    allow = _paths(ALLOWLIST)
    lossy = set(_paths(LOSSY))
    manifest = repair.read_manifest(PATCHES)

    inventory = json.loads(CROSSING_INVENTORY.read_text(encoding="utf8"))
    crossing_paths = {event["path"] for event in inventory["events"]}

    tf_locations = [
        str(ROOT / "tf" / TF_VERSION),
        str(ROOT / PROVENANCE_DIR / TF_VERSION),
    ]
    api = Fabric(locations=tf_locations, silent="deep").load(NEEDED, silent="deep")
    if api is False or api is None:
        raise RuntimeError("current TF + provenance artifact did not load")

    rows: dict[str, dict] = {}
    for rel in allow:
        if rel not in manifest:
            raise RuntimeError(f"{rel}: allowlisted path missing from patch manifest")
        path = CORPUS / rel
        if not path.is_file():
            raise RuntimeError(f"{rel}: source file missing")

        raw = path.read_bytes()
        manifest_sha, patches = manifest[rel]
        actual_sha = sha256(raw).hexdigest()
        if actual_sha != manifest_sha:
            raise RuntimeError(
                f"{rel}: source SHA drift: {actual_sha} != {manifest_sha}"
            )

        source_measure = _source_measure(raw, patches)
        graph_measure = _graph_measure(api, rel, raw, rel in lossy)
        required_now = graph_measure["contract_a_failures"] > 0

        rows[rel] = {
            "source_sha256": actual_sha,
            "crossing_owned_by_issue_12": rel in crossing_paths,
            "repair_reasons": [patch.reason for patch in patches],
            "repair_classes": [_repair_class(patch) for patch in patches],
            "source_measurement": source_measure,
            "graph_measurement": graph_measure,
            "required_now": required_now,
        }

    result = {
        "schema": 1,
        "issue": 142,
        "source_version": "0.3",
        "tf_version": TF_VERSION,
        "allowlist_count": len(allow),
        "crossing_count": sum(
            row["crossing_owned_by_issue_12"] for row in rows.values()
        ),
        "non_crossing_count": sum(
            not row["crossing_owned_by_issue_12"] for row in rows.values()
        ),
        "required_now_count": sum(row["required_now"] for row in rows.values()),
        "rows": rows,
    }

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf8",
    )
    print(
        f"measured {len(rows)} exceptions: "
        f"{result['crossing_count']} crossing / "
        f"{result['non_crossing_count']} non-crossing / "
        f"{result['required_now_count']} currently required"
    )
    for rel, row in rows.items():
        sm = row["source_measurement"]
        gm = row["graph_measurement"]
        print(
            f"{rel}: required={row['required_now']} "
            f"inexact=({sm['inexact_start_boundaries']},"
            f"{sm['inexact_end_boundaries']}) "
            f"bad-slices={gm['invalid_word_slice']} "
            f"mismatch={gm['graph_mismatch']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
