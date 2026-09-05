# Research: reproducible external sign-reference validation

Issue: #22

## Current behavior before this ticket

`programs/check_signrefs.py` read whatever happened to exist under git-ignored `refs/`. If the directory was absent or empty it printed a skip message and exited 0. `signrefs.load()` also accepted arbitrary subsets. Hosted CI therefore could not distinguish a real external-reference pass from a missing-input skip, and release tooling had no machine-readable evidence that the intended witnesses were actually used.

The repository pinned neither source revisions nor hashes for these files. The historical report was therefore reproducible only by possession of the original local `refs/` directory.

## Input inventory

All six inputs can be acquired read-only without authentication. None needs to be committed or redistributed by TLHdig-TF.

| local file | canonical source | exact revision / object | locked content identity | license / redistribution | preprocessing |
|---|---|---|---|---|---|
| `osl.asl` | `oracc/osl`, `00lib/osl.asl` | commit `7749a4bd8589491b987ab3da31660ef4abca5012` | Git blob SHA-1 `28d36ef5760befefd4921a62c2acd4f53be17eab` | the file itself declares CC0 | direct copy |
| `potnia-hittite.yaml` | `AncientNLP/potnia`, `potnia/data/hittite.yaml` | commit `95691a4a6007afed0fed4084a1c263fed3249ee0` | Git blob SHA-1 `cc77838c7f89249d27d23f573425bfd784aca7e7` | Apache-2.0 (`LICENSE` in the same revision) | direct copy / local rename |
| `tffromatf-mapping.tsv` | `Nino-cunei/tfFromAtf`, `characters/mapping.tsv` | commit `382cdc234bf400993f3bff48df5ace84f73fe28d` | Git blob SHA-1 `711a1c23fbce16453500cb8ccadee7fad5fd89e5` | MIT (`LICENSE` in the repository); repository is archived | direct copy / local rename |
| `nuolenna-signlist.tsv` | `tosaja/Nuolenna`, `sign_list.txt` | commit `0ccc814c8f312417f1a0648e752fd7ef02558363` | Git blob SHA-1 `7c0ec45e976eed7e4ee66b86076e2ca3d30f6432` | README states AGPL-3.0-or-later and explicitly refers to use of the sign list | direct copy / local rename |
| `enmerkar-signlist.csv` | `eggrobin/Enmerkar`, `sign_list.csv` | commit `b20e9c0c1436fdf6e9732b79a39cf7225b3447ad` | Git blob SHA-1 `9f633bcd81921c3fdb556be4c2ea861a35480873` | README says the sign list is OGSL-derived and available under CC BY-SA 3.0 | direct copy / local rename |
| `wiktionary-hittite-module.lua` | English Wiktionary `Module:hit-translit/sign-list` | permanent revision `oldid=83078078` (2024-12-19) | revision/slot/content SHA-1 `b8437e38b05fcd16b9f94cf6a968fa12e39010a3` | Wiktionary page footer: CC BY-SA; additional terms may apply | fetch module source; local rename |

The Wiktionary loader intentionally needs the `sign-list` module, not `Module:hit-translit/data`: the former contains `export.sign_list = { ... }`, which is the structure parsed by `_wiktionary()` and `equivalents()`.

### Wiktionary hash bootstrap

MediaWiki documentation has historically described stored SHA-1 values differently, so the lock was bootstrapped from the exact revision on a clean GitHub-hosted runner rather than by assuming an encoding. An anonymous `prop=revisions` request for revision `83078078`, requesting `ids|sha1|slotsha1|content`, returned:

- revision id: `83078078`;
- revision SHA-1: `b8437e38b05fcd16b9f94cf6a968fa12e39010a3`;
- main-slot SHA-1: the same value;
- SHA-1 recomputed over the returned UTF-8 bytes: the same value;
- returned content length: 29,940 bytes.

The one-shot probe workflow used only read permission and printed metadata/hashes, never source content; it was removed immediately after the lock was populated. Production acquisition recomputes the content SHA-1 and requires both MediaWiki metadata hashes to match the returned bytes before comparing with the lock.

## Provenance and independence

The six files are not six independent scholarly opinions. `signrefs.LINEAGE` records that Enmerkar derives from OGSL and that tfFromAtf descends from a Šašková list. Reproducible acquisition must preserve this distinction; source count must not be described as independent-vote count.

Licenses differ from CC0 through copyleft. Fetching them transiently during CI and leaving `refs/` git-ignored avoids redistributing a mixed-license bundle from this repository. Generated agreement counts and diagnostics remain the shipped artifacts.

## Failure modes that need separate states

1. **Unavailable**: network error, HTTP error, or intentionally offline run before the file exists.
2. **Stale/wrong object**: downloaded bytes do not match the pinned Git object or MediaWiki revision/hash.
3. **Malformed**: bytes match acquisition expectations but the loader cannot obtain usable readings.
4. **Partial set**: some references are present and others are missing. This must never be reported as a complete pass.
5. **Policy skip**: ordinary/offline operation may deliberately decline network acquisition, but the skip must be explicit.
6. **Release skip**: not acceptable. A release/certification invocation must fail if a required reference did not run.
7. **Unpinned extra**: a newly added or stray recognized loader must not enter the vote unless it is also added to the lock with provenance and integrity data.

## Feasibility conclusion

A clean hosted runner can reproduce the check without secrets and without committing external data. Five inputs are pinned by immutable Git commit plus blob SHA. Wiktionary is pinned by permanent revision ID plus a SHA-1 independently recomputed over the content returned by that exact revision.

The acquisition layer should stay separate from the scholarly comparison layer: `programs/signrefs.lock.json` plus a fetch/verify command populates `refs/`, then the existing sign-list loaders and vote logic run only after the complete source set is verified. This keeps network and provenance failures from being confused with corpus disagreements.
