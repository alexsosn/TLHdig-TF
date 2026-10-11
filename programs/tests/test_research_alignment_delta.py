"""TDD gates for real-artifact impact report of mixed alignment PR #155."""
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _module():
    import research_alignment_delta
    return research_alignment_delta


def test_diff_counts_added_withdrawn_replaced_and_unchanged():
    change = _module().mapping_delta(
        {1: "𒀀", 2: "𒁀", 3: "𒀭", 4: "𒉿"},
        {1: "𒀀", 2: "𒁁", 4: "𒉿", 5: "𒋫"},
    )
    assert change["totalOld"] == 4
    assert change["totalNew"] == 4
    assert change["added"] == 1
    assert change["withdrawn"] == 1
    assert change["replaced"] == 1
    assert change["unchanged"] == 2
    assert change["nodesChanged"] == {2, 3, 5}


def test_protected_content_identity_rejects_unrelated_graph_change():
    diff = _module().changed_protected(
        {"main:otype.tf": "sha:x", "main:cu_sign.tf": "sha:y",
         "main:cu_pua_unmapped.tf": "sha:z"},
        {"main:otype.tf": "sha:different", "main:cu_sign.tf": "sha:new",
         "main:cu_pua_unmapped.tf": "sha:z"},
    )
    assert diff == ["main:otype.tf"]


def test_protected_identity_rejects_missing_existing_feature():
    changed = _module().changed_protected(
        {"main:otype.tf": "sha:x", "main:cu_sign.tf": "sha:y"},
        {"main:cu_sign.tf": "sha:z"},
    )
    assert "main:otype.tf" in changed


def test_reference_buckets_are_not_a_correction_oracle():
    from tlhdig.signrefs import References
    refs = References({"wa": {"osl": {"𒉿"}, "potnia": {"𒁀"}}})
    bucket = _module().reference_bucket
    assert bucket("wa", "𒉿", refs) == "split"
    assert bucket("wa", "𒊀", refs) == "all-disagree"
    assert bucket("unattested", "𒀀", refs) == "unknown"


def test_unevaluated_sign_is_not_voted_on():
    from tlhdig.signrefs import References
    assert _module().reference_bucket("x", "▒", References({})) == "excluded"


def test_comparison_refuses_unbound_source_text(tmp_path):
    from tlhdig import build_manifest
    old = tmp_path / "old"
    new = tmp_path / "new"
    old.mkdir()
    new.mkdir()
    (old / "cu.tf").write_text("@node\n\n1\t𒀀\n", encoding="utf8")
    (new / "cu.tf").write_text("@node\n\n1\t𒁀\n", encoding="utf8")
    assert build_manifest._output_sha256(old / "cu.tf") != build_manifest._output_sha256(new / "cu.tf")


def test_derived_compound_counts_are_exactly_tied_to_cu_sign():
    """#21 RED: only exact derived codepoint lengths may change with alignment."""
    mod = _module()
    glyphs = {1: "𒀀", 2: "𒈨𒌍", 3: "▒", 4: "𒋡𒋗𒂃"}
    correct = {2: "2", 4: "3"}
    assert mod.derived_nsigns_mismatches(glyphs, correct) == []
    assert mod.derived_nsigns_mismatches(glyphs, {2: "1", 4: "3"}) == [2]
    assert mod.derived_nsigns_mismatches(glyphs, {2: "2"}) == [4]
    assert mod.derived_nsigns_mismatches(glyphs, {**correct, 1: "1"}) == [1]


def test_derived_nsigns_change_does_not_unprotect_other_features():
    """#21 RED: cu_nsigns is derived; unrelated features stay immutable."""
    mod = _module()
    before = {
        "main:cu_sign.tf": "old-glyphs",
        "main:cu_nsigns.tf": "old-counts",
        "main:cu.tf": "unchanged-source",
        "main:otype.tf": "unchanged-types",
    }
    after = {**before, "main:cu_sign.tf": "new-glyphs",
             "main:cu_nsigns.tf": "new-counts"}
    assert mod.changed_protected(before, after) == []
    after["main:cu.tf"] = "tampered-source"
    assert mod.changed_protected(before, after) == ["main:cu.tf"]


def test_candidate_workflow_snapshots_all_derived_baseline_inputs():
    """#21 RED: a real baseline audit requires the old compound counts file."""
    repo = Path(__file__).resolve().parents[2]
    workflow = (repo / ".github/workflows/research-alignment-delta-21.yml").read_text(encoding="utf8")
    assert "cp tf/0.4.0/cu_sign.tf /tmp/tlhdig-before/" in workflow
    assert "cp tf/0.4.0/cu_nsigns.tf /tmp/tlhdig-before/" in workflow


def test_nullable_transition_report_uses_deterministic_unambiguous_keys():
    """RED after real-corpus failure: None and string method states must coexist."""
    from collections import Counter
    import json
    summarize = _module().serialize_transitions
    counts = Counter({(None, "damage"): 3, ("compound", None): 2,
                      ("None", "damage"): 1, ("compound", "damage"): 4})
    first = summarize(counts)
    assert first == summarize(Counter(dict(reversed(list(counts.items())))))
    assert {tuple(json.loads(pair)): n for pair, n in first.items()} == dict(counts)
    assert list(first) == sorted(first)  # stable JSON serialization order


def test_nullable_alignment_level_transitions_remain_distinct():
    from collections import Counter
    import json
    result = _module().serialize_transitions(
        Counter({(None, "0"): 9, ("0", None): 3, ("0", "3"): 1})
    )
    assert {tuple(json.loads(key)): n for key, n in result.items()} == {
        (None, "0"): 9, ("0", None): 3, ("0", "3"): 1,
    }


def test_real_corpus_delta_forbids_new_readable_ellipsis_assignments():
    """RED #157: first hosted candidate mapped >100 lacuna sign slots to glyphs."""
    mod = _module()
    before = {10: "𒀀", 11: "𒉡"}
    after = {10: "𒀀", 11: "𒊭", 12: "𒌍", 13: "𒁀"}
    readings = {10: "…", 11: "…", 12: "…", 13: "ba"}
    assert mod.newly_asserted_lacuna_glyphs(before, after, readings) == [11, 12]
    assert mod.newly_asserted_lacuna_glyphs(
        {11: "𒉡"}, {11: "𒉡"}, {11: "…"},
    ) == []
    assert mod.newly_asserted_lacuna_glyphs(
        {}, {1: "▒"}, {1: "…"},
    ) == [1]
