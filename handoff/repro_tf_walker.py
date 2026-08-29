"""Minimal reproduction: TF 13.1.0 crashes while deleting unlinked nodes that have edges.

    pip install text-fabric==13.1.0
    python repro_tf_walker.py

Expected: the walk completes and the two unlinked `meta` nodes are removed.
Actual:   TypeError: argument of type 'int' is not iterable
          at tf/convert/walker.py:1425

Two `meta` nodes are needed, not one. The faulty loop sits inside
`if node in fData:` and iterates the *remaining* entries of the same edge feature, so
with a single node the dict is empty by then and the body never runs.
"""
import tempfile

from tf.convert.walker import CV
from tf.fabric import Fabric


def director(cv):
    word = cv.node("word")
    s = cv.slot()
    cv.feature(s, letter="a")

    # Nodes with no slots of their own that carry an edge. Anything outside the text
    # stream looks like this: a lexeme, an annotation, a bibliographic record.
    for i in range(2):
        meta = cv.node("meta")
        cv.feature(meta, kind=f"note{i}")
        cv.edge(meta, word, refers=None)
        cv.terminate(meta)

    cv.terminate(word)


TF = Fabric(locations=tempfile.mkdtemp(), silent="deep")
cv = CV(TF, silent="deep")
good = cv.walk(
    director,
    "sign",
    otext={
        "fmt:text-orig-full": "{letter}",
        "sectionTypes": "word",
        "sectionFeatures": "letter",
    },
    generic={"name": "repro"},
    intFeatures=set(),
    featureMeta={
        "letter": {"description": "x"},
        "kind": {"description": "x"},
        "refers": {"description": "x"},
    },
    warn=False,
)
print("walk returned:", good)
