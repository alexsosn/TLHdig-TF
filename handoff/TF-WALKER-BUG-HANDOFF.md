# Hand-off: bug in Text-Fabric `CV._removeUnlinked`

**For:** whoever picks up reporting this upstream.
**Task:** check whether it is already reported at `annotation/text-fabric`; if not, file
an issue and submit a PR per the project's contribution rules.
**Not done yet:** no issue search has been performed, nothing has been filed, no fork or
branch exists. Start from zero.
**NB:** Make sure to check if Context Fabric implementation has the same bug. I'm not sure if original Text Fabric is even accepting the PRs these days.

---

## 1. Summary

`tf.convert.walker.CV.walk()` raises `TypeError` while removing unlinked nodes, if any
unlinked node carries an edge and at least one other node has an edge in the same edge
feature. The conversion aborts.

* **Package:** `text-fabric`
* **Version:** `13.1.0` — the current PyPI release as of 2026-08-29
* **Also on `master`:** yes, identical code at the same line numbers (checked via the
  GitHub contents API)
* **File:** `tf/convert/walker.py`, method `_removeUnlinked`, lines **1421–1426**
* **Python:** reproduced on 3.13.1, macOS. Nothing version-specific about it.

---

## 2. Reproduction

`repro_tf_walker.py` sits next to this file. It is self-contained — stdlib plus
`text-fabric` — and takes about a second.

```bash
pip install text-fabric==13.1.0
python repro_tf_walker.py
```

Observed:

```
File ".../tf/convert/walker.py", line 1425, in _removeUnlinked
    if node in toValues:
       ^^^^^^^^^^^^^^^^
TypeError: argument of type 'int' is not iterable
```

Expected: the walk completes and reports the two unlinked `meta` nodes as removed.

**Note for whoever reduces this further:** two unlinked nodes are required, not one.
The faulty loop is nested inside `if node in fData:` and iterates the *remaining*
entries of that same edge feature, so with a single node the dict is already empty when
the loop is reached and the body never executes. An earlier one-node version of this
repro did **not** trigger the bug.

---

## 3. The defect

```python
# tf/convert/walker.py, _removeUnlinked
1421                    for (f, fData) in edgeFeatures.items():
1422                        if node in fData:
1423                            del fData[node]
1424                            for (fNode, toValues) in fData:      # <-- missing .items()
1425                                if node in toValues:
1426                                    del toValues[node]
```

`edgeFeatures[f]` maps a *from-node* to a `{to-node: value}` dict. During a walk the
node references are `(nodeType, seq)` tuples.

Line 1424 iterates `fData` directly, which yields its **keys**. Because each key is a
2-tuple, the unpacking `(fNode, toValues)` silently succeeds and binds:

* `fNode` → the node **type** (a `str`)
* `toValues` → the node **sequence number** (an `int`)

Line 1425 then evaluates `node in toValues`, i.e. `tuple in int`, which raises. The
unpacking succeeding is what makes this fail confusingly far from its cause.

**Fix:** `for (fNode, toValues) in fData.items():`

### 3.1 A second, latent defect in the same block

Worth mentioning in the issue, but arguably a separate change: the inner loop is
indented **inside** `if node in fData:`. Its purpose is to strip *incoming* edges that
point at the deleted node, but it only runs when the node also happens to have an
*outgoing* edge in that same feature.

A node with only incoming edges therefore keeps dangling references to a node that no
longer exists. Correcting the `.items()` bug alone leaves this in place. The loop
probably belongs at the `for (f, fData)` level:

```python
for (f, fData) in edgeFeatures.items():
    fData.pop(node, None)
    for toValues in fData.values():
        toValues.pop(node, None)
```

I have **not** verified that this second issue produces observable breakage — it is
read from the code, not from a failing run. Please confirm before asserting it upstream,
and consider filing it separately so the clear bug is not held up by the arguable one.

---

## 4. Why it matters

Any node outside the text stream hits this: a lexeme, an annotation, a bibliographic
record, an editorial event. Such nodes have no slots of their own, so TF deletes them —
and if they carry edges, the deletion crashes.

It surfaced while converting the TLHdig Hittite corpus, where `analysis` nodes (one per
morphological reading) and `edit` nodes (one per editorial event) are both slotless and
edge-bearing. Workaround in that project: give every such node explicit slots via
`cv.node(nodeType, slots=...)` so it is never unlinked. That is a reasonable modelling
choice anyway, but it should not be *forced* by a crash.

---

## 5. What to do

1. **Search existing issues first.** `annotation/text-fabric` issues and PRs, open and
   closed. Terms worth trying: `_removeUnlinked`, `removeUnlinked`, `unlinked`,
   `walker.py`, `not iterable`, `argument of type 'int'`. Also skim `CHANGELOG` /
   release notes above 13.1.0 in case it is fixed but unreleased. If it is already
   reported, add the reproduction to that thread rather than opening a duplicate.
2. **Read the contribution rules before filing** — check for `CONTRIBUTING.md`, a PR
   template, and any issue templates in the repo.
3. **Issue:** version, platform, the repro script, the traceback, the two-node
   requirement, and the analysis in §3. Keep §3.1 clearly marked as unverified.
4. **PR:** the one-line `.items()` fix, plus a regression test. There is a test suite
   under `test/` — follow its existing layout and naming rather than inventing a new
   one. Match the project's commit-message style.
5. Decide whether to include §3.1 in the same PR. My inclination is a separate issue:
   the `.items()` fix is unambiguous and should land quickly.

---

## 6. Provenance

Found on 2026-08-29 while building the TLHdig → Text-Fabric converter in this
repository. The workaround is in `programs/tlhdig/convert.py`, which notes the crash at
the point where `analysis` and `edit` nodes are given explicit slots.

Nothing here has been communicated to the maintainers. The reproduction is verified;
the §3.1 analysis is not.
