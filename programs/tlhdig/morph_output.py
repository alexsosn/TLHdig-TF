"""#150: loaded TF morphology output parity against reviewed source attributes.

The RED gate intentionally calls this function before implementation.
It must not claim source authentication or independently validate the
TLHdig mrp grammar; these belong to separate source/parser checks.
"""


class MorphOutputMismatch(ValueError):
    """Source-derived morphology differs from the actually loaded TF graph."""


def assert_word_output(api, word_node: int, source_attributes) -> None:
    """Validate each written analysis and valued selection edge (RED stub)."""
    raise NotImplementedError("RED: per-analysis output audit has not been implemented")
