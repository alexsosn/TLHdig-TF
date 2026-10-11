# Research: clean-user acquisition resolves a stale artifact

Issue: #47

## Question

A clean user runs `use("alexsosn/TLHdig-TF")` or `tf alexsosn/TLHdig-TF` with an empty
`~/text-fabric-data` cache and no local clone. Which app code and which generated TF
artifact does pinned Text-Fabric `13.1.0` actually select, and is it the one supported
current artifact `tf/0.4.0`?

This is a distribution/resolution question. It is not about adding another Agora
registration: the corpus is already registered in Agora `registry/resources.yaml` as
`TLHdig-TF` with `tf_path: tf/0.4.0`, lazily following upstream main.

## Resolution semantics in pinned Text-Fabric 13.1.0

Read from the pinned installation, not from documentation prose.

`tf/advanced/repo.py::fromString()` maps the checkout specifier to a (commit, release)
request pair. For the bare/default case the specifier is the empty string:

```python
if not string:
    commit = ""
    release = ""
```

`Checkout.download()` then tries the release first and only falls back to a commit:

```python
if rChk is not None:
    fetched = self.downloadRelease(rChk, showErrors=cChk is None)
if not fetched and cChk is not None:
    fetched = self.downloadCommit(cChk, showErrors=True)
```

`getReleaseObj("")` resolves an empty release request to GitHub's **latest release**:

```python
r = g.get_release(release) if release else g.get_latest_release()
```

`getCommitObj("")` resolves an empty commit request to the **default-branch head**:

```python
cs = g.get_commits(sha=commit) if commit else g.get_commits()
```

So bare acquisition means: *the GitHub latest release if one exists, otherwise the head
of the default branch*. It does not mean current main while any non-prerelease,
non-draft release exists.

App checkout and data checkout are independent calls, but both default to the same bare
specifier, so both land on the same release.

## Finding 1 — the latest release is stale, and it resolves silently

The repository's only release is `tlhdig-0.3_tf-0.2.0`, published 2026-09-05, not a
draft and not a prerelease, therefore GitHub's `releases/latest`. It points at commit
`4309cf3318c682282c1480b233786362a3083471`.

At that commit:

- `app/config.yaml` declares `provenanceSpec.version: "0.1.0"` with `relative: /tf`;
- the tree contains **both** `tf/0.1.0` and `tf/0.2.0`.

The release carries **no assets**. `downloadRelease()` looks for an asset named
`tf-<version>.zip`, finds none, and falls back to `downloadCommit(commit)` for the
*release's* commit rather than to the default-branch head.

Consequence: the app is taken from the stale release, it declares version `0.1.0`, that
version directory exists at the same commit, and the load **succeeds** against
`tf/0.1.0`. The user is two schema generations behind current `tf/0.4.0` with no error
and no warning.

A silent stale success is worse than a failure. This is the defect #47 must close.

### Empirical confirmation

Probe run 2026-10-11 in a fresh interpreter with `HOME` set to an empty temporary
directory **before the first `import tf`**, checking out only the small `/app` folder so
no dataset download was required:

```json
{
  "commit": "4309cf3318c682282c1480b233786362a3083471",
  "release": "tlhdig-0.3_tf-0.2.0",
  "local": null,
  "appDir": "alexsosn/TLHdig-TF/app"
}
```

Bare acquisition selected the stale release, as predicted from the code path.

## Finding 2 — the documented install cannot acquire online at all

`README.md` documents `python -m pip install text-fabric==13.1.0`, and
`requirements.txt` pins the same bare distribution. Neither provides Text-Fabric's
GitHub backend, which needs the `[github]` extra (PyGithub).

With the documented install the same probe fails before any resolution happens:

```text
Backend provider github not supported.
Cannot reach online data on github
Try installing text-fabric one of the following:
pip install text-fabric[github]
```

So the documented install path cannot perform bare acquisition in either direction.
`requirements.txt` is bound by `BUILD-MANIFEST.json` and exists for *rebuild*
reproducibility; the consumer install instruction is a separate README concern and is
where the `[github]` extra belongs.

## Finding 3 — upstream TF 13.1.0 is incompatible with current PyGithub

With `text-fabric[github]==13.1.0` and the PyGithub resolved today, resolution succeeds
but the subsequent download aborts:

```text
could not save corpus data to ~/text-fabric-data/github
unexpected error from builtins: 'RateLimitOverview' object has no attribute 'core'
```

TF 13.1.0 reads `rate_limiting.core` on an object whose current PyGithub shape no longer
exposes it. This is an upstream defect, it is outside #47's contract, and it does not
affect Findings 1 and 2: resolution had already selected the stale release before the
failure. It does mean a distribution gate must distinguish *resolution* assertions from
*download* assertions, and must report an unavailable backend as an explicit state
rather than as a pass.

## Repair options considered

**Delete the release and tag.** With no non-prerelease release, `getReleaseObj("")`
returns `None`, `downloadRelease()` returns `False`, and the fallback
`downloadCommit("")` resolves the default-branch head — current main, declaring
`0.4.0`. Correct outcome, but it destroys a published public artifact irreversibly and
discards the release notes.

**Cut a new release at current main.** Makes the latest release current today, but
re-creates exactly the obligation #115 removed: every rebuild of the pre-alpha artifact
would need a new release to keep bare acquisition honest. Rejected as an artificial
release bottleneck.

**Mark the existing release as a prerelease.** GitHub defines `releases/latest` as the
most recent non-draft, non-prerelease release, so a prerelease is skipped. Resolution
falls through to the default-branch head, which is what the one-current-artifact policy
in #115 actually means. The historical release, its tag, and its notes survive as a
development record, and the change is reversible.

The third option is selected. It matches #115 ("GitHub Releases are optional snapshots,
not the primary source of truth for ongoing pre-alpha development") and needs no
per-rebuild maintenance.

## What the gate must assert

Resolution, not download, is the contract that can be checked deterministically:

1. either the repository publishes **no** GitHub latest release, in which case bare
   acquisition resolves the default-branch head;
2. or the published latest release declares the current `TF_VERSION` in its
   `app/config.yaml` **and** contains `tf/<TF_VERSION>`.

Both branches are acceptable; silently resolving a different artifact is not. The second
branch is kept open deliberately so a future deliberate snapshot does not have to fight
the gate.

Mirroring the established `check_signrefs.py` policy, the gate runs `--mode ordinary`
with an explicit availability skip and `--mode release` where an unavailable backend is
a failure rather than a pass.

## Scope boundary

In scope: bare-acquisition resolution, the gate, and the stale-release repair.

Out of scope: the `:hot` / `:clone` browser commands and their smoke proof (#44/#45,
plan frozen in `docs/plan-browser-product-smoke.md`), the upstream PyGithub defect in
Finding 3, and full dependency-environment locking (#106).

## Post-fix verification

`tlhdig-0.3_tf-0.2.0` was marked as a prerelease on 2026-10-11.
`GET /repos/alexsosn/TLHdig-TF/releases/latest` now answers `404 Not Found`, and the
same probe re-run against the live repository resolves:

```json
{
  "commit": "88dc8298547b11e8a954a7bfb07dd3e55aa716ab",
  "release": null,
  "local": null
}
```

That commit is exactly `origin/main` at the time of measurement, so bare acquisition now
tracks the default-branch head and therefore the current artifact. The gate passes in
strict `--mode release`.

The download step still aborts on the upstream PyGithub incompatibility of Finding 3.
That is a separate upstream defect; the resolution contract this issue owns is restored.

## Conclusion

Bare acquisition is empirically proven to resolve the stale `tlhdig-0.3_tf-0.2.0`
release and to load `tf/0.1.0` silently. Marking that release as a prerelease restores
default resolution to current main without creating a per-rebuild release obligation.
A resolution gate with ordinary/release modes keeps the property from regressing, and
the README install instruction needs the `[github]` extra before bare acquisition can
work for a documented clean user at all.
