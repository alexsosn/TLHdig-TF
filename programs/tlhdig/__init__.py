"""TLHdig → Text-Fabric conversion.

Source : TLHdig Beta 0.3, Zenodo 10.5281/zenodo.20328284 (CC-BY-4.0)
Layout : see ../../docs/TF-CONVERSION-PLAN.md
"""
SOURCE_VERSION = "0.3"      # upstream TLHdig release
TF_VERSION = "0.5.0"        # this ontology + converter (kept separate, plan §9)

# Provenance features live in a separate Text-Fabric module, loaded only when wanted.
#
# `srcxml` and `src_span` are large validation/audit payloads rather than ordinary query
# features. At sign level they preserve byte-exact source fragments; at document-level
# they preserve the complete original AOHeader. The document header intentionally
# includes fields that are not semantically modelled as dedicated TF features, so raw
# preservation must not be confused with semantic normalization. Contract A verifies
# graph/source byte fidelity and Contract B declares which source constructs are
# represented semantically versus preserved-only.
#
# TF loads a module by path: `alexsosn/TLHdig-TF/tf-provenance`, or locally by passing
# both directories as `locations`.
PROVENANCE_DIR = "tf-provenance"
PROVENANCE_FEATURES = ("srcxml", "src_span")
