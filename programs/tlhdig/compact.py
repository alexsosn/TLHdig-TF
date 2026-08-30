"""Compact .tf node feature files by grouping nodes that share a value.

The TF file format states that a node spec denotes a *set*: `1-3,5-10,15` is legal and
means exactly those nodes.  TF's writer nonetheless emits one line per node, which for
this corpus costs 124 MB on `morph.tf`, where one 300-character alternative-set string
is repeated 231,131 times.

Grouping is semantics-preserving: the same node still receives the same value, and the
format's "last assignment wins" rule is unaffected because each node appears once.
"""

from __future__ import annotations

from pathlib import Path


def _split(path: Path) -> tuple[str, list[str]]:
    text = path.read_text(encoding="utf8")
    head, _, body = text.partition("\n\n")
    # TF reads with `for line in fh`, which yields no line after the final newline.
    # `split("\n")` does, so drop that one artefact -- every other empty line is real.
    if body.endswith("\n"):
        body = body[:-1]
    return head + "\n\n", body.split("\n")


def _nodes_of(spec: str) -> list[int]:
    out = []
    for part in spec.split(","):
        if not part:
            continue
        if "-" in part[1:]:
            a, b = part.split("-", 1)
            lo, hi = sorted((int(a), int(b)))
            out.extend(range(lo, hi + 1))
        else:
            out.append(int(part))
    return out


def _parse(body: list[str]):
    """Yield (nodes, value), honouring TF's optimised form.

    A line with no tab carries only a value; its node is the running implicit node,
    which advances to max(nodes) + 1 after **every** line (tf/core/data.py:_readDataTf).
    Crucially, such a line is *not* a node spec -- `after.tf` legitimately holds the
    bare value '-'.

    An **empty line is a value too**: TF writes `''` that way, and its reader takes
    `fields = [""]`, `valTf = ""`, then advances the implicit node like any other line.
    Skipping empty lines here desynchronised the counter, so every value after the first
    empty one was rewritten onto the wrong node -- 5 of 6 `after` values in a six-sign
    document, and `<sGr>UR.SAG</sGr>` shipped as `<sGr>UR-SAG</sGr>`.
    """
    implicit = 1
    for line in body:
        if "\t" in line:
            spec, _, value = line.partition("\t")
            nodes = _nodes_of(spec)
            if not nodes:
                continue
        else:
            nodes = [implicit]
            value = line
        implicit = max(nodes) + 1
        yield nodes, value


def read_values(path: Path) -> dict[int, str]:
    """Expand a node feature to {node: value}."""
    _, body = _split(path)
    return {n: v for nodes, v in _parse(body) for n in nodes}


def _spec(nodes: list[int]) -> str:
    """Render a sorted node list as the shortest spec of singletons and ranges."""
    parts = []
    start = prev = nodes[0]
    for n in nodes[1:]:
        if n == prev + 1:
            prev = n
            continue
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = n
    parts.append(str(start) if start == prev else f"{start}-{prev}")
    return ",".join(parts)


def compact_file(path: Path) -> bool:
    """Rewrite one node feature file in place.  Returns False for non-node features."""
    head, body = _split(path)
    if not head.lstrip().startswith("@node"):
        return False

    groups: dict[str, list[int]] = {}
    for nodes, value in _parse(body):
        groups.setdefault(value, []).extend(nodes)

    lines = []
    for value, nodes in groups.items():
        nodes.sort()
        lines.append(f"{_spec(nodes)}\t{value}")
    # keep output deterministic and roughly in node order
    lines.sort(key=lambda l: int(l.split("\t", 1)[0].split(",")[0].split("-")[0]))
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf8")
    return True


def compact_dir(d: Path) -> list[tuple[str, int, int]]:
    """Compact every node feature in a directory.  Returns (name, before, after)."""
    out = []
    # TF keeps its binary cache in a directory literally named `.tf`, which the
    # glob also matches.
    for f in sorted(x for x in d.glob("*.tf") if x.is_file()):
        before = f.stat().st_size
        if compact_file(f):
            out.append((f.name, before, f.stat().st_size))
    return out
