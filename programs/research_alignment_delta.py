#!/usr/bin/env python
"""Real-artifact before/after audit for #21, without choosing scholarly corrections.

Data source: pinned current TF, exact source glyphs and independently pinned
sign-reference witnesses. This is a research report and not a merge approval.
"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tlhdig import TF_VERSION, appcheck, build_manifest, compact, signrefs, signref_inputs
from tlhdig.paths import PROGRAMS, ROOT

# Conversion-specific outputs allowed to differ. All source and linguistic
# features are protected by a complete normalized-output identity comparison.
ALLOWED = frozenset({
    "main:cu_sign.tf", "main:cu_aligned.tf", "main:cu_method.tf",
    "main:cu_undecided.tf", "main:cu_unrendered.tf",
    "main:cu_nsigns.tf",  # strictly derived from cu_sign; checked separately
})


def changed_protected(before: dict, after: dict) -> list[str]:
    return sorted(k for k in set(before) | set(after)
                  if k not in ALLOWED and before.get(k) != after.get(k))


def derived_nsigns_mismatches(
    glyphs: dict[int, str], nsigns: dict[int, str],
) -> list[int]:
    """Every cu_nsigns must be exactly len(cu_sign)>1; no dangling counts."""
    expected = {node: str(len(glyph)) for node, glyph in glyphs.items()
                if len(glyph) > 1}
    return sorted(node for node in set(expected) | set(nsigns)
                  if expected.get(node) != nsigns.get(node))


def newly_asserted_lacuna_glyphs(
    before: dict[int, str], after: dict[int, str], readings: dict[int, str],
) -> list[int]:
    """New/changed cu_sign values asserted for an unspecified XML lacuna.

    Preserve the baseline as-is for a controlled comparison; reject any
    *new* claim that an ellipsis slot represents a specific visible sign.
    This is source semantics, not a sign-list majority vote (#157).
    """
    return sorted(node for node, glyph in after.items()
                  if readings.get(node, "").strip() == "…"
                  and before.get(node) != glyph)


def mapping_delta(before: dict[int, str], after: dict[int, str]) -> dict:
    old = set(before)
    new = set(after)
    common = old & new
    replaced = {n for n in common if before[n] != after[n]}
    added, withdrawn = new - old, old - new
    return {
        "totalOld": len(old), "totalNew": len(new),
        "added": len(added), "withdrawn": len(withdrawn),
        "replaced": len(replaced), "unchanged": len(common - replaced),
        "nodesChanged": replaced | added | withdrawn,
    }


def serialize_transitions(transitions: Counter) -> dict[str, int]:
    """Stable, unambiguous JSON pair keys for nullable TF transition states.

    A missing level/method (None) must not sort against a string, or become
    indistinguishable from the literal string "None" in the research report.
    """
    pairs = [(json.dumps([before, after], ensure_ascii=False), count)
             for (before, after), count in transitions.items()]
    return dict(sorted(pairs))


def reference_bucket(reading: str, glyph: str, refs: signrefs.References) -> str:
    if reading in ("", "x", "…") or not glyph or "▒" in glyph:
        return "excluded"
    verdict = refs.verdict(reading, glyph)
    if verdict.unknown:
        return "unknown"
    if verdict.support and verdict.against:
        return "split"
    if verdict.support:
        return "supported"
    return "all-disagree"


def _line_owners(tfdir: Path, affected: set[int]) -> dict[int, int]:
    if not affected:
        return {}
    first, last = appcheck.node_ranges(tfdir)["line"]
    owners = {}
    for nodes, value in compact._parse(compact._split(tfdir / "oslots.tf")[1]):
        for line in nodes:
            if first <= line <= last:
                for sign in compact._nodes_of(value):
                    if sign in affected:
                        if sign in owners and owners[sign] != line:
                            raise ValueError(f"sign has multiple parent lines: {sign}")
                        owners[sign] = line
    return owners


def _verified_refs(refdir: Path) -> signrefs.References:
    specs = signref_inputs.load_lock(PROGRAMS / "signrefs.lock.json")
    state = signref_inputs.inspect_local(specs, refdir)
    if state.state != signref_inputs.PASSED:
        raise ValueError(f"reference set incomplete or unverified: {state.state}")
    refs = signrefs.load(refdir)
    expected = {spec.name for spec in specs}
    actual = {source for table in refs.table.values() for source in table}
    if actual != expected:
        raise ValueError(f"verified sources not all parsed: {expected - actual}")
    return refs


def analyze(
    before_dir: Path, after_dir: Path, baseline_json: Path,
    provenance_dir: Path, refdir: Path, outdir: Path,
) -> dict:
    before_identity = json.loads(baseline_json.read_text(encoding="utf8"))
    after_identity = build_manifest.output_identity(after_dir, provenance_dir)
    violations = changed_protected(
        before_identity["files"], after_identity["files"]
    )
    if violations:
        raise ValueError("non-alignment TF output changed or vanished: "
                         + ", ".join(violations[:20]))
    old = compact.read_values(before_dir / "cu_sign.tf")
    new = compact.read_values(after_dir / "cu_sign.tf")
    for name, directory, glyphs in (
        ("baseline", before_dir, old), ("candidate", after_dir, new),
    ):
        observed = compact.read_values(directory / "cu_nsigns.tf")
        mismatches = derived_nsigns_mismatches(glyphs, observed)
        if mismatches:
            raise ValueError(
                f"{name} cu_nsigns is not derived from cu_sign: "
                f"{len(mismatches)} mismatches; first nodes {mismatches[:10]}"
            )
    metrics = mapping_delta(old, new)
    changed = metrics.pop("nodesChanged")
    old_level = compact.read_values(before_dir / "cu_aligned.tf")
    new_level = compact.read_values(after_dir / "cu_aligned.tf")
    old_method = compact.read_values(before_dir / "cu_method.tf")
    new_method = compact.read_values(after_dir / "cu_method.tf")
    sym = compact.read_values(after_dir / "sym.tf")
    new_ellipsis = newly_asserted_lacuna_glyphs(old, new, sym)
    if new_ellipsis:
        raise ValueError(
            "new legible glyphs asserted for unspecified ellipsis lacunae: "
            f"{len(new_ellipsis)} signs; first nodes {new_ellipsis[:10]}"
        )
    owner = _line_owners(after_dir, changed)
    lnr = compact.read_values(after_dir / "lnr.tf")
    txtid = compact.read_values(after_dir / "txtid.tf")
    refs = _verified_refs(refdir)
    before_votes, after_votes = Counter(), Counter()
    transitions = Counter()
    level_transitions = Counter()
    method_transitions = Counter()
    outdir.mkdir(parents=True, exist_ok=True)
    target = outdir / "research-alignment-delta-21.jsonl.gz"

    @lru_cache(maxsize=20_000)
    def vote(reading: str, glyph: str) -> str:
        return reference_bucket(reading, glyph, refs)

    with gzip.open(target, "wt", encoding="utf8") as fp:
        for sign in sorted(changed):
            previous, current = old.get(sign), new.get(sign)
            reading = sym.get(sign, "")
            previous_bucket = vote(reading, previous or "")
            current_bucket = vote(reading, current or "")
            before_votes[previous_bucket] += 1
            after_votes[current_bucket] += 1
            transitions[(previous_bucket, current_bucket)] += 1
            line = owner.get(sign)
            before_l = old_level.get(line) if line is not None else None
            after_l = new_level.get(line) if line is not None else None
            level_transitions[(before_l, after_l)] += 1
            method_transitions[(old_method.get(line), new_method.get(line))] += 1
            rec = {"signNode": sign, "lineNode": line,
                   "txtid": txtid.get(line), "lnr": lnr.get(line),
                   "reading": reading, "old": previous, "new": current,
                   "oldReference": previous_bucket,
                   "newReference": current_bucket,
                   "oldLevel": before_l, "newLevel": after_l,
                   "oldMethod": old_method.get(line), "newMethod": new_method.get(line)}
            fp.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    if len(owner) != len(changed):
        raise ValueError(f"{len(changed)-len(owner)} changed signs lack a line join")
    summary = {
        "issue": 21, "tfVersion": TF_VERSION, "comparison": metrics,
        "changedSignRecords": len(changed),
        "newLegibleEllipsisAssignments": len(new_ellipsis),
        "beforeReferenceVerdicts": dict(before_votes),
        "afterReferenceVerdicts": dict(after_votes),
        "referenceTransitions": serialize_transitions(transitions),
        "levelTransitions": serialize_transitions(level_transitions),
        "methodTransitions": serialize_transitions(method_transitions),
        "protectedFeatureDifferences": violations,
        "cases": target.name,
        "note": "Reference votes are evidence, not a glyph replacement oracle.",
    }
    (outdir / "research-alignment-delta-21.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf8",
    )
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", type=Path, default=ROOT / "tf" / TF_VERSION)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--provenance", type=Path,
                        default=ROOT / "tf-provenance" / TF_VERSION)
    parser.add_argument("--refs", type=Path, default=ROOT / "refs")
    parser.add_argument("--outdir", type=Path, default=ROOT / "reports")
    args = parser.parse_args(argv)
    try:
        report = analyze(args.before, args.after, args.baseline,
                         args.provenance, args.refs, args.outdir)
    except (ValueError, OSError) as exc:
        print(f"alignment delta rejected: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
