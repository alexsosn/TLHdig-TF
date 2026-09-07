# Plan: preserve unresolved manuscript references

Issue: #18

Research: `docs/research-manuscript-unresolved-context.md`

This is a narrow extension of `docs/plan-manuscript-joins.md`. Production code changes start only after this plan and a hosted RED.

## Model

Extend the pure `Statement` record with an optional normalized source reference:

```python
context: str = ""
```

`context` is populated only when source text associated with an unresolved statement would otherwise be left outside all parsed fragment occurrences. For the measured targetless status family, it is the single normalized residual manuscript label such as `KBo 31.5` from `KBo 31.5++`.

Do not populate it for resolved binary statements or use it as an endpoint identity.

Emit the value on the authoritative `joinstmt` as optional feature:

```text
join_context
```

Semantics:

- raw operator spelling stays in `join_raw`;
- unresolved source reference/context stays in `join_context`;
- `join_resolved=0` remains unchanged;
- no `joinLeft`, `joinRight`, or `joined` edge is invented solely because context exists;
- `joinDocument` remains the ownership/provenance edge.

## Deterministic association rule

After block tokenization, if an unresolved statement has no left or right endpoint and the block has exactly one normalized residual text chunk representing the targetless status label, attach that chunk as `Statement.context`. The measured production family contains 22 such records.

If future input has multiple residual chunks or ambiguous association, preserve the statement but leave `context` empty rather than guessing. Such a new corpus shape must be surfaced by the conservation/research gates before a stronger rule is introduced.

## RED gates

Before implementation:

1. parser fixture `KBo 31.5++` must require `statement.context == "KBo 31.5"` while both endpoints remain `None`;
2. graph fixture must require `join_context="KBo 31.5"` on the `joinstmt` and no fragment-to-fragment projection;
3. independent conservation comparison must treat differing/missing context as a statement-ledger mismatch.

## GREEN / release gates

After implementation:

- full parser/graph suites remain GREEN;
- production strict audit must still find 30 unresolved statements and exactly 22 endpoint-free context-bearing statements;
- `programs/check_manuscript_joins.py` must compare `join_context` exactly source-to-graph;
- final `tf/0.3.0` build, app/schema check, census, and `release-v3` certification must pass;
- a logically independent adversarial PR review must explicitly attack context loss and accidental promotion of targetless status records to edges.
