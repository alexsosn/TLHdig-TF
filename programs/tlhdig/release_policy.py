"""Versioned invariants for a publishable full release certification.

Keep policy identity separate from orchestration and stamp parsing so the writer and the
independent verifier cannot silently disagree about what "full release" means. Changing
the required gate/input set or artifact-identity contract bumps POLICY.
"""
from __future__ import annotations

from dataclasses import dataclass

POLICY = "release-v4"
ARTIFACT_DIGEST_ALGORITHM = "tlhdig-tf-modules-v2"
DELTA_BASELINE_TF_VERSION = "0.3.0"

FIDELITY_BASELINES = (
    "knownLossy",
    "contractAKnown",
    "knownWordDeficit",
)

_RELEASE_V3_GATES = (
    "corpus-identity",
    "repair-manifest",
    "sign-round-trip",
    "morphology",
    "structure",
    "manuscript-joins",
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
_RELEASE_V3_INPUTS = (
    "corpusManifest",
    "repairManifest",
    "signrefLock",
)

REQUIRED_GATES = _RELEASE_V3_GATES[:-1] + (
    "predecessor-delta",
    "code-tree-stable",
)
REQUIRED_INPUTS = _RELEASE_V3_INPUTS + ("releaseDelta",)

MODES = frozenset({"regression-valid", "research-ready"})


@dataclass(frozen=True)
class PolicyContract:
    required_gates: tuple[str, ...]
    required_inputs: tuple[str, ...]
    fidelity_baselines: tuple[str, ...]
    requires_predecessor_evidence: bool = False


POLICY_CONTRACTS = {
    "release-v3": PolicyContract(
        required_gates=_RELEASE_V3_GATES,
        required_inputs=_RELEASE_V3_INPUTS,
        fidelity_baselines=FIDELITY_BASELINES,
    ),
    "release-v4": PolicyContract(
        required_gates=REQUIRED_GATES,
        required_inputs=REQUIRED_INPUTS,
        fidelity_baselines=FIDELITY_BASELINES,
        requires_predecessor_evidence=True,
    ),
}


def policy_contract(name: object) -> PolicyContract | None:
    """Return the immutable verification contract for a recorded policy name."""
    return POLICY_CONTRACTS.get(name) if isinstance(name, str) else None
