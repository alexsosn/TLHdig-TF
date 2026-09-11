# Research: symlinked mandatory inputs before destructive rebuild (#128)

Status: research only. No build behavior changes here.

## Question

Can a mandatory checked-in input satisfy `programs/build.py` preflight through a symlink, allowing the current generated artifact to be deleted before the repository's stricter identity layer rejects that input?

## Current destructive boundary

`build.py` performs source/config preflight and then calls `reset_current_output()` before conversion. The required checked-in inputs on current `main` are `programs/patches.yaml`, `programs/corpus.sha256`, and `programs/excluded.txt`; #124 adds conversion-critical `programs/signmap-multi.tsv` to the same pre-reset set.

The existence predicate is `Path.is_file()`. In Python, `Path.is_file()` follows a symlink and reports true when the target is a regular file. The subsequent readers likewise consume the resolved target normally.

That means this sequence is currently possible on a checkout that preserves symlinks:

1. a required path is a symlink to a readable regular file;
2. `is_file()` accepts it;
3. build preflight/source parsing succeeds far enough to reach cleanup;
4. `reset_current_output()` deletes current `tf/<TF_VERSION>` and `tf-provenance/<TF_VERSION>`;
5. conversion may run using the symlink target;
6. later current-build identity/validation rejects the same input because `tlhdig.build_manifest._sha256()` explicitly fails when `path.is_symlink()` is true.

The late rejection protects manifest truth, but not preservation of the previously valid current artifact. The invariant needed here is therefore earlier and narrower: an invalid mandatory build input must fail before destructive reset.

## Repository evidence

The current `programs/` Git tree contains no mode-`120000` symlink entries. Relevant build/validation data files are ordinary blobs (`100644`), including:

- `patches.yaml`;
- `corpus.sha256`;
- `excluded.txt`;
- `signmap-multi.tsv`;
- `signmap.tsv`;
- `known_lossy.txt`;
- `contract_a_known.txt`;
- `signrefs.lock.json`.

So no present repository workflow depends on these files being symlinks. Requiring regular non-symlink files is compatible with the checked-in state.

The existing output-reset boundary is already deliberately stricter than `resolve()`-and-delete: #118 rejects symlinked output targets/parents and validates both targets before deleting either. Applying the same fail-closed principle to the finite set of mandatory pre-reset inputs is consistent with current architecture rather than a new security framework.

## Scope: destructive inputs vs validation-only inputs

Not every file in `validate_current.current_inputs()` needs to block cleanup merely because the later manifest hashes it.

The pre-reset contract should cover files consumed by the build before/during conversion whose absence/substitution can affect the rebuilt artifact:

- repair manifest;
- corpus identity manifest;
- exclusion ledger;
- compound sign map once #124 lands.

Files used only by later validation (`known_lossy.txt`, `contract_a_known.txt`, `signmap.tsv`, sign-reference lock, etc.) are a separate ordering question. Moving every validation input into destructive preflight would broaden this ticket and duplicate future validation orchestration work. #128 should protect exactly the build's mandatory pre-reset inputs unless another file is proven conversion-critical during implementation refresh.

## Minimal rule

For each mandatory pre-reset path, require both:

```python
path.is_file() and not path.is_symlink()
```

and report the offending repository path before reset.

A stronger resolved-parent ownership rule is unnecessary for this ticket. The inputs are not caller-selected arbitrary paths: they are exact repository-owned constants. Rejecting the path object itself when it is a symlink closes the demonstrated gap without inventing a generic filesystem trust abstraction.

A regular file reached through a symlinked repository/programs parent is not part of the current checked-in topology and is already outside the ordinary Git checkout contract. If later evidence shows parent-path substitution is practical in supported execution environments, it should get its own path-ownership ticket/test rather than silently expanding this one.

## Cross-platform test implications

POSIX Git/checkout can preserve mode-`120000` symlinks. Windows environments may disable symlink creation or materialize/check out links differently depending on Git configuration and privileges.

Therefore the production invariant should be platform-independent (`Path.is_symlink()` is explicit), while an integration fixture that creates a real symlink may use `pytest.skip` only when the platform genuinely cannot create it. A small helper-level test can still exercise the regular-file acceptance/rejection predicate without making the whole contract depend on symlink privileges.

## Relationship to #124 and #126

- #124 owns adding missing `signmap-multi.tsv` to mandatory pre-reset existence checking.
- #126 owns semantic/content usability of that table before reset.
- #128 owns filesystem type of mandatory pre-reset inputs.

The clean implementation order is: establish the final required-input set from #124, then make one focused preflight helper/check express missing, symlink, and (where owned by #126) content diagnostics without duplicating cleanup logic.

## Research conclusion

**Confirmed defect class; narrow fix justified.**

A symlink to a valid regular file can satisfy the current `is_file()` preflight but contradict the repository's later manifest identity policy. All relevant checked-in inputs are regular Git blobs, so there is no compatibility reason to accept symlinks. The smallest safe contract is to reject symlinked mandatory pre-reset inputs before either generated output tree is touched.
