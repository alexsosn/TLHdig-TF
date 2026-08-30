"""Check `app/config.yaml` against the dataset it describes.

Text-Fabric validates an app config only when `use()` actually loads the corpus, which
for this dataset means ~12 minutes and ~5 GB before a typo in a label is reported.  Worse,
a `features:` list naming something that does not exist on that node type fails silently
-- the field simply never renders, so the app looks fine and is quietly wrong.

This reads `otype.tf` for the node-type ranges and each feature file for the nodes it
covers, and answers the only question that matters: does every feature this config names
actually carry values on the node type it is named under?
"""

from __future__ import annotations

import re
from pathlib import Path

from . import compact

# `{lnno}`, `{index}. {lemma} {morph}` -- TF's template syntax.
TEMPLATE_FIELD = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)")


def node_ranges(tf_dir: Path) -> dict[str, tuple[int, int]]:
    """Inclusive (first, last) node number for every node type, from otype.tf."""
    out: dict[str, tuple[int, int]] = {}
    _, body = compact._split(tf_dir / "otype.tf")
    for nodes, value in compact._parse(body):
        lo, hi = min(nodes), max(nodes)
        if value in out:
            plo, phi = out[value]
            out[value] = (min(lo, plo), max(hi, phi))
        else:
            out[value] = (lo, hi)
    return out


def feature_path(tf_dir: Path, feature: str) -> Path | None:
    """Where a feature file lives -- the dataset, or the provenance module beside it."""
    here = tf_dir / f"{feature}.tf"
    if here.is_file():
        return here
    from . import PROVENANCE_DIR

    there = tf_dir.parent.parent / PROVENANCE_DIR / tf_dir.name / f"{feature}.tf"
    return there if there.is_file() else None


def covers(tf_dir: Path, feature: str, lo: int, hi: int) -> bool:
    """Does `feature` carry a value on at least one node in [lo, hi]?

    Streams and stops at the first hit; a feature usually has one in its first lines.
    """
    path = feature_path(tf_dir, feature)
    if path is None:
        return False
    _, body = compact._split(path)
    for nodes, _value in compact._parse(body):
        for n in nodes:
            if lo <= n <= hi:
                return True
    return False


def referenced_features(spec: dict) -> set[str]:
    """Every feature name one typeDisplay entry refers to."""
    names: set[str] = set()
    for key in ("label", "template"):
        value = spec.get(key)
        if isinstance(value, str):
            names.update(TEMPLATE_FIELD.findall(value))
    for key in ("features", "featuresBare"):
        value = spec.get(key)
        if isinstance(value, str):
            # TF accepts `lex:gloss` to mean "gloss, reached via lex"; take both halves.
            for token in value.split():
                names.update(t for t in token.split(":") if t)
    return names


def check(tf_dir: Path, config: dict) -> list[str]:
    """Return one message per problem; empty means the config matches the dataset."""
    problems: list[str] = []
    ranges = node_ranges(tf_dir)

    for ntype, spec in (config.get("typeDisplay") or {}).items():
        if ntype not in ranges:
            problems.append(f"typeDisplay.{ntype}: no such node type in otype.tf")
            continue
        lo, hi = ranges[ntype]
        for feat in sorted(referenced_features(spec or {})):
            if feature_path(tf_dir, feat) is None:
                problems.append(f"typeDisplay.{ntype}: feature {feat!r} does not exist")
            elif not covers(tf_dir, feat, lo, hi):
                problems.append(
                    f"typeDisplay.{ntype}: feature {feat!r} exists but has no value on "
                    f"any {ntype} node -- it would render as nothing"
                )

    data = config.get("dataDisplay") or {}
    for feat in data.get("excludedFeatures") or []:
        if feature_path(tf_dir, feat) is None:
            problems.append(f"dataDisplay.excludedFeatures: {feat!r} does not exist")

    fmt = data.get("textFormat")
    if fmt:
        # otext.tf is all metadata and usually has no body at all, so read the file
        # rather than the header `_split` carves off.
        otext = (tf_dir / "otext.tf").read_text(encoding="utf8")
        if f"@fmt:{fmt}=" not in otext:
            problems.append(f"dataDisplay.textFormat: {fmt!r} is not declared in otext.tf")

    return problems
