# References and citation

## Source corpus

TLHdig-TF is derived from **TLHdig 0.3 (Thesaurus Linguarum Hethaeorum digitalis)**, published by the Hethitologie-Portal Mainz team under CC-BY-4.0. The pinned source dataset used by this conversion is identified by DOI **10.5281/zenodo.20328284**. When the underlying Hittite corpus is the scholarly source being cited, cite that source dataset rather than treating this conversion as a replacement edition.

- Source DOI: <https://doi.org/10.5281/zenodo.20328284>
- Source identity used by the build: [`../programs/corpus.sha256`](../programs/corpus.sha256)
- Conversion citation metadata: [`../CITATION.cff`](../CITATION.cff)

## Text-Fabric

The current repository pins **Text-Fabric 13.1.0**. Text-Fabric supplies the graph representation, loading/query APIs, app framework and browser used by this project.

- Text-Fabric project: <https://github.com/annotation/text-fabric>
- Exact project dependency pin: [`../requirements.txt`](../requirements.txt)

## Project evidence

For claims about what the current generated artifact contains, prefer executable/current project evidence over prose copied from an older release:

- [`features/0_home.md`](features/0_home.md) for the generated feature reference;
- [`../reports/census.md`](../reports/census.md) for current node counts and basic invariants;
- [`../reports/alignment.md`](../reports/alignment.md) for cuneiform alignment coverage and methods;
- [`../reports/markers.md`](../reports/markers.md) and [`../reports/contract_a_graph.md`](../reports/contract_a_graph.md) for source-conservation checks;
- [`../KNOWN-ISSUES.md`](../KNOWN-ISSUES.md) for maintained limitations;
- [`RELEASE.md`](RELEASE.md) for the current build-validation and manifest contract.

## Citation practice

Record the TLHdig source version/DOI, the TLHdig-TF repository revision (or other immutable revision identifier), and any filtering policy that materially affects the result. For analyses depending on repaired XML, provenance spans, exclusions or cuneiform alignment, cite the corresponding report or source record as well.
