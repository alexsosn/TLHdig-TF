"""TDD contract for measured Contract-A provenance exceptions (#142)."""
from __future__ import annotations

import json
from pathlib import Path

from tlhdig import featuremeta
from tlhdig.paths import PROGRAMS, REPORTS


EXPECTED_SRC_SPAN_DESCRIPTION = (
    "byte range in the immutable source file named by src_file; repaired-source "
    "coordinates are translated back through OffsetMap. Files in "
    "contract_a_known.txt are measured exceptions where Contract A cannot yet "
    "reconstruct the immutable source exactly."
)

NON_CROSSING_REASON_TOKENS = {
    "CTH 372_XML_GEBET/KUB 31.127+.xml": ("stray </w>", "inexact"),
    "CTH 526_XML_KULTINV/KUB 42.100+.xml": ("stray </w>", "inexact"),
    "CTH 526_XML_KULTINV/VS.NF 12.111.xml": ("stray </w>", "inexact"),
    "CTH 529_XML_KULTINV/KBo 12.53+.xml": ("stray </w>", "inexact"),
    "CTH 581_XML_HDivT/KBo 18.142.xml": ("attribute", "graph content"),
    "CTH 790_XML_TLH/KBo 64.188.xml": ("ODF", "inexact"),
    "CTH 831_XML_TLH/KBo 64.209.xml": ("malformed <w", "inexact"),
}


def _allowlist() -> tuple[str, dict[str, str]]:
    text = (PROGRAMS / "contract_a_known.txt").read_text(encoding="utf8")
    rows = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        rel, sep, reason = line.partition("\t")
        assert sep, f"allowlist row has no tab-separated reason: {line!r}"
        rows[rel] = reason
    return text, rows


def _census() -> dict:
    return json.loads(
        (REPORTS / "contract-a-exception-census.json").read_text(encoding="utf8")
    )


def test_frozen_census_measures_every_current_exception() -> None:
    data = _census()
    _text, allow = _allowlist()

    assert data["allowlist_count"] == 16
    assert data["crossing_count"] == 9
    assert data["non_crossing_count"] == 7
    assert data["required_now_count"] == 16
    assert set(data["rows"]) == set(allow)

    for rel, row in data["rows"].items():
        assert row["source_sha256"]
        assert row["repair_reasons"]
        assert row["repair_classes"]
        assert row["required_now"] is True
        assert row["graph_measurement"]["contract_a_failures"] > 0, rel
        assert "inexact_start_boundaries" in row["source_measurement"]
        assert "inexact_end_boundaries" in row["source_measurement"]


def test_allowlist_explains_crossing_and_non_crossing_root_causes() -> None:
    text, allow = _allowlist()
    data = _census()

    assert "9 crossing" in text
    assert "7 non-crossing" in text

    crossing = {
        rel for rel, row in data["rows"].items()
        if row["crossing_owned_by_issue_12"]
    }
    non_crossing = set(data["rows"]) - crossing

    assert len(crossing) == 9
    assert non_crossing == set(NON_CROSSING_REASON_TOKENS)

    for rel in crossing:
        assert "crossing" in allow[rel].lower(), rel

    for rel, tokens in NON_CROSSING_REASON_TOKENS.items():
        reason = allow[rel]
        assert "crossing-tag" not in reason.lower(), rel
        for token in tokens:
            assert token.lower() in reason.lower(), (rel, token, reason)


def test_src_span_metadata_describes_immutable_source_coordinates() -> None:
    description = featuremeta.DESCRIPTIONS["src_span"]

    assert description == EXPECTED_SRC_SPAN_DESCRIPTION
    assert "166 repaired documents" not in description
    assert "indexes the repaired byte stream" not in description
