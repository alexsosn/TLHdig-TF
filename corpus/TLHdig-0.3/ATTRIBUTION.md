# Source corpus — attribution and licence

The contents of this directory are **not** covered by the MIT licence at the root of
this repository. They are a redistribution of a third-party dataset under CC-BY-4.0.

## Dataset

> Müller, Gerfrid; Prechel, Doris; Rieken, Elisabeth; Schwemer, Daniel.
> *Thesaurus Linguarum Hethaeorum digitalis (TLHdig) Beta Version 0.3.* Zenodo, 2026.
> <https://doi.org/10.5281/zenodo.20328284>

| | |
|---|---|
| Version | Beta 0.3 |
| DOI (this version) | `10.5281/zenodo.20328284` |
| Concept DOI (all versions) | `10.5281/zenodo.15459133` |
| Published | 2026-05-21 |
| Original archive | `TLHbasisONLINE25_1_ZENODO_Beta_03.zip` (74,449,198 bytes, MD5 `f9acbc8db3111cc7dd88d82f7819a912`) |
| Licence | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |
| Project | Hethitologie-Portal Mainz — <https://www.hethport.uni-wuerzburg.de/TLHdig/> |

TLHdig is a living repository maintained by the Hittitological community. It is not a
critical edition; the depositors state that the epigraphical and philological quality of
the data is uneven and under continuous development.

The transliterations were not created by the TLHdig team but reflect a century of
collective Hittitological scholarship. See the Contributors section on the TLHdig site.

## Modifications

Under CC-BY-4.0 §3(a)(1)(B), changes must be indicated. As redistributed here the corpus
is **unmodified** except that:

* `.DS_Store` files (macOS Finder artefacts, absent from the Zenodo archive) are not
  committed — see `.gitignore` at the repository root.

No XML file has been altered. Repairs to the 224 malformed files described in
[docs/TF-CONVERSION-RESEARCH.md](../../docs/TF-CONVERSION-RESEARCH.md) §9.1 are applied
by the conversion pipeline into a separate output directory and are never written back
over these sources.

## Note on one file

`CTH 813_XML_TLH/KUB 37.25.xml` is shipped in the upstream Beta 0.3 archive as an
ownCloud/Nextcloud **encrypted blob**, not XML. It is preserved here exactly as released.
See the research document §9.1 for the report that should go upstream.
