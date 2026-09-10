# Adversarial review: release-v6 bytecode and frozen-plan boundary

Second logically independent review of #81 after the previous ignored-file/YAML/executable-input fixes.

## Blocking finding: ignored bytecode is still an executable bypass

`tlhdig.protected_tree._generated_python_cache()` currently treats every ignored
`__pycache__/*.pyc` / `*.pyo` as harmless generated output. The predicate checks only
the path shape; it does **not** prove that the bytecode was generated from the tracked
protected source.

That reopens the exact trust-boundary class the ignored-untracked fix was intended to
close. A timestamp-valid `.pyc` can contain a different code object while carrying the
mtime/size header expected for the tracked `.py`. CPython will execute that cache in
preference to compiling the tracked source, while the current protected-tree identity
ignores the cache and continues to describe only committed HEAD.

The review reproduced this mechanism under Python 3.13 with a tracked source containing
`VALUE = 1` and a forged cache containing `VALUE = 9` with the tracked source's timestamp
and size. Import returned `VALUE == 9`.

### Corrected contract

Ignored bytecode may be exempted only when it is demonstrably equivalent to a fresh
compilation of its corresponding **tracked protected source** under the current
interpreter/optimization level. A malformed, orphaned, excluded-source, wrong-version,
or semantically different cache must make the protected checkout dirty/fail closed.

The implementation should remain local and conservative:

- accept only ordinary `.pyc` cache paths that `importlib.util.source_from_cache()` maps
  to a protected tracked `.py` source;
- decode the cached code object fail-closed;
- compile the current source with the cache's optimization level and exact source path;
- exempt the cache only when the cached and freshly compiled code objects serialize
  identically;
- do not broadly exempt obsolete `.pyo` or arbitrary files merely because they live
  below `__pycache__`.

A tests-only RED must first demonstrate that a forged importable cache is currently
accepted by `protected_tree.identity()` even though importing the module executes the
forged value. The existing positive cache-preservation control should then be tightened
to use a real interpreter-generated `.pyc`, not an arbitrary placeholder.

Because this changes `programs/**` and its tests, the release-v6 protected digest changes;
full ordinary CI and canonical certification must be rerun after GREEN.

## Frozen-plan corrections

The committed plan also contains two stale statements from before the prior adversarial
round. The final contract is:

- `programs/shard.txt` is **protected**, because the integration shard is executable test
  input; it is not an allowed development-evidence exclusion.
- temporary release workflows are protected/retriggered for both `.yml` **and** `.yaml`.
- the top-level `programs/research_*.py` exclusion is narrow and currently has the
  explicit protected exception `research_weblink_ids.py`; future protected code must not
  acquire an untracked dependency on another excluded research script.

This review artifact supersedes the contradictory `shard.txt` / `.yml`-only wording in
`docs/plan-release-certification-freshness.md`; that plan text should be cleaned before
final merge, but production behavior is governed by the stricter reviewed contract and
tests.

Any blocking finding after the bytecode fix restarts RED -> GREEN -> full gates -> fresh
exact-head review.
