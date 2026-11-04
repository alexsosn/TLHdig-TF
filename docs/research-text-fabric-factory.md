# Research: text-fabric-factory reuse for TLHdig-TF

Issue: #140  
Decision scope: TLHdig 0.3 AOxml → Text-Fabric conversion  
Third-party revision inspected: `annotation/text-fabric-factory@bae4a39d298ab6a44668b37e565d799d11f9a244`  
TLHdig baseline inspected: `main@0261d2d46b3419a1f907e231a03f749d133cfb5e`

## Decision

**Use `text-fabric-factory` as implementation/reference material only.**

Do not add `text-fabric-factory` as a TLHdig-TF build dependency and do not wrap the
current AOxml semantic converter in its XML conversion framework.

The useful shared conversion boundary already exists one layer lower:
TLHdig-TF directly uses Text-Fabric's `tf.convert.walker.CV`. TFF uses the same
walker. Replacing TLHdig's source/semantic layer with TFF therefore would not buy a
more standard TF output path; it would replace corpus-specific interpretation and
provenance code while retaining the same underlying TF writer.

TFF remains useful as reference material for app scaffolding, conversion metadata,
XML inventory UX, and examples of organizing a TF conversion. Those ideas can be
adopted independently where they improve existing TLHdig tickets. There is no
justified TFF integration/migration plan after this research.

## Baseline: invariants the current converter must preserve

The acceptance criterion is not merely “produces loadable TF”. The current repository
has explicit contracts that arose from failures observed in TLHdig 0.3.

### Byte-faithful source identity and provenance

`programs/tlhdig/source.py` deliberately scans the byte stream with Expat because
lxml exposes source lines but not exact byte offsets. Each element receives exact
`outer`/`inner` byte ranges. Reconstruction is done by slicing source bytes rather
than serializing an XML tree; serialization can change namespace spelling, entity
spelling, empty-element syntax, quoting, and whitespace.

The repair layer is also byte-oriented and SHA-pinned. Repairs are applied in memory;
source files are not rewritten. `OffsetMap` translates repaired-stream coordinates
back to immutable source coordinates. Issue #12 is strengthening this further by
separating proven byte-local repair from structural recovery.

Any replacement that starts from a reparsed tree, normalized text, or regenerated XML
without an exact original-byte coordinate map fails this contract.

### Semantic slot model

TLHdig's slot type is `sign`, not XML character or generic token. The converter maps
AOxml word content through `tlhdig.signs`, keeps word/sign structure, creates
linguistic analyses and lexeme edges, and aligns transliteration with cuneiform line
data. Empty structural objects are handled deliberately rather than by inserting a
generic character into the transcription.

### AOxml-specific graph semantics

The current director creates a corpus-specific ontology rather than mirroring XML
elements:

- containment spine: document / surface / column / line / word / sign;
- morphology: alternative `analysis` nodes, selection edges, normalized linguistic
  features, and shared lexeme nodes;
- damage/editorial markup: explicit cluster/range semantics and induced sign flags;
- writing-system markup: determinative, Sumerogram and Akkadogram features including
  long-form AO wrappers;
- apparatus: manuscript blocks, fragments, joins and related edges;
- editorial history and notes as dedicated nodes;
- provenance split into a separately loadable TF module.

`programs/check_tags.py` makes this a closed Contract-B vocabulary/placement check.
It distinguishes body from header namespaces and checks placement/cardinality, not
only element names.

### Conservation and failure semantics

The conversion ledger accounts for every source file and treats unexpected exclusions
as failures. Independent gates check source/graph structure, damage markers, source
spans, morphology, tags, cuneiform alignment, app configuration and corpus identity.
Known malformed input is version-specific evidence, not permission to make a parser
generically tolerant.

## What TFF actually provides

### Generic XML converter

TFF's own `tff/convert/xml.py` says that its generic XML converter is intended more
as an example than as a production engine and points semantic corpora toward custom
conversion.

Its default implementation in `tff/convert/xmlCustom.py` has these semantics:

- parse XML with lxml;
- recursively mirror XML elements to TF nodes using local tag names;
- copy XML attributes to features;
- condense every run of text/tail whitespace to one space;
- use Unicode characters as TF slots;
- insert a U+200B zero-width-space slot into an otherwise empty element;
- add a synthetic final slot per source file;
- optionally transform the complete XML text string before parsing.

These are reasonable generic defaults. They are incompatible defaults for TLHdig.

### TF walker

TFF delegates TF construction to `tf.convert.walker.CV`.

TLHdig already does exactly that in `programs/tlhdig/convert.py`:

```python
TF = Fabric(...)
cv = CV(TF, ...)
cv.walk(..., "sign", ...)
```

There is therefore no missing reusable walker layer to acquire from TFF.

### XML inventory/checking

TFF provides an inventory-oriented `check` task for XML elements/attributes.

TLHdig already has a stronger corpus-specific gate in `programs/check_tags.py`:
it inventories the repaired AOxml stream, separates body/header semantics, detects
namespace and placement drift, rejects undeclared constructs, and also rejects declared
but no-longer-observed header vocabulary. Generic inventory can inspire report UX but
does not replace this gate.

### App/browser generation

TFF can generate/update a TF app, documentation, CSS and configuration with custom
overrides. This is the most reusable-looking part at first glance.

TLHdig already has an app and `tlhdig.appcheck`, including tests that catch features
configured on the wrong node type and stale artifact targeting. Issue #45 owns the
remaining end-to-end app/browser regression gate.

TFF's `appTask` is coupled to converter state such as its slot mode, section model,
generated feature metadata and TFF templates. Adopting the package solely to render
templates would add a build dependency and another app model while leaving the
TLHdig-specific app contract to local tests anyway. The templates remain useful
reference material for #45 and future documentation work.

### Packaging

At the inspected revision:

- package metadata reports `text-fabric-factory 1.0.8`;
- Python requirement is `>=3.9`;
- `text-fabric` is an unbounded runtime dependency;
- the repository's latest inspected commit is 2025-12-04;
- metadata classifies the package as Beta.

TLHdig pins deterministic rebuild dependencies, currently Python 3.13.1 with
`text-fabric==13.1.0`, `lxml==5.4.0`, `pytest==8.3.4`, and `PyYAML==6.0.2`.
Adding TFF would therefore require us to pin and compatibility-test an extra framework
whose principal reusable primitive, `CV`, is already obtained from the pinned
Text-Fabric dependency.

## Real-data comparison

### KBo 12.55: lexical damage plus malformed terminal structure

`CTH 209_XML_TLH/KBo 12.55.xml` contains ordinary AOxml morphology and inline damage,
but its terminal word is malformed. The current repair/recovery work distinguishes
two proven byte-local attribute repairs from the later structural close decision.

A strict lxml-first generic conversion cannot represent that distinction. A
whole-document transform hook could rewrite the text before lxml sees it, but then TFF
still supplies no immutable-byte coordinate map or typed recovery event model. Reusing
that hook would relocate the current repair system rather than replace it.

### KUB 26.29+: mixed semantic markup and crossing wrapper

`CTH 144_XML_SVH/KUB 26.29+.xml` combines:

- `AO:Manuscripts` and multiple publication witnesses;
- line and colon boundaries;
- `AO:Sumgram`, `AO:Akkgram`, determinatives;
- deletion/lacuna/correction markup;
- notes embedded inside words;
- line-level cuneiform strings;
- a real crossing `AO:Akkgram` defect where the historic manifest inserted an early
  synthetic close and later deleted the delayed original close.

Issue #12 now treats those two historic patches as one structural-recovery defect so
the delayed source close remains evidence. TFF's generic tree walk cannot start until
this source has already been changed into parseable XML, and once it starts it maps the
tree rather than the evidentiary byte stream.

The default character-slot model would also split a TLHdig sign representation into
characters rather than preserve the existing sign ontology and cuneiform alignment.

### KBo 53.4+: merged-document apparatus

`CTH 342_XML_MYTH/KBo 53.4+.xml` contains merged-document metadata with nested source
document IDs and editorial history. TLHdig's header and manuscript logic consumes
specific structural paths and exposes domain relationships rather than treating every
header element as a generic node.

A generic element→node conversion could retain XML shape, but that is not semantic
equivalence to the current graph and would weaken the placement contracts that catch
known vocabulary appearing at an unsupported path.

## Compatibility matrix

| Requirement | TLHdig current path | TFF generic XML path | Compatibility |
|---|---|---|---|
| Exact immutable source byte offsets | Expat byte spans + OffsetMap | lxml tree; no original-byte span model | incompatible |
| SHA-pinned mechanical repair / reviewed recovery | repository-specific byte policy | optional whole-text transform hook | incompatible |
| Malformed-source local recovery | explicit version-bound policy (#12) | parser requires parseable XML | incompatible |
| Slot type | sign | character by default | incompatible |
| Whitespace | source/sign semantics | collapses text/tail whitespace runs | incompatible |
| AO namespace/source spelling | byte scanner preserves written names | generic walk reduces tags/attrs to local names | incompatible for provenance/contracts |
| Word/sign tokenization | AOxml-specific `signs.py` | generic characters | incompatible |
| Morphological alternatives | dedicated analysis/selection/lexeme model | generic XML nodes/attributes | not supplied |
| Damage/editorial ranges | range tracker + conservation gates | generic element containment | not supplied |
| Cuneiform alignment | TLHdig line/sign model + gates | not supplied | not supplied |
| Manuscript/fragment/join graph | corpus-specific parsers/edges | generic element containment | not supplied |
| Contract-B vocabulary/placement | closed corpus-specific gate | generic inventory | weaker |
| TF serialization | direct `CV` | direct `CV` | already shared |
| App scaffolding | local app + appcheck; #45 open | generated templates/config | reference useful |
| Conversion metadata ideas | local feature metadata | conversionMethod/conversionCode conventions | reference useful |

## Options considered

### 1. Adopt TFF as the primary converter

Rejected. The generic XML semantics conflict with sign slots, whitespace handling and
source provenance before any higher-level AOxml mapping is considered. Making it
equivalent would require replacing its director with the TLHdig director and restoring
our byte/recovery layer, which collapses into option 3.

### 2. Adopt only generic walker/inventory/app helpers as a dependency

Rejected as a package boundary.

The walker is already used directly from Text-Fabric. The inventory is weaker than the
current Contract-B gate. App generation is useful but coupled enough to TFF conversion
state that importing the framework only for templates provides little leverage and
creates a new dependency/pinning surface.

### 3. Wrap the existing TLHdig semantic parser in TFF infrastructure

Rejected. TFF explicitly permits a custom conversion task, so this is technically
possible, but it would mainly add TFF's lifecycle/version/layout conventions around a
director that still has to remain TLHdig-owned. It does not solve provenance,
malformed-source recovery, semantic mapping or conservation. The wrapper would become
another orchestration layer to test.

### 4. Replace selected generic XML plumbing

No current production replacement is justified. The source scanner, repair/recovery,
tag inventory and director are all specialized precisely where TFF is generic.

Individual ideas may still be copied or reimplemented locally when they fit an existing
ticket:

- generated app/documentation templates can inform #45;
- the `conversionMethod` / `conversionCode` metadata convention is a useful reference
  if provenance-of-features becomes a product requirement;
- TFF's organization of check/convert/load/app tasks is a useful UX reference;
- its XML inventory reports can inform presentation of Contract-B diagnostics.

These are ideas, not a reason to import TFF.

### 5. Keep current architecture and use TFF as reference material

Selected.

This preserves the existing direct dependency on Text-Fabric and keeps the boundary
clear:

```text
immutable AOxml bytes
    ↓
TLHdig repair/recovery + byte coordinates
    ↓
TLHdig semantic interpretation
    ↓
tf.convert.walker.CV
    ↓
TF dataset + local app
```

TFF is consulted outside that runtime path.

## Dependency, performance and maintenance cost

A performance POC is not justified for the decision above. The TFF generic converter
would produce a different graph (character slots and generic element nodes), so a
runtime or memory comparison would benchmark different products. A fair benchmark
would first require reimplementing TLHdig semantics inside TFF, at which point the
dominant semantic work remains our code and the architectural question is already
settled.

The measurable dependency difference is simpler: current TLHdig pins Text-Fabric
directly; TFF itself depends on Text-Fabric without a version bound. Importing TFF would
add framework/API compatibility work without removing the direct Text-Fabric dependency
or the TLHdig-specific tests.

Maintenance also becomes less clear, because failures could originate in three layers
(TLHdig custom director → TFF orchestration → Text-Fabric walker) instead of the current
two. For a pre-alpha corpus with active repair/recovery work, that indirection has no
identified compensating capability.

## Consequences

- Do not add `text-fabric-factory` to `requirements.txt`.
- Do not migrate the AOxml converter to `tff.convert.xml`.
- Continue using the pinned `tf.convert.walker.CV` directly.
- Keep source byte scanning, repair/recovery, semantic mapping and conservation gates
  local to TLHdig-TF.
- Treat TFF app/template and metadata conventions as reference input to the existing
  app/documentation backlog rather than a dependency.
- No migration/TDD implementation ticket follows from #140. If a future proposal wants
  TFF in the runtime/build path, it must identify a concrete capability not already
  supplied by Text-Fabric or local code and prove byte-provenance plus semantic
  equivalence on the current malformed-source regressions before dependency adoption.
