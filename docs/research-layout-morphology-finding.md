# Research finding: morphology attached to layout-only source words

Origin: issue #92 morphology-marker census.

This is a scope-separation record, not an implementation plan for #92.

Hosted diagnostic run `34414659150`, job `102676734157`, ran `programs/research_contentless_mrp.py` against the repaired production corpus using the same byte-span/sign-token boundary that the converter uses to decide whether a `<w>` has any non-empty sign token. The diagnostic does not reuse the production morphology parser.

It found exactly:

- 15 source `<w>` elements with one or more `mrpN` candidates for which `keep_empty=False` leaves no non-empty sign token;
- 15 `mrpN` candidate records on those words;
- 2 broad-prefix candidates, both beginning with `①`;
- examples spanning PTAC, TLH, BESRIT and HFR projects;
- representative raw records include `@@@@ `, `nu@@CONNn@@`, `① nu@@CONNn@@`, and `① DUG@Gefäß@{b → ACC.SG(UNM)}@28.2.1.1@`.

Current converter behavior returns from `_State.word()` before `morph.analyses(node.attrib)` when `keep_empty=False` leaves no sign-producing token. Those source morphology records therefore cannot create `analysis` nodes in TF 0.4.0.

This is distinct from #92's lexical-marker problem. Marker normalization must neither suppress nor manufacture analyses to make its source/TF counts balance. The 15 records should be researched as a separate ontology/fidelity question: whether morphology attached to a layout-only source word belongs on a layout node, on a source/provenance representation, on a zero-slot analysis surrogate, or should remain source-only with an explicit loss contract.

No production behavior is changed by this finding.
