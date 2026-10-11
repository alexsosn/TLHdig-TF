# Plan: reject symlinked mandatory build inputs before reset (#128)

Status: frozen after `docs/research-preflight-symlinks.md`. Production work starts only after the active #124/#126 preflight chain is synchronized so this ticket does not duplicate or race their required-input/content checks.

## Contract

Every mandatory input that `programs/build.py` requires before `reset_current_output()` must be an existing regular file **and not a symlink**.

On failure:

- print/name the offending repository path and reason;
- return failure before `reset_current_output()`;
- leave the previous current main/provenance trees and `BUILD-MANIFEST.json` untouched;
- never call the converter.

Normal regular-file behavior is unchanged.

## Scope

Apply this only to the finite destructive-build preflight set. After #124 that set is expected to be:

- `PATCHES` / `programs/patches.yaml`;
- `PROGRAMS / "corpus.sha256"`;
- `PROGRAMS / "excluded.txt"`;
- `PROGRAMS / "signmap-multi.tsv"`.

Refresh against merged #124/#126 before coding. If that final code centralizes the set/helper, extend it rather than creating a second list.

Do not automatically pull every `validate_current.current_inputs()` entry into pre-reset checking: validation-only allowlists/reference locks are not proven destructive-build dependencies.

## TDD / RED gate

Before production changes, add focused tests proving the current behavior is unsafe.

Required cases:

1. create a valid regular target file and replace one mandatory input path with a symlink to it;
2. run/simulate build orchestration and require failure before reset;
3. assert a sentinel old `BUILD-MANIFEST.json` or old generated feature remains byte-identical;
4. assert converter was not called;
5. diagnostic identifies the offending input and says it is a symlink/not a regular owned input;
6. an ordinary regular mandatory input remains accepted;
7. test at least two representatives if the final preflight helper has path-specific behavior (otherwise one parametrized integration case plus helper unit cases is sufficient).

For platforms where creating a filesystem symlink is unavailable, the integration fixture may skip only that real-symlink case. Keep a platform-independent unit contract for the helper/predicate so Windows CI cannot report the entire invariant as untested.

The RED commit must not alter production preflight.

## Minimal implementation

Prefer one small helper near the existing build preflight, for example:

```python
def preflight_regular_input(path: Path) -> str | None:
    if path.is_symlink():
        return "symlink is not allowed"
    if not path.is_file():
        return "missing or not a regular file"
    return None
```

Exact API may follow #124/#126's merged shape. Check `is_symlink()` before `is_file()` so a broken symlink receives an explicit symlink diagnostic rather than being misreported only as missing.

Do not resolve/follow the target to validate it. Do not add a generalized repository ownership/sandbox abstraction.

## Ordering with #126

If #126 has already introduced semantic validation for `signmap-multi.tsv`, filesystem-type validation runs first:

1. mandatory path type/existence;
2. table semantic usability (#126);
3. source identity/exclusion parsing as currently ordered;
4. destructive reset;
5. conversion.

A symlink therefore cannot be opened by the semantic validator before the filesystem preflight rejects it.

## GREEN gates

Require:

- focused preflight tests;
- full `python -m pytest programs/tests -q`;
- ordinary CI;
- current `BUILD-MANIFEST.json` refresh/verification if the merged implementation touches `programs/build.py` or other manifest-bound executable code;
- no generated TF semantic/output changes expected from the successful regular-file path.

If current-output hashes change on a normal build, stop and investigate; #128 itself should not alter corpus bytes.

## Logically independent adversarial review

On the exact final head, attack at least:

- broken symlink reported merely as missing and accidentally followed later;
- symlink target opened by #126 content validation before type rejection;
- one mandatory input omitted from the centralized check;
- validation-only files accidentally promoted into destructive preflight without evidence;
- reset occurring before all mandatory paths are checked;
- converter invoked after a rejected input;
- legitimate regular-file builds changed;
- tests passing only because symlink creation skipped on the runner;
- manifest refresh describing different executable bytes than final head.

A blocking finding requires a focused regression before correction and a fresh exact-head review.

## Non-goals

- arbitrary repository symlink auditing;
- symlinked output cleanup paths (already owned by #118/#119);
- semantic compound-map validation (#126);
- dependency locking or release certification;
- parent-directory sandboxing absent evidence of a supported execution-path defect.
