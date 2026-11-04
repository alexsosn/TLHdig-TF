# Plan amendment: bind executable code tree (#116)

The frozen plan's `codeCommit` rule correctly avoids requiring the producing commit to equal the later commit that adds `BUILD-MANIFEST.json`, but a commit SHA used only as provenance does not by itself make stale generated output detectable after converter/validator code changes.

Before production implementation, add one direct current-code identity to the manifest.

`build_manifest` will hash a deterministic logical mapping of the executable files supplied by the caller. The repository-level caller will include:

- top-level `programs/*.py` commands;
- `programs/tlhdig/*.py` converter/validation modules;
- `app/config.yaml`.

`requirements.txt` remains a separately named reproducibility input. Corpus source identity remains governed by `programs/corpus.sha256` plus the existing independent corpus-identity gate; patches, exclusions and external sign-reference lock remain separately named inputs.

The manifest gains:

```json
"code": {
  "algorithm": "tlhdig-current-code-v1",
  "digest": "sha256:...",
  "files": {
    "app/config.yaml": "sha256:...",
    "programs/build.py": "sha256:...",
    "programs/tlhdig/convert.py": "sha256:..."
  }
}
```

Verification recomputes this identity from the current checkout. Therefore a later docs/workflow/manifest-only commit does not invalidate the current build, while an executable converter/checker/config change does. `codeCommit` remains useful provenance for the checkout that actually ran validation.

A RED regression test must prove that changing one supplied executable file invalidates a previously written manifest before production code is added.
