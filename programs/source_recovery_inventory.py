#!/usr/bin/env python
"""Generate the machine-readable crossing-tag repair inventory for issue #12.

This is research evidence, not a repair policy. It records what the current pinned
manifest does and where it does it. Recovery disposition belongs in a separately
reviewed layer so observation cannot silently become an editorial decision.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tlhdig import repair, signs, source
from tlhdig.paths import CORPUS, PATCHES, PROGRAMS, REPORTS

CROSSING_REASON = "crossing tags: inner element closed before its parent"
_CLOSE = re.compile(rb"</([A-Za-z_][-\w.:]*)>")


class InventoryError(RuntimeError):
    """The checked-in manifest/source no longer has the expected measurable shape."""


def _active_paths(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out = set()
    for raw in path.read_text(encoding="utf8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.add(line.split("\t", 1)[0])
    return out


def crossing_delta(old: bytes, new: bytes) -> tuple[list[str], str]:
    """Return ordered inserted closing tags and the close tag they precede.

    Current crossing patches are produced as inserted closing tags plus the old target
    (possibly with unique following context included in that target). Reject any
    different shape instead of guessing.
    """
    if not old or not new.endswith(old):
        raise InventoryError("crossing patch is not an inserted-prefix rewrite")
    prefix = new[: -len(old)]
    matches = list(_CLOSE.finditer(prefix))
    if not matches or b"".join(m.group(0) for m in matches) != prefix:
        raise InventoryError(f"crossing prefix is not only closing tags: {prefix[:120]!r}")
    boundary = _CLOSE.match(old)
    if boundary is None:
        raise InventoryError(f"crossing target does not start at a close tag: {old[:120]!r}")
    return (
        [m.group(1).decode("utf8", "surrogateescape") for m in matches],
        boundary.group(1).decode("utf8", "surrogateescape"),
    )


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def manifest_context_fingerprint(patches: list[repair.Patch]) -> str:
    """SHA-256 of the complete ordered patch sequence for one source file."""
    canonical = json.dumps(
        [
            [_b64(patch.old), _b64(patch.new), patch.reason]
            for patch in patches
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf8")).hexdigest()


def observation_fingerprint(
    *,
    source_sha256: str,
    patch_ordinal: int,
    intermediate_byte_start: int,
    original_byte_start: int,
    boundary: str,
    inserted_closures: list[str],
    old_base64: str,
    new_base64: str,
    manifest_context_fingerprint: str,
) -> str:
    """Canonical exact-observation signature used to bind reviewed dispositions."""
    canonical = json.dumps(
        [
            source_sha256,
            patch_ordinal,
            intermediate_byte_start,
            original_byte_start,
            boundary,
            inserted_closures,
            old_base64,
            new_base64,
            manifest_context_fingerprint,
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf8")).hexdigest()


def build_inventory(
    *,
    corpus: Path = CORPUS,
    manifest: Path = PATCHES,
    known_lossy: Path = PROGRAMS / "known_lossy.txt",
    contract_a_known: Path = PROGRAMS / "contract_a_known.txt",
    context_bytes: int = 160,
) -> list[dict]:
    """Measure every crossing patch against its actual sequential byte stream."""
    entries = repair.read_manifest(manifest)
    lossy = _active_paths(known_lossy)
    contract = _active_paths(contract_a_known)
    rows: list[dict] = []

    for rel, (expected_sha, patches) in sorted(entries.items()):
        source = corpus / rel
        if not source.is_file():
            raise InventoryError(f"manifest source missing: {rel}")
        original = source.read_bytes()
        actual_sha = sha256(original).hexdigest()
        if actual_sha != expected_sha:
            raise InventoryError(
                f"source sha mismatch for {rel}: {actual_sha} != {expected_sha}"
            )

        current = original
        prior: list[repair.Patch] = []
        manifest_fp = manifest_context_fingerprint(patches)
        for ordinal, patch in enumerate(patches, start=1):
            n = current.count(patch.old)
            if n != 1:
                raise InventoryError(
                    f"{rel} patch {ordinal}: target occurs {n} times in sequential stream"
                )
            start = current.find(patch.old)

            if patch.reason == CROSSING_REASON:
                closures, boundary = crossing_delta(patch.old, patch.new)
                # Prefer literal source evidence when the crossing target itself is
                # still present exactly once in the immutable file. OffsetMap operates
                # on whole manifest replacement ranges, whose uniqueness context can
                # make an unchanged suffix look edited (KUB 6.46, IBoT 4.235).
                direct_count = original.count(patch.old)
                if direct_count == 1:
                    original_start = original.find(patch.old)
                    exact = True
                    offset_method = "direct_unique_target"
                else:
                    omap = repair.OffsetMap(original, prior)
                    original_start = omap.to_original(start)
                    exact = omap.is_exact(start)
                    offset_method = (
                        "offset_map_exact" if exact else "offset_map_inexact"
                    )
                lo = max(0, original_start - context_bytes)
                hi = min(len(original), original_start + context_bytes)
                old_base64 = _b64(patch.old)
                new_base64 = _b64(patch.new)
                rows.append(
                    {
                        "event_id": f"{rel}:{ordinal}",
                        "path": rel,
                        "source_sha256": actual_sha,
                        "patch_ordinal": ordinal,
                        "intermediate_byte_start": start,
                        "original_byte_start": original_start,
                        "original_offset_exact": exact,
                        "original_offset_method": offset_method,
                        "boundary": boundary,
                        "inserted_closures": closures,
                        "inserted_close_count": len(closures),
                        "current_known_lossy": rel in lossy,
                        "current_contract_a_known": rel in contract,
                        "old_base64": old_base64,
                        "new_base64": new_base64,
                        "manifest_context_fingerprint": manifest_fp,
                        "later_patch_count": len(patches) - ordinal,
                        "later_patch_reasons": [
                            later.reason for later in patches[ordinal:]
                        ],
                        "observation_fingerprint": observation_fingerprint(
                            source_sha256=actual_sha,
                            patch_ordinal=ordinal,
                            intermediate_byte_start=start,
                            original_byte_start=original_start,
                            boundary=boundary,
                            inserted_closures=closures,
                            old_base64=old_base64,
                            new_base64=new_base64,
                            manifest_context_fingerprint=manifest_fp,
                        ),
                        "original_context_start": lo,
                        "original_context_end": hi,
                        "original_context_base64": _b64(original[lo:hi]),
                    }
                )

            current = current[:start] + patch.new + current[start + len(patch.old) :]
            prior.append(patch)

    return rows


_LB_OPEN = re.compile(rb"<lb(?:\s|/?>)")
_W_OPEN = re.compile(rb"<w(?:\s|/?>)")


def measure_filtered_word_loss(data: bytes) -> dict:
    """Measure exactly what check_signs.py loses when empty sign tokens are filtered."""
    failing: list[dict] = []
    lost_total = 0
    for sp in source.scan(data):
        if sp.tag != "w":
            continue
        inner = source.inner_bytes(data, sp)
        tokens = signs.tokenise_word(inner)
        kept = "".join(
            token.srcxml + token.after
            for token in tokens
            if token.type != "empty"
        ).encode("utf8")
        all_empty = all(token.type == "empty" for token in tokens)
        if all_empty or kept == inner:
            continue

        dropped = [
            (token.srcxml + token.after).encode("utf8")
            for token in tokens
            if token.type == "empty" and (token.srcxml or token.after)
        ]
        lost = len(inner) - len(kept)
        if lost <= 0:
            raise InventoryError(
                f"filtered-loss accounting is not a strict byte loss at w@{sp.outer_start}"
            )
        if sum(len(part) for part in dropped) != lost:
            raise InventoryError(
                f"filtered-loss segments do not balance at w@{sp.outer_start}: "
                f"{sum(len(part) for part in dropped)} != {lost}"
            )
        lost_total += lost
        failing.append(
            {
                "outer_start": sp.outer_start,
                "outer_end": sp.outer_end,
                "inner_start": sp.inner_start,
                "inner_end": sp.inner_end,
                "inner_bytes": len(inner),
                "lost_bytes": lost,
                "lb_open_count": len(_LB_OPEN.findall(inner)),
                "nested_w_open_count": len(_W_OPEN.findall(inner)),
                "dropped_segments_base64": [_b64(part) for part in dropped],
            }
        )
    return {
        "failing_words": len(failing),
        "lost_bytes": lost_total,
        "words": failing,
    }


def measure_crossing_file_effects(
    rows: list[dict],
    *,
    corpus: Path = CORPUS,
    manifest: Path = PATCHES,
) -> dict[str, dict]:
    """Measure current filtered sign loss independently for every crossing-tag file."""
    entries = repair.read_manifest(manifest)
    known_by_path = {
        row["path"]: row["current_known_lossy"]
        for row in rows
    }
    out: dict[str, dict] = {}
    for rel in sorted({row["path"] for row in rows}):
        expected_sha, patches = entries[rel]
        original = (corpus / rel).read_bytes()
        data = repair.apply(original, patches, expect_sha=expected_sha)
        effect = measure_filtered_word_loss(data)
        known = bool(known_by_path.get(rel))
        effect["current_known_lossy"] = known
        effect["known_lossy_matches_measured_loss"] = (
            known == (effect["failing_words"] > 0)
        )
        out[rel] = effect
    return out


def summarize(rows: list[dict], effects: dict[str, dict] | None = None) -> dict:
    files = {row["path"] for row in rows}
    lossy_files = {row["path"] for row in rows if row["current_known_lossy"]}
    contract_files = {row["path"] for row in rows if row["current_contract_a_known"]}
    boundaries = Counter(row["boundary"] for row in rows)
    closures = Counter(name for row in rows for name in row["inserted_closures"])
    summary = {
        "event_count": len(rows),
        "file_count": len(files),
        "inserted_close_count": sum(row["inserted_close_count"] for row in rows),
        "multi_close_event_count": sum(row["inserted_close_count"] > 1 for row in rows),
        "crossing_events_with_later_patches": sum(
            row["later_patch_count"] > 0 for row in rows
        ),
        "max_inserted_close_count": max(
            (row["inserted_close_count"] for row in rows), default=0
        ),
        "boundary_counts": dict(sorted(boundaries.items())),
        "closure_counts": dict(sorted(closures.items())),
        "known_lossy_crossing_file_count": len(lossy_files),
        "contract_a_crossing_file_count": len(contract_files),
    }
    if effects is not None:
        summary.update(
            {
                "measured_filtered_loss_file_count": sum(
                    effect["failing_words"] > 0 for effect in effects.values()
                ),
                "measured_filtered_loss_word_count": sum(
                    effect["failing_words"] for effect in effects.values()
                ),
                "measured_filtered_lost_bytes": sum(
                    effect["lost_bytes"] for effect in effects.values()
                ),
                "known_lossy_measurement_disagreement_file_count": sum(
                    not effect["known_lossy_matches_measured_loss"]
                    for effect in effects.values()
                ),
            }
        )
    return summary


def payload(rows: list[dict], effects: dict[str, dict] | None = None) -> dict:
    return {
        "schema": 2,
        "scope": "crossing-tag repair observations for pinned TLHdig 0.3",
        "reason": CROSSING_REASON,
        "policy": (
            "Observation only. Recovery/evidence disposition is intentionally not "
            "encoded in this file."
        ),
        "summary": summarize(rows, effects),
        "events": rows,
        "file_effects": effects or {},
    }


def render(rows: list[dict], effects: dict[str, dict] | None = None) -> str:
    return json.dumps(
        payload(rows, effects), indent=2, ensure_ascii=True, sort_keys=True
    ) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="write reports/source-recovery-inventory.json",
    )
    args = parser.parse_args(argv)

    rows = build_inventory()
    effects = measure_crossing_file_effects(rows)
    text = render(rows, effects)
    if args.write:
        REPORTS.mkdir(exist_ok=True)
        out = REPORTS / "source-recovery-inventory.json"
        out.write_text(text, encoding="utf8")
        print(out.relative_to(REPORTS.parent))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
