# Plan: cut what the dataset costs a consumer

**Issue:** (not yet filed)
**Research prerequisite:** `docs/research-distribution-size.md`

The measured problem: a consumer who wants one dataset version downloads ~4.1 GB to get
something that ships in 125 MB. Compile and live cost (~350–470 MB cache, ~5 GB peak for
`loadAll()`) are properties of a 3.4M-slot corpus and are already mitigated by loading a
feature subset. The download multiplier is the only accidental cost.

This plan is five independently landable steps. Each is useful alone; none requires the
next.

## 1. What must not break

Three existing guarantees constrain the order of work.

**Published versions are immutable.** `.github/workflows/build-docid-raw-021.yml` records
the tree hash of every published release directory before it builds and re-checks all four
before pushing. `programs/publish_dataset.sh` and the release stamp assume the same. Steps
2 and 3 below deliberately change this policy; they must change the guards to match, not
work around them.

**A release is certified by comparison with its predecessor.**
`programs/check_docid_raw_release.py` proves only `docid_raw` changed by diffing 0.2.1
against 0.2.0, feature file by feature file. **0.2.0 must still be present when 0.2.1 is
certified.** This is the hard sequencing constraint in this plan.

**The stamp is bound to bytes.** `tlhdig/stamp.py` digests `p.read_bytes()` for every
`.tf` file across the main dataset and the provenance module. Any step that changes what
ships changes the digest and requires re-certification, not a hand-edited manifest.

## 2. Step A — document the shallow clone

No repository change. `README.md` and `docs/RELEASE.md` gain the one line that saves a
consumer 2.4 GB today:

```bash
git clone --depth 1 https://github.com/alexsosn/TLHdig-TF
```

Zero risk, zero coupling to the rest of this plan. Land it first and independently.

## 3. Step B — publish 0.2.1, then retire the older versions

**Order matters and is not negotiable:** 0.2.1 is certified against 0.2.0, so 0.2.0 is
deleted in a *separate, later* commit than the one that publishes 0.2.1.

1. Land `tf/0.2.1` + `tf-provenance/0.2.1` under the current release gates (PR #11).
2. In a follow-up commit, remove `tf/0.1.0`, `tf-provenance/0.1.0`, `tf/0.2.0`,
   `tf-provenance/0.2.0`.

Effect on a fresh checkout: −888 MB, leaving one version rather than three.

This does **not** shrink `.git`; the blobs stay in history. Reclaiming those 2.4 GB needs
a history rewrite, which would break every existing clone, fork and open PR. Out of scope
here — Step D exists so that it never becomes necessary.

### What Step B forces to change

- The immutable-tree guard in the build workflow must stop naming retired directories.
- `check_docid_raw_release.py` compares against a sibling directory in the working tree.
  Once only one version ships, a future "only feature X changed" certification has no
  in-tree baseline. It must fetch the predecessor from a git tag or a release asset. This
  is the real cost of Step B and should be designed before the deletion lands, not after.
- `docs/RELEASE.md` records what "published" means. Retiring versions is a policy change
  to that document, not a cleanup.

### Not a concern: losing the repository path

Whether dropping `tf/0.2.0` as a citable repository path is acceptable was raised and
**answered: yes**. The conversion is a buggy pre-alpha and versions may be discarded as
needed. Git tags and (after Step D) release assets keep the bytes regardless.

The constraint that survives is the build-order one above, which is about certification
mechanics, not archival policy.

## 4. Step C — decide whether a point release ships a whole copy

0.2.1 changes three `docid_raw` values, and ships 447 MB to do it. With Step B in place
the tree holds one version, so this is no longer a growth problem — but it remains true
that a three-value correction costs a full re-publication.

This is a question to answer, not a change to make: is a `docid_raw`-class fix a new
version at all, or an amendment to the current one? The immutability policy currently
answers "new version" and the certification machinery is built around that answer.
Changing it touches `release_policy.POLICY`. Defer until Steps A, B and D have landed.

## 5. Step D — distribute the dataset as a release asset

The order-of-magnitude win, and the fix that makes the history question moot.

**The Text-Fabric app already exists.** `app/config.yaml` carries `apiVersion: 3`, a full
`provenanceSpec` and the display configuration, and its own first line states that it is
what makes `use("alexsosn/TLHdig-TF")` and the TF browser work.
`wiki/independent-code-architecture-review-2026-08-30.md` records "no TF app" as a
usability defect, but that review predates the file by one day and is stale on this point.

Verified against the installed text-fabric 13.1.0: `advanced/repo.py` `downloadRelease()`
downloads a release **asset** when one exists, and otherwise falls back to
`downloadDir(commit, exclude=r"\.tfx")`, which walks only the `relative` subdirectory for
the requested version. Neither path fetches `.git` or `corpus/`. `advanced/zipdata.py`
(`tf-zip`) is the packaging side: each version directory becomes its own zip named
`relative-version.zip`, with `.tf` caches excluded.

So what is missing is not the app. It is:

1. **The version pin is stale.** `app/config.yaml` has `provenanceSpec.version: "0.1.0"`
   while the shipped dataset is 0.2.1, so `use("alexsosn/TLHdig-TF")` silently serves the
   first release. One-line fix, and the highest value-per-character change in this plan.
   It should be checked by a gate — `check_app.py` already validates the config against
   the dataset and is the natural home for it.
2. **No release assets exist**, so consumers take the per-file API fallback rather than a
   125 MB zip. Produce them with `tf-zip` and attach `tf/<version>` and
   `tf-provenance/<version>` to the **GitHub release**. Zenodo was considered and
   rejected: hosting our own output there would mint this conversion a DOI it does not
   have and has not asked for, and GitHub assets are what `use()` reads natively.
3. Once assets are authoritative, the repository need not carry any built dataset, and
   `check_docid_raw_release.py` gets its predecessor baseline from the previous asset —
   which resolves the gap Step B opens.

Consumer download after Step D: **125 MB for one version**, against ~4.1 GB today.

## 6. Step E — stop committing the upstream corpus; fetch it from Zenodo

`corpus/TLHdig-0.3/` is 380 MB and 24,135 tracked files. It is not our data: it is the
TLHdig Beta 0.3 archive, already cited in `CITATION.cff` and already published at
`doi:10.5281/zenodo.20328284`. Fetching it instead of committing it mints nothing — that
DOI is the upstream authors', and we cite it either way.

Everything needed is already in place:

- `programs/corpus.sha256` — 24,142 file hashes, so per-file identity is already pinned;
- `corpus/TLHdig-0.3/ATTRIBUTION.md` — records the archive exactly:
  `TLHbasisONLINE25_1_ZENODO_Beta_03.zip`, 74,449,198 bytes, MD5
  `f9acbc8db3111cc7dd88d82f7819a912`;
- `programs/tlhdig/signref_inputs.py` — an existing locked-fetch-with-hash-verification
  pattern for external inputs, directly reusable.

Effect: **−380 MB** from every checkout, and the repository becomes the converter rather
than a second copy of someone else's corpus.

The cost is real and should be weighed in a research pass first:

- the build gains a network dependency on Zenodo, where today it has none;
- `check_corpus_identity` becomes a gate over fetched rather than committed bytes;
- CI downloads 74 MB per run unless cached.

This is the same trade the signref lock already accepts for external sign lists, so there
is precedent — but it moves the corpus from "guaranteed present" to "verified on
arrival", which is a larger step than it looks. Note also
`signref_inputs.prepare()`'s current inability to recover from a corrupt cache (filed
separately); that failure mode would apply here too, over 380 MB instead of 30 KB.

## 7. Sequence

```text
A  document --depth 1                      independent, land now
D1 fix the stale version pin               one line, add a gate to check_app.py
B1 publish 0.2.1                           PR #11, unchanged
D2 release assets via tf-zip               4.1 GB -> 125 MB for a consumer
B2 retire 0.1.0 and 0.2.0                  -888 MB, after D2
E  corpus from Zenodo                      -380 MB, needs a research pass first
C  revisit point-release policy            last
```

D1 is separable from the rest of D and should not wait for it: `use()` currently serves
0.1.0 to everyone, and the fix is one line.

D2 before B2 remains right — it gives B2 its certification baseline back as a release
asset, so the gap never opens.

E is the largest single reduction (−380 MB) and the only step that changes what the build
depends on. It is sequenced last among the reductions for that reason, not because it is
least valuable.

## 8. Open decisions

1. Does this work get its own issue, or fold into #25's backlog orchestration? (The
   `signref_inputs.prepare()` cache-recovery defect found while certifying 0.2.1 is a
   **separate** issue from this plan; both are unfiled.)
2. Step E's trade: is a Zenodo network dependency at build time acceptable in exchange for
   −380 MB and a repository that stops duplicating upstream? Needs
   `docs/research-corpus-acquisition.md` before it is answered.

Resolved:

- *Losing `tf/0.2.0` as a repository path* — acceptable; pre-alpha, versions are
  discardable.
- *Where release assets live* — GitHub. Zenodo rejected for our own output; it would mint
  a DOI this conversion has not asked for.
- *Whether `srcxml` keeps shipping* — retained. It is a 28 MB TF feature in the optional
  provenance module, not the upstream corpus, and it already costs nothing to a consumer
  who does not load that module. The 380 MB question was `corpus/`, now Step E.
