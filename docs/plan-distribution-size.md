# Plan: cut what the dataset costs a consumer

**Issue:** #39
**Research prerequisite:** `docs/research-distribution-size.md`

The measured problem: a consumer who wants one dataset version downloads **~1.5 GB** to
get something that ships in 125 MB — about 12×. (An earlier draft said 4.1 GB. That was
`du` on a working copy holding 1.52 GiB of loose objects from local builds; GitHub reports
the published repository as 1.51 GB, and `git count-objects` agrees.)

Live cost — ~5 GB peak for `loadAll()` — is a property of a 3.4M-slot corpus and is
genuinely reduced by loading a feature subset. Compile cost is not: 184 MB of the 250 MB
cache is fixed structural precompute that a subset still pays. The download multiplier is
the only accidental cost of the three.

Five steps, A–E. Step A is independent; the rest have a required order, given in §7.

## 1. What must not break

Three existing guarantees constrain the order of work.

**Published versions are immutable, and a workflow enforces it.**
`.github/workflows/build-docid-raw-021.yml` records the tree hash of every published
release directory before it builds (lines 28-31), re-checks them after
(line 77: `git diff --exit-code HEAD -- tf/0.1.0 … tf/0.2.0 …`), and re-checks them again
before pushing (lines 101-104). Steps B and C below deliberately change this policy; they
must change the guards to match, not work around them.

**A release is compared against its predecessor — but not by the certifier.**
`programs/check_docid_raw_release.py` proves only `docid_raw` changed by diffing 0.2.1
against 0.2.0, feature file by feature file, so **0.2.0 must still be present when 0.2.1
is certified.** That comparison is *not* among `release_policy.REQUIRED_GATES`; it is a
separate workflow step, and the checker hardcodes `OLD = "0.2.0"` / `NEW = "0.2.1"` — a
one-off, not a standing mechanism. A release therefore certifies clean without it (issue
#38). The sequencing constraint is real; the guarantee behind it is weaker than it looks.

**The stamp is bound to bytes.** `tlhdig/stamp.py` digests `p.read_bytes()` for every
`.tf` file across the main dataset and the provenance module. Any step that changes what
ships changes the digest and requires re-certification, not a hand-edited manifest.

## 2. Step A — document the shallow clone

No repository change. `README.md` and `docs/RELEASE.md` gain the one line that saves a
consumer roughly 1.3 GB today — a full clone fetches ~1.5 GB, a depth-1 clone about
0.2 GB, and both then write the same ~1.7 GB checkout:

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

This does **not** shrink `.git`; the blobs stay in history. Reclaiming the ~1.4 GB of
packed history needs a rewrite, which would break every existing clone, fork and open PR.
Out of scope here — Step D exists so that it never becomes necessary.

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
needed. Git tags and (after Step D) release assets keep the bytes — though note that
GitHub release assets are mutable and deletable by any repo admin, so they are a
distribution channel, not an archive. That is an acceptable trade here precisely because
the versions are discardable; it would not be if they were being cited.

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
usability defect. That review was correct when written: it landed at 19:13 on 2026-08-30
and `app/config.yaml` was created 84 minutes later, at 20:37, by a commit named "Fix nine
findings from the independent architecture review". The app exists *because of* the
review, not in spite of it.

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
   125 MB zip. Produce them with `tf-zip` and attach them to the **GitHub release**.
   Zenodo was considered and rejected: hosting our own output there would mint this
   conversion a DOI it does not have and has not asked for, and GitHub assets are what
   `use()` reads natively.

   Two mechanics to settle first. `downloadRelease()` looks for exactly one asset name,
   `f"{relative-flattened}{version}.zip"` — `tf-0.2.1.zip` — so attaching a
   `tf-provenance` zip does nothing until `app/config.yaml` gains a `moduleSpecs:` entry,
   which it currently lacks. And `tf-zipall` / `zipAll()`, which bundles the app, the main
   module and every declared module into one `complete.zip`, is probably the better fit
   than per-directory `tf-zip`.
3. Once assets are authoritative, the repository need not carry any built dataset, and
   `check_docid_raw_release.py` gets its predecessor baseline from the previous asset —
   which resolves the gap Step B opens.

Consumer download after Step D: **125 MB for one version**, against ~1.5 GB today.

## 6. Step E — stop committing the upstream corpus; fetch it from Zenodo

`corpus/TLHdig-0.3/` is 380 MB and 24,135 tracked files. It is not our data: it is the
TLHdig Beta 0.3 archive, already cited in `CITATION.cff` and already published at
`doi:10.5281/zenodo.20328284`. Fetching it instead of committing it mints nothing — that
DOI is the upstream authors', and we cite it either way.

Everything needed is already in place:

- `programs/corpus.sha256` — 24,135 file hashes (24,142 lines, 7 of them comments), so
  per-file identity is already pinned;
- `corpus/TLHdig-0.3/ATTRIBUTION.md` — records the archive exactly:
  `TLHbasisONLINE25_1_ZENODO_Beta_03.zip`, 74,449,198 bytes, MD5
  `f9acbc8db3111cc7dd88d82f7819a912`;
- `programs/tlhdig/signref_inputs.py` — an existing locked-fetch-with-hash-verification
  pattern for external inputs, directly reusable.

Effect: **−380 MB** from every checkout, and the repository becomes the converter rather
than a second copy of someone else's corpus.

Two things complicate it. `programs/corpus.sha256` states that it "Covers EVERY file in
the tree, not only `*.xml`", and that **LICENSE and ATTRIBUTION.md are added by this
repository** — so a Zenodo fetch must reconstitute repo-authored files, not just unzip.
And the unzip has to reproduce all 24,135 pinned paths under the same Unicode
normalisation, which is exactly the hazard PR #34 just fixed for the corpus sort key.

The cost is real and should be weighed in a research pass first:

- the build gains a network dependency on Zenodo, where today it has none;
- `check_corpus_identity` becomes a gate over fetched rather than committed bytes;
- CI downloads 74 MB per run unless cached.

This is the same trade the signref lock already accepts for external sign lists, so there
is precedent — but it moves the corpus from "guaranteed present" to "verified on
arrival", which is a larger step than it looks. Note also
`signref_inputs.prepare()`'s current inability to recover from a corrupt cache (#36); that
failure mode would apply here too, over 380 MB instead of 30 KB.

## 7. Sequence

```text
A  document --depth 1                      independent, land now
D1 fix the stale version pin               one line, add a gate to check_app.py
B1 publish 0.2.1                           PR #11, unchanged
D2 release assets via tf-zip               1.5 GB -> 125 MB for a consumer
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

1. Step E's trade: is a Zenodo network dependency at build time acceptable in exchange for
   −380 MB and a repository that stops duplicating upstream? Needs
   `docs/research-corpus-acquisition.md` before it is answered.

Resolved:

- *Where this work is tracked* — issue #39. Defects found while drafting were filed
  separately: #36 (`signref_inputs.prepare()` cannot recover from a corrupt cache), #37
  (the stale version pin, which is step D1 here), #38 (certification does not check the
  predecessor). Folding #39 into #25's backlog orchestration remains reasonable.
- *Losing `tf/0.2.0` as a repository path* — acceptable; pre-alpha, versions are
  discardable.
- *Where release assets live* — GitHub. Zenodo rejected for our own output; it would mint
  a DOI this conversion has not asked for.
- *Whether `srcxml` keeps shipping* — retained. It is a 28 MB TF feature in the optional
  provenance module, not the upstream corpus, and it already costs nothing to a consumer
  who does not load that module. The 380 MB question was `corpus/`, now Step E.
