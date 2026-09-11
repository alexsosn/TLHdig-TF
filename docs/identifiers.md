# Identifiers and navigation

TLHdig-TF preserves several kinds of identity that answer different questions. They should not be collapsed into one universal identifier.

## `docid`

`docid` is the normalized source-derived document identifier used by the current section configuration. It is useful for human-readable navigation, but it is **not globally unique** in the current corpus. The maintained duplicate census is in [`../KNOWN-ISSUES.md`](../KNOWN-ISSUES.md).

For duplicate groups, `docgroup` and `edition` relations preserve the relationship between separate document records instead of merging them into one node.

## Source-record identity

`src_file` identifies the source XML record within the pinned current source snapshot. When a workflow must distinguish two current document records that share `docid`, retain `src_file` as well.

`src_file` is a source-snapshot identity, not a promise of a permanent citation key across future upstream reorganizations or pre-1.0 schema changes.

## Section addresses

The configured section levels are document / column / line. Text-Fabric can therefore resolve addresses of the form:

```python
line = T.nodeFromSection(("KUB 21.8", "Vs. II", "1′"))
```

Two limitations matter:

- some current line nodes have no usable source line number and therefore no ordinary complete section address;
- a complete-looking `(docid, collabel, lnno)` tuple can still be ambiguous when `docid` belongs to more than one document record.

The current known populations are tracked in [`../KNOWN-ISSUES.md`](../KNOWN-ISSUES.md). Issue #16 owns a future unambiguous record/address design; this manual does not pre-document that solution.

## TF node numbers

Raw Text-Fabric node numbers are convenient within one loaded artifact. Do not publish them as persistent scholarly identifiers: regeneration can change technical node numbering.

## Upstream links

The corpus app provides a guarded route back to TLHdig where a source identity can be mapped safely. Ambiguous/unresolved records should fail closed rather than silently link to a different upstream record.

For reproducible analysis, record the repository/TF version and use scholarly/source identifiers in exported results whenever possible.
