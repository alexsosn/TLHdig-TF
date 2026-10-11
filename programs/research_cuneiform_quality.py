"""Read-only evidence inventory for #21 alignment gaps and #23 sign disagreements.

Every record retains alternatives and overlapping candidate flags. Never vote a
replacement into cu_sign. Generated JSONL reports are research, not corrections.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

from tlhdig import TF_VERSION, appcheck, compact, cuneiform, signrefs, signref_inputs
from tlhdig.paths import ROOT, PROGRAMS, REPORTS


def is_pua(ch):
    n = ord(ch)
    return 0xE000 <= n <= 0xF8FF or 0xF0000 <= n <= 0xFFFFD or 0x100000 <= n <= 0x10FFFD


def classify_gap(cu, syms, multi):
    points = cuneiform.split_points(cu)
    flags = []
    if cuneiform.UNRENDERED_SOURCE in cu:
        flags.append("unrendered")
    if any(is_pua(c) for c in cu):
        flags.append("pua")
    if cuneiform.PLACEHOLDER in points:
        flags.append("placeholder")
        if points.count(cuneiform.PLACEHOLDER) != syms.count(cuneiform.ILLEGIBLE):
            flags.append("damage-count-mismatch")
    if any(s in multi for s in syms):
        flags.append("compound")
    if any(cuneiform.numeral(s) is not None for s in syms):
        flags.append("numeral")
    if any(c in cu for c in "?|°"):
        flags.append("editorial")
    if len(points) != len(syms):
        flags.append("count-mismatch")
    if not cu:
        primary = "no-cu"
    elif not syms:
        primary = "no-sign-slots"
    else:
        primary = next((v for v in ("unrendered", "pua", "damage-count-mismatch",
                  "compound", "numeral", "editorial", "count-mismatch") if v in flags), "unknown")
    return dict(primary=primary, flags=flags, points=len(points), slots=len(syms),
                delta=len(points) - len(syms),
                puaCodepoints=sorted({f"U+{ord(c):04X}" for c in cu if is_pua(c)}))


def classify_disagreement(reading, glyph, refs):
    v = refs.verdict(reading, glyph)
    status = ("unknown" if v.unknown else
              "split" if v.support and v.against else
              "supported" if v.support else "all-disagree")
    candidates = {k: sorted(vals) for k, vals in sorted(refs.table.get(reading, {}).items())}
    return dict(status=status, reference_conflict=refs.contested(reading),
                sourceCandidates=candidates, sources=len(candidates),
                traditions=len(refs.lineages(reading)),
                equivalenceAwareSupport=v.support, equivalenceAwareAgainst=v.against,
                alternatives=sorted(v.alternatives))


def feat(directory, name, lo, hi):
    path = directory / (name + ".tf")
    if not path.is_file():
        return {}
    return {n: value for nodes, value in compact._parse(compact._split(path)[1])
            for n in nodes if lo <= n <= hi}


def line_to_sign(directory, low, high):
    owners, slots = {}, defaultdict(list)
    implicit = 1
    for raw in compact._split(directory / "oslots.tf")[1]:
        if "\t" in raw:
            key, _, val = raw.partition("\t")
            nodes = compact._nodes_of(key)
            if not nodes:
                continue
        else:
            nodes, val = [implicit], raw
        implicit = max(nodes) + 1
        for node in nodes:
            if low <= node <= high:
                for sign in compact._nodes_of(val):
                    owners[sign] = node
                    slots[node].append(sign)
    return owners, slots


def _emit(handle, data):
    handle.write(json.dumps(data, sort_keys=True, ensure_ascii=False) + "\n")


def inventory(directory, outdir, *, do_gaps=True, do_signrefs=True, refdir=None):
    ranges = appcheck.node_ranges(directory)
    low, high = ranges["line"]
    slo, shi = ranges["sign"]
    owner, slots = line_to_sign(directory, low, high)
    syms = feat(directory, "sym", slo, shi)
    glyphs = feat(directory, "cu_sign", slo, shi)
    anchor = feat(directory, "anchor", slo, shi)
    levels = feat(directory, "cu_aligned", low, high)
    lnr = feat(directory, "lnr", low, high)
    txtid = feat(directory, "txtid", low, high)
    outdir.mkdir(parents=True, exist_ok=True)
    out = {}

    if do_gaps:
        cu = feat(directory, "cu", low, high)
        multi = cuneiform.load_multi(PROGRAMS / "signmap-multi.tsv")
        primary, flags = Counter(), Counter()
        with gzip.open(outdir / "research-alignment-gaps-21.jsonl.gz", "wt", encoding="utf8") as f:
            for line in sorted(levels):
                if int(levels[line] or 0) != 0:
                    continue
                reading = [syms.get(s, "") for s in slots[line] if not anchor.get(s)]
                original = cu.get(line, "")
                case = classify_gap(original, reading, multi)
                primary[case["primary"]] += 1
                flags.update(case["flags"])
                _emit(f, dict(lineNode=line, txtid=txtid.get(line), lnr=lnr.get(line),
                              cu=original, readings=reading, **case))
        out["gaps"] = dict(issue=21, total=sum(primary.values()),
                           primary=dict(primary), overlappingFlags=dict(flags),
                           evidence="candidate explanations; no automated correction")

    if do_signrefs:
        specs = signref_inputs.load_lock(PROGRAMS / "signrefs.lock.json")
        result = signref_inputs.inspect_local(specs, refdir)
        if result.state != signref_inputs.PASSED:
            raise ValueError(f"locked reference set not available: {result.state}")
        refs = signrefs.load(refdir)
        known = {name for tables in refs.table.values() for name in tables}
        if known != {spec.name for spec in specs}:
            raise ValueError("verified references did not all parse")
        statuses, flags, top = Counter(), Counter(), Counter()
        lang = feat(directory, "lang", slo, shi)
        with gzip.open(outdir / "research-sign-disagreements-23.jsonl.gz", "wt", encoding="utf8") as f:
            for sign, glyph in sorted(glyphs.items()):
                if not glyph or anchor.get(sign):
                    continue
                reading = (syms.get(sign) or "").strip()
                if reading in ("", "x", "…"):
                    continue
                case = classify_disagreement(reading, glyph, refs)
                statuses[case["status"]] += 1
                if case["status"] != "all-disagree":
                    continue
                attributes = []
                if any(is_pua(c) for c in glyph):
                    attributes.append("pua")
                if reading.lstrip("+").isdigit():
                    attributes.append("numeral")
                if len(glyph) > 1:
                    attributes.append("multi-codepoint")
                if case["reference_conflict"]:
                    attributes.append("reference-conflict")
                attributes.append("single-tradition" if case["traditions"] == 1 else
                                  "multiple-traditions")
                flags.update(attributes)
                top[(reading, glyph)] += 1
                line = owner.get(sign)
                _emit(f, dict(signNode=sign, lineNode=line, txtid=txtid.get(line),
                              lnr=lnr.get(line), lang=lang.get(sign),
                              cu_aligned=int(levels.get(line, 0) or 0),
                              reading=reading, cu_sign=glyph, flags=attributes, **case))
        out["disagreements"] = dict(issue=23, statuses=dict(statuses),
                                    allDisagree=statuses["all-disagree"],
                                    overlappingFlags=dict(flags),
                                    topPairs=[dict(reading=r, glyph=g, count=n)
                                              for (r, g), n in top.most_common(100)],
                                    evidence="outvoted is not equivalent to wrong")
    out["tfVersion"] = TF_VERSION
    (outdir / "research-cuneiform-quality-21-23.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf8")
    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["all", "gaps", "disagreements"], default="all")
    p.add_argument("--tfdir", type=Path, default=ROOT / "tf" / TF_VERSION)
    p.add_argument("--refs", type=Path, default=ROOT / "refs")
    p.add_argument("--outdir", type=Path, default=REPORTS)
    args = p.parse_args(argv)
    if not (args.tfdir / "otype.tf").is_file():
        p.error("current TF artifact not present")
    output = inventory(args.tfdir, args.outdir, do_gaps=args.mode != "disagreements",
                       do_signrefs=args.mode != "gaps", refdir=args.refs)
    print(json.dumps(output, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
