"""The AOxml element declaration table.

Contract B promises every editorial fact becomes queryable rather than surviving as an
opaque string, and nothing checked it -- so `AO:Sumgram` and `AO:ParagrNr` passed into
`srcxml` with their meaning invisible and no gate noticed. Declaring a destination for
every element makes "nobody thought about this tag" a failure.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tlhdig import signs, tags


def test_an_unknown_element_is_reported():
    assert tags.undeclared(["w", "lb", "AO:NewThing"]) == ["AO:NewThing"]


def test_declared_elements_pass():
    assert tags.undeclared(["w", "lb", "del_in", "ParagrNr"]) == []


def test_every_destination_is_a_known_kind():
    unknown = {k for k in tags.DESTINATION.values() if k not in tags.KINDS}
    assert not unknown, f"undefined destination kinds: {unknown}"


def test_every_wrapper_the_tokeniser_knows_is_declared():
    """The two tables must not drift: a wrapper signs.py handles but tags.py does not
    declare would read as unmodelled when it is in fact modelled."""
    for wrapper in signs.WRAPPERS:
        # the tokeniser keys on the tag as written (`AO:Sumgram`), the inventory on the
        # bare local name, because that is what the source census produces
        bare = wrapper.split(":")[-1]
        assert tags.DESTINATION.get(bare) == "wrapper", wrapper


def test_every_valued_annotation_is_declared():
    for name in signs.VALUED:
        # `surpl` and `surplus` are the same annotation under two spellings
        if name == "surplus":
            continue
        assert tags.DESTINATION.get(name) == "annotation", name


def test_raw_is_a_deliberate_choice_not_a_default():
    """`raw` must be spelled out per element, so adding a tag cannot silently inherit it."""
    assert "ParagrNr" in tags.DESTINATION
    assert tags.DESTINATION["ParagrNr"] == "raw"
    assert tags.undeclared(["SomethingNew"]) == ["SomethingNew"]
