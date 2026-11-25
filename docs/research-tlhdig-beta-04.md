# TLHdig Beta 0.4 source migration research (#174)

## Measured from the supplied upstream ZIP

Archive `TLHbasisONLINE25_1_ZENODO_Beta_04.zip`: MD5 `a31a1ac9808ac77432466a910ed85969`; SHA-256 `3ec8ca10fde9d73106310f346b1790bf11ce538bcf855721cd75fa92b2d0f798`. ZIP CRC check passes. Root `TLHbasisONLINE25_1_ZENODO_Beta_04/`; separate `__MACOSX/` entries are not corpus data. No duplicate NFC paths, symlinks, path traversal or ZIP encryption found. The existing corpus identity policy excludes filesystem noise.

| Metric | Beta 0.3 pinned | Beta 0.4 measured |
|---|---:|---:|
| Source members (excluding local noise) | 24,135 | 24,324 |
| .xml files | 23,937 | 24,131 |
| Non-XML | 198 | 193 |
| Raw strict XML parse success | not remeasured | 24,108 |
| Raw strict XML parse failure | not remeasured | 23 |

347,726,764 bytes of substantive members; 547 .DS_Store files under the corpus root excluded. The published 24,318 claim is not the actual count of .xml files in the supplied archive. Preserve non-XML substantive members, including the extensionless XML-like KUB 31.116 file, CSS and other formats. Do not normalize source bytes. Both lxml (no network, no entity expansion) and independent namespace-aware Expat parsing identified the same 23 bad paths.

## Existing exceptions

Compared all 53 entries of the current excluded.txt against new archive paths: 43 now parse strictly at their old paths; 2 still fail there (CTH 628_XML_HFR/KBo 47.71.xml has invalid AO:-LineNrExpl QName; CTH 813_XML_TLH/KUB 37.25.xml still starts HBEGIN:oc_encryption_module:OC_DEFAULT_M). Eight old paths are absent, of which six have unique basename candidates (not proven identity):
- CTH 537_XML_HDivT/KUB 4.53.xml -> CTH 999_XML_HDivT/KUB 4.53.xml
- CTH 582_XML_TLH/{KBo 46.126,KUB 52.46,VSNF 12.150}.xml -> CTH 582_XML_HDivT/ same filenames
- CTH 670_XML_HFR/CTH 670-aus-CTH 832/KBo 52.74.xml -> CTH 670_XML_HFR/CTH 670-4101-4125/KBo 52.74.xml
- CTH 670_XML_HFR/CTH 670-aus-CTH 832/KBo 66.131.xml -> CTH 670_XML_HFR/CTH 670-mit-Frage/KBo 66.131.xml
- CTH 612_XML_TLH/KUB 10.7.xml and CTH 776_XML_TLH/KBo 35.183.xml have no same-basename match.

Strict parse is not a TF conversion test and does not establish that source repairs or omissions can be dropped without philological checks. The old repair manifest lists 173 file entries, including two also in excluded.txt. Full old/new hash diff, repair-specific audit, licensing and loaded TF validation remain pending. Archive record must explicitly permit redistribution before committing corpus bytes. The new archive contains 418,154 lb and 1,674,757 w elements among strictly parseable files; these are raw tags, not equivalent to generated TF node counts.

## Staged migration plan

1. Compare the new full member SHA-256 manifest to the old one, with separate added/removed/changed/unchanged and exact-byte rename candidates; retain original bytes.
2. Audit each old repair and exclusion against the new source, inspect source-specific tests and semantic/coordinate ledgers. Test each changed behavior before changing conversion code.
3. Reuse corpusid, build and validate_current; update source version and DOI only alongside the new verified source and TF artifacts. Resolve cache/version decision deliberately; keep one active artifact on main.
4. Run full validation, adversarial source-to-graph review, cold acquisition and browser smoke. Refresh published release only after integration. No claim that new corpus is usable until these pass.

Current environment can inspect supplied ZIP but cannot git clone or download from Zenodo directly (DNS/network). Connector can read and commit text files but not transfer the local binary tree. An import through a hosted GitHub runner is a possible bounded workaround, contingent on repository permissions and explicit archive licence verification; otherwise use a local git checkout.
