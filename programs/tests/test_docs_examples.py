from __future__ import annotations

import contextlib
import io
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
QUERYING = ROOT / "docs" / "querying.md"

EXAMPLE_RE = re.compile(
    r"<!--\s*executable-example:\s*([a-z0-9-]+)\s*-->\s*"
    r"```python\s*\n(.*?)```",
    re.DOTALL,
)
EXPECTED = (
    "load-selected",
    "section-text",
    "morphology-candidates",
    "editorial-extents",
    "cuneiform-alignment",
    "document-identity",
    "manuscript-relations",
)


def _examples() -> dict[str, str]:
    text = QUERYING.read_text(encoding="utf8")
    return {name: source for name, source in EXAMPLE_RE.findall(text)}


def test_curated_query_examples_are_present_and_compile() -> None:
    examples = _examples()
    assert tuple(examples) == EXPECTED
    for name in EXPECTED:
        compile(examples[name], f"docs/querying.md:{name}", "exec")


@pytest.mark.skipif(
    os.environ.get("TLHDIG_EXECUTE_DOC_EXAMPLES") != "1",
    reason="current-artifact example execution is an opt-in integration gate",
)
def test_curated_query_examples_execute_against_current_artifact() -> None:
    examples = _examples()
    assert tuple(examples) == EXPECTED

    namespace: dict[str, object] = {}
    sink = io.StringIO()
    for name in EXPECTED:
        with contextlib.redirect_stdout(sink):
            exec(
                compile(examples[name], f"docs/querying.md:{name}", "exec"),
                namespace,
                namespace,
            )

        if name == "load-selected":
            assert namespace.get("api") is not None
        elif name == "section-text":
            assert namespace.get("line") is not None
        elif name == "morphology-candidates":
            assert len(namespace.get("candidates", ())) > 1
        elif name == "editorial-extents":
            assert namespace.get("hits")
        elif name == "cuneiform-alignment":
            assert namespace.get("pairs")
        elif name == "document-identity":
            assert namespace.get("documents")
        elif name == "manuscript-relations":
            assert namespace.get("join_examples")
