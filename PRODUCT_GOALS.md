# Product goals — TLHdig-TF

## Users and purpose

Hittitologists and comparative Anatolian linguists should be able to analyze Hittite cuneiform texts at corpus scale, including morphological alternatives, editorial interventions, damaged readings, witnesses and cautiously aligned signs. The original TLHdig remains the reference interface for reading individual texts.

## Representative research journeys

1. Find a text by its attested document identity and navigate its physical lines and editorial sections.
2. Search for a lemma, morphological analysis or word form without collapsing mutually alternative analyses into a false single reading.
3. Locate examples of damage, restoration, addition, quotation or textual variants with the original editorial marker and source identity.
4. Inspect aligned Unicode cuneiform signs, identify the alignment mechanism and exclude uncertain or unattested mappings.
5. Reproduce a corpus-wide search in native TF with explicit exclusions and understandable resource requirements.

## Minimum usable release

A documented, independently loadable current native TF artifact and browser/CLI path lets a new researcher run several source-checked searches. Source omissions, crossing-tag repairs, incomplete sign alignment and non-unique document identifiers are openly reported; they must not be hidden by aggregate coverage percentages. A real end-user browser smoke must check navigation, rendering and query results against the distributed artifact.

## Boundaries and current priority

Use source XML and existing native TF semantics, not a custom sign database or speculative universal cuneiform alignment system. Preserve the KBo 41.49+ source-data-loss fix under regression tests and make the current committed TF artifact reliably browseable (issues #45/#47). Treat philological ambiguities as explicit data limitations rather than silent guesses.

## Autonomous-development decision rules

- Select work by the researcher journeys above, not issue count or the ease of adding tests. Prefer finishing active PRs and releases over opening new tickets.
- Before introducing a new adapter, workflow, registry, protocol, or validation layer, demonstrate that an existing mechanism cannot meet a concrete acceptance need.
- Preserve source fidelity, access controls, security, and applicable upstream rights. Do not invent inferred text or silently weaken correctness gates.
- Batch repetitive data changes and reuse parameterized tests. Keep independent adversarial review proportional to risk, and validate the actual researcher path.
- If two successive cycles do not advance a journey or remove an observed blocker, reconsider the approach. Stop when the scoped deliverable works instead of generating optional infrastructure work.
