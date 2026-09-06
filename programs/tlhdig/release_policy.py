"""Versioned invariants for a publishable full release certification.

Keep policy identity separate from orchestration and stamp parsing so the writer and the
independent verifier cannot silently disagree about what "full release" means. Changing
the required gate/input set is a policy change and should bump POLICY.
"""

POLICY = "release-v1"

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
