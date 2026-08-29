"""Prototype 3: bracket pairing without a stack."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import brackets as B


def _t():
    t = B.Tracker()
    t.start_line(1)
    return t


def test_simple_pair():
    t = _t()
    B.feed(t, "del_in", 5)
    B.feed(t, "del_fin", 9, offset=2)
    t.finish()
    (cl,) = t.clusters
    assert (cl.type, cl.start_sign, cl.end_sign, cl.end_offset) == ("del", 5, 9, 2)
    assert cl.orphan == "none" and not cl.crossesline


def test_crossing_families_both_pair():
    """del_in laes_in del_fin laes_fin -- a single LIFO stack pairs these wrongly."""
    t = _t()
    B.feed(t, "del_in", 1)
    B.feed(t, "laes_in", 2)
    B.feed(t, "del_fin", 3)
    B.feed(t, "laes_fin", 4)
    t.finish()
    got = {c.type: (c.start_sign, c.end_sign) for c in t.clusters}
    assert got == {"del": (1, 3), "laes": (2, 4)}
    assert all(c.orphan == "none" for c in t.clusters)


def test_orphan_close_is_not_back_projected():
    t = _t()
    B.feed(t, "del_fin", 7)
    t.finish()
    (cl,) = t.clusters
    assert cl.orphan == "close"
    assert cl.start_sign is None       # no invented start
    assert cl.end_sign == 7


def test_orphan_open_recorded_at_document_end():
    t = _t()
    B.feed(t, "del_in", 3)
    t.finish()
    (cl,) = t.clusters
    assert cl.orphan == "open" and cl.end_sign is None


def test_range_continues_when_next_line_opens_with_a_close():
    """40% of unclosed line-final breaks really do continue; those must survive."""
    t = _t()
    B.feed(t, "del_in", 3)
    t.start_line(2, continues=frozenset({"del"}))
    B.feed(t, "del_fin", 11)
    t.finish()
    (cl,) = t.clusters
    assert cl.crossesline and cl.start_line == 1 and cl.end_line == 2
    assert cl.orphan == "none"
    assert t.stats["del:continued_across_line"] == 1


def test_range_retired_when_next_line_does_not_continue_it():
    """The other 60%: the open meant 'rest of line broken' and must not drag forward."""
    t = _t()
    B.feed(t, "del_in", 3)
    t.start_line(2)                      # no continuation hint
    B.feed(t, "del_in", 7)               # a fresh range, not a reopen
    B.feed(t, "del_fin", 9)
    t.finish()
    retired = [c for c in t.clusters if c.orphan == "open"]
    paired = [c for c in t.clusters if c.orphan == "none"]
    assert len(retired) == 1 and retired[0].start_sign == 3
    assert len(paired) == 1 and paired[0].start_sign == 7
    assert t.stats["del:retired_at_line_end"] == 1
    assert "del:reopened_while_open" not in t.stats


def test_same_family_reopen_is_flagged_not_nested():
    t = _t()
    B.feed(t, "del_in", 1)
    B.feed(t, "del_in", 2)
    B.feed(t, "del_fin", 3)
    t.finish()
    assert t.stats["del:reopened_while_open"] == 1
    assert any(c.nested for c in t.clusters)


def test_active_families_for_induced_flags():
    t = _t()
    B.feed(t, "del_in", 1)
    B.feed(t, "laes_in", 1)
    assert t.active() == frozenset({"del", "laes"})
    B.feed(t, "del_fin", 2)
    assert t.active() == frozenset({"laes"})


def test_markers_are_conserved_under_fuzz():
    """No marker may ever be dropped, whatever order they arrive in.

    This is the invariant that caught the reopen bug: displacing an open cluster
    without retiring it lost a marker that was present in the source.
    """
    import random

    random.seed(5)
    tags = list(B.OPEN) + list(B.CLOSE)
    for _ in range(2000):
        seq = [random.choice(tags) for _ in range(random.randint(1, 12))]
        t = B.Tracker()
        t.start_line(1)
        line = 1
        for i, tag in enumerate(seq):
            if random.random() < 0.15:
                line += 1
                hint = frozenset({"del"}) if random.random() < 0.4 else frozenset()
                t.start_line(line, hint)
            B.feed(t, tag, i)
        t.finish()
        assert sum(1 for c in t.clusters if c.start_sign is not None) == sum(
            1 for x in seq if x in B.OPEN
        )
        assert sum(1 for c in t.clusters if c.end_sign is not None) == sum(
            1 for x in seq if x in B.CLOSE
        )
