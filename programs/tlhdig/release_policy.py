"""Versioned invariants for a publishable full release certification.

Keep policy identity separate from orchestration and stamp parsing so the writer and the
independent verifier cannot silently disagree about what "full release" means. Changing
the required gate/input set or artifact-identity contract bumps POLICY.
"""
from __future__ import annotations

from dataclasses import dataclass

POLICY = "release-v5"
ARTIFACT_DIGEST_ALGORITHM = "tlhdig-tf-modules-v2"
DELTA_BASELINE_TF_VERSION = "0.3.0"
DELTA_BASELINE_DIGEST = (
    "sha256:93790f9e283c3c3d29d8a751b1eecbb7fd908745470aa36b9cec0525b90182d1"
)

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

_RELEASE_V4_GATES = _RELEASE_V3_GATES[:-1] + (
    "predecessor-delta",
    "code-tree-stable",
)
_RELEASE_V4_INPUTS = _RELEASE_V3_INPUTS + ("releaseDelta",)

_RELEASE_V5_GATES = (
    "corpus-identity",
    "repair-manifest",
    "sign-round-trip",
    "morphology",
    "structure",
    "sign-language",
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
    "predecessor-delta",
    "code-tree-stable",
)

REQUIRED_GATES = _RELEASE_V5_GATES
REQUIRED_INPUTS = _RELEASE_V4_INPUTS

MODES = frozenset({"regression-valid", "research-ready"})


@dataclass(frozen=True)
class PolicyContract:
    required_gates: tuple[str, ...]
    required_inputs: tuple[str, ...]
    fidelity_baselines: tuple[str, ...]
    requires_predecessor_evidence: bool = False
    delta_baseline_tf_version: str | None = None
    delta_baseline_digest: str | None = None


POLICY_CONTRACTS = {
    "release-v3": PolicyContract(
        required_gates=_RELEASE_V3_GATES,
        required_inputs=_RELEASE_V3_INPUTS,
        fidelity_baselines=FIDELITY_BASELINES,
    ),
    "release-v4": PolicyContract(
        required_gates=_RELEASE_V4_GATES,
        required_inputs=_RELEASE_V4_INPUTS,
        fidelity_baselines=FIDELITY_BASELINES,
        requires_predecessor_evidence=True,
        delta_baseline_tf_version=DELTA_BASELINE_TF_VERSION,
        delta_baseline_digest=DELTA_BASELINE_DIGEST,
    ),
    "release-v5": PolicyContract(
        required_gates=_RELEASE_V5_GATES,
        required_inputs=_RELEASE_V4_INPUTS,
        fidelity_baselines=FIDELITY_BASELINES,
        requires_predecessor_evidence=True,
        delta_baseline_tf_version=DELTA_BASELINE_TF_VERSION,
        delta_baseline_digest=DELTA_BASELINE_DIGEST,
    ),
}


def policy_contract(name: object) -> PolicyContract | None:
    """Return the immutable verification contract for a recorded policy name."""
    return POLICY_CONTRACTS.get(name) if isinstance(name, str) else None
