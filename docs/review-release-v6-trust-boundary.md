# Adversarial review: release-v6 trust boundary

Independent review of #81 after its first canonical GREEN found four additional fail-closed gaps. Production fixes must preserve the already-hosted RED evidence before this branch can be finalized.

1. **Ignored untracked protected files were invisible.** `git ls-files --others --exclude-standard` omits ignored files, so an ignored local executable under `programs/**` could be present while the protected identity still described only committed HEAD. Hosted RED `34458403112` proved the current implementation did not raise; 619 existing tests passed and exactly this one new test failed.
2. **GitHub Actions `.yaml` release workflows were outside the profile.** The temporary release-workflow families matched only `.yml` even though GitHub accepts both suffixes. Hosted RED `34458675530` produced exactly the expected three failures total at that point: the ignored-file test plus the protected-identity and retrigger assertions for `.yaml`.
3. **`programs/shard.txt` is executable test input, not research metadata.** `programs/tests/test_shard.py` reads it to select the 91-document adversarial integration shard that checks source/graph structure, marker conservation, and compaction. Excluding it allows material changes in integration-test coverage without changing the protected identity or retriggering canonical certification.
4. **`programs/research_weblink_ids.py` is promoted release-safety code despite its name.** It is imported by `test_tlhdig_weblink.py`, inspected by `test_release_hygiene.py`, and executed directly by ordinary CI as the TLHdig web-link identity safety gate. A blanket `research_*.py` exclusion therefore cannot exclude this specific file.

Hosted RED `34459042882` froze all four findings together: **619 existing tests passed and exactly 6 intended tests failed**. No unrelated test failed.

## Minimal GREEN contract

- inspect both ordinary and ignored untracked files under protected paths;
- exempt only normal generated Python bytecode under `__pycache__` so imports themselves do not self-invalidate certification;
- make `programs/shard.txt` protected;
- keep genuinely research-only top-level `research_*.py` excluded, but explicitly protect `research_weblink_ids.py` because current tests/CI execute it;
- match and retrigger temporary release-workflow families for both `.yml` and `.yaml`;
- preserve historical schema-1 policy behavior and release-v6 digest algorithm/profile identifiers;
- after GREEN, rerun ordinary CI and canonical certification because these changes alter the protected release-v6 identity.

Any new blocker found on the resulting exact head restarts RED → fix → full gates → fresh independent review.