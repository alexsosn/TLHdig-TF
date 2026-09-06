"""Versioned invariants for a publishable full release certification.

Keep policy identity separate from orchestration and stamp parsing so the writer and the
independent verifier cannot silently disagree about what "full release" means. Changing
the required gate/input set or artifact-identity contract bumps POLICY.
"""

POLICY = "release-v2"
ARTIFACT_DIGEST_ALGORITHM = "tlhdig-tf-modules-v2"

REQUIRED_GATES = (
    "corpus-identity",
    "repair-manifest",
    "sign-round-trip",
    "morphology",
    "structure",
    "contract-a-graph",
    "marker-conservation",
    "tag-inventory",
    "provenance-split",
    "alignment",
    "fetch-signrefs",
    "check-signrefs",
    "app",
    "census",
    "code-tree-stable",
)

REQUIRED_INPUTS = (
    "corpusManifest",
    "repairManifest",
    "signrefLock",
)

FIDELITY_BASELINES = (
    "knownLossy",
    "contractAKnown",
    "knownWordDeficit",
)

MODES = frozenset({"regression-valid", "research-ready"})
