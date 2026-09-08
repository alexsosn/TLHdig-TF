#!/usr/bin/env python3
"""Measure released features relevant to corpus-specific TF rendering (#42).

The script reads node-feature files directly. It deliberately avoids ``oslots`` and
loading the full Text-Fabric graph, so the research gate is reproducible in ordinary
CI even though a complete browser load is multi-gigabyte.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROGRAMS = Path(__file__).resolve().parent
ROOT = PROGRAMS.parent
sys.path.insert(0, str(PROGRAMS))

from tlhdig import TF_VERSION

SIGN_FEATURES = (
    "sgr",
    "agr",
    "det",
    "missing",
    "laes",
    "ras",
    "add",
    "corr",
    "subscr",
    "materlect",
    "surplus",
    "num",
)
# These four flags are emitted for every sign as explicit integer 0/1 values. A raw
# node-feature row therefore means "the feature is defined", not "the state applies".
# The other selected features are sparse: a row itself denotes a relevant state/value.
EXPLICIT_ZERO_FLAGS = frozenset({"sgr", "agr", "det", "num"})
WORD_METRICS = ("nanalyses", "nselected")
LINE_FEATURES = ("cu", "cudirty")


def data_rows(path: Path):
    """Yield ``(node_spec, value)`` rows after a TF node-feature header."""

    in_body = False
    with path.open(encoding="utf8") as stream:
        for raw in stream:
            line = raw.rstrip("\r\n")
            if not in_body:
                if not line:
                    in_body = True
                continue
            if not line:
                continue
            spec, sep, value = line.partition("\t")
            if not sep:
                raise ValueError(f"{path}: malformed TF data row: {line!r}")
            yield spec, value


def expand_node_spec(spec: str):
    for part in spec.split(","):
        part = part.strip()
        if not part:
            raise ValueError(f"empty node-spec part in {spec!r}")
        if "-" in part:
            first, last = part.split("-", 1)
            first_i = int(first)
            last_i = int(last)
            if last_i < first_i:
                raise ValueError(f"descending node range {part!r}")
            yield from range(first_i, last_i + 1)
        else:
            yield int(part)


def state_is_active(feature: str, value: str) -> bool:
    """Whether a stored feature value represents a renderer-relevant state."""

    if feature in EXPLICIT_ZERO_FLAGS:
        return value.strip() not in {"", "0"}
    return True


def load_special_states(tf_dir: Path):
    states: dict[int, dict[str, str]] = defaultdict(dict)
    counts: dict[str, int] = {}
    for feature in SIGN_FEATURES:
        path = tf_dir / f"{feature}.tf"
        if not path.exists():
            counts[feature] = 0
            continue
        count = 0
        for spec, value in data_rows(path):
            if not state_is_active(feature, value):
                continue
            for node in expand_node_spec(spec):
                states[node][feature] = value
                count += 1
        counts[feature] = count
    return states, counts


def sampled_nodes(states: dict[int, dict[str, str]], limit: int):
    by_feature: dict[str, list[int]] = {feature: [] for feature in SIGN_FEATURES}
    by_combo: dict[tuple[str, ...], list[int]] = defaultdict(list)
    combo_counts = Counter()

    for node in sorted(states):
        combo = tuple(sorted(states[node]))
        combo_counts[combo] += 1
        if len(by_combo[combo]) < limit:
            by_combo[combo].append(node)
        for feature in combo:
            if len(by_feature[feature]) < limit:
                by_feature[feature].append(node)

    wanted = set()
    for nodes in by_feature.values():
        wanted.update(nodes)
    for nodes in by_combo.values():
        wanted.update(nodes)
    return by_feature, by_combo, combo_counts, wanted


def values_for_nodes(path: Path, wanted: set[int]) -> dict[int, str]:
    """Read values only for a small requested node set."""

    if not path.exists() or not wanted:
        return {}
    result = {}
    pending = set(wanted)
    for spec, value in data_rows(path):
        if not pending:
            break
        for node in expand_node_spec(spec):
            if node in pending:
                result[node] = value
                pending.remove(node)
                if not pending:
                    break
    return result


def numeric_metric(tf_dir: Path, feature: str, threshold: int = 1, limit: int = 5):
    path = tf_dir / f"{feature}.tf"
    count = 0
    examples = []
    if not path.exists():
        return {"count_gt_1": 0, "examples": []}
    for spec, value in data_rows(path):
        try:
            numeric = int(value)
        except ValueError:
            continue
        if numeric <= threshold:
            continue
        for node in expand_node_spec(spec):
            count += 1
            if len(examples) < limit:
                examples.append({"node": node, "value": numeric})
    return {"count_gt_1": count, "examples": examples}


def feature_presence(tf_dir: Path, feature: str) -> int:
    path = tf_dir / f"{feature}.tf"
    if not path.exists():
        return 0
    total = 0
    for spec, _value in data_rows(path):
        total += sum(1 for _ in expand_node_spec(spec))
    return total


def report(tf_dir: Path, sample_limit: int = 3) -> dict:
    states, feature_counts = load_special_states(tf_dir)
    by_feature, by_combo, combo_counts, wanted = sampled_nodes(states, sample_limit)

    symbols = values_for_nodes(tf_dir / "sym.tf", wanted)
    source_files = values_for_nodes(tf_dir / "src_file.tf", wanted)
    source_lines = values_for_nodes(tf_dir / "srcln.tf", wanted)

    def example(node: int):
        return {
            "node": node,
            "sym": symbols.get(node),
            "src_file": source_files.get(node),
            "srcln": source_lines.get(node),
            "states": states[node],
        }

    feature_examples = {
        feature: [example(node) for node in nodes]
        for feature, nodes in by_feature.items()
        if nodes
    }
    combination_examples = [
        {
            "features": list(combo),
            "count": combo_counts[combo],
            "examples": [example(node) for node in nodes],
        }
        for combo, nodes in sorted(
            by_combo.items(), key=lambda item: (-combo_counts[item[0]], item[0])
        )
    ]

    return {
        "tf_version": TF_VERSION,
        "sign_feature_counts": feature_counts,
        "signs_with_any_selected_state": len(states),
        "combination_count": len(combo_counts),
        "combination_examples": combination_examples,
        "feature_examples": feature_examples,
        "competing_analysis_metrics": {
            feature: numeric_metric(tf_dir, feature, limit=sample_limit)
            for feature in WORD_METRICS
        },
        "line_feature_counts": {
            feature: feature_presence(tf_dir, feature) for feature in LINE_FEATURES
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tf-dir",
        type=Path,
        default=ROOT / "tf" / TF_VERSION,
        help="released TF directory (default: current committed release)",
    )
    parser.add_argument("--sample-limit", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        result = report(args.tf_dir, sample_limit=max(1, args.sample_limit))
    except (OSError, ValueError) as exc:
        print(f"renderer research: ERROR: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
