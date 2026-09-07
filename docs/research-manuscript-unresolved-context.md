# Research: unresolved manuscript source context

Issue: #18

This follow-up audit tests the acceptance requirement that unresolved join references remain explicit and queryable rather than disappearing from the TF graph. It uses the same production-eligible source population as the converter: pinned repair manifest, strict byte/XML parsing, encrypted-file exclusion, and `body/div1` manuscript scope.

## Finding

The repaired/strict production population contains **30 unresolved manuscript join statements**. Of these:

- **22** have neither a left nor a right fragment endpoint;
- the same **22** occur in apparatus blocks with no parsed fragment entry;
- all **22** retain a manuscript label only as parser `residual_text` / raw block text;
- therefore all **22** would lose that source reference as queryable TF data if the graph stores only `join_kind`, `join_raw`, `join_reason`, and `joinDocument`.

Representative source forms are:

```xml
<AO:Manuscripts>KBo 31.5++</AO:Manuscripts>
<AO:Manuscripts>KBo 52.107a(+)</AO:Manuscripts>
<AO:Manuscripts>KBo 52.108(+)(+)</AO:Manuscripts>
```

The parser currently produces source statements such as `direct-multi / ++` or `indirect / (+)` with no endpoints, while the manuscript label (`KBo 31.5`, `KBo 52.107a`, `KBo 52.108`) survives only in `Apparatus.residual_text`.

The 22 measured labels are single normalized residual chunks associated with a single endpoint-free unresolved status statement in their block. No evidence supports converting them into ordinary `fragment` endpoints: the source does not serialize them as `TxtPubl`, `TextPubl`, `InvNr`, or a safely delimited plain entry participating in a binary boundary.

## Interpretation boundary

The source value must be preserved without inventing graph semantics. The narrow representation is therefore an optional raw-reference/context feature on the authoritative `joinstmt` node. This records the unresolved manuscript reference while keeping `left=None`, `right=None`, `join_resolved=0`, and emitting no `joined` edge.

The graph must not reinterpret these 22 status records as resolved joins, infer an external target, synthesize a fragment solely to satisfy an edge model, or treat the document id as an endpoint.

## Release consequence

The independent source-to-graph conservation checker must compare this unresolved reference exactly. A build that preserves only the marker (`++`, `(+)`, etc.) but drops the associated label fails issue #18 even if statement counts still balance.
