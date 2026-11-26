"""Beta 0.4 exposed a mismatch between repair and the production XML parser."""
import sys
from pathlib import Path

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tlhdig import repair


@pytest.mark.parametrize("data", [
    b'<r xmlns:AO="urn:ao"><AO:-LineNrExpl>obv.</AO:-LineNrExpl></r>',
    b'<r xmlns:AO="urn:ao"><AO:--superscr>?</AO:--superscr></r>',
    b'<r><AO:LineNrExpl>obv.</AO:LineNrExpl></r>',
])
def test_namespace_invalid_is_not_parseable(data):
    with pytest.raises(etree.XMLSyntaxError):
        etree.fromstring(data)
    assert not repair.parses(data)


def test_valid_namespace_and_literal_text_unchanged():
    data = b'<r xmlns:AO="urn:ao"><AO:LineNrExpl>obv.</AO:LineNrExpl></r>'
    assert repair.parses(data)
    assert repair.propose_iteratively(data) == []
