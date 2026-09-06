"""TLHdig → Text-Fabric conversion.

Source : TLHdig Beta 0.3, Zenodo 10.5281/zenodo.20328284 (CC-BY-4.0)
Layout : see ../../docs/TF-CONVERSION-PLAN.md
"""
SOURCE_VERSION = "0.3"      # upstream TLHdig release
TF_VERSION = "0.3.0"        # this ontology + converter (kept separate, plan §9)

# Provenance features live in a separate Text-Fabric module, loaded only when wanted.
#
# `srcxml` and `src_span` are 56 MB of 412 -- more than the entire lexical and
# morphological layer -- and they serve validation, not query. Every tag inside
# `srcxml` is modelled elsewhere: the wrappers as `sgr`/`agr`/`det`/`num`, the damage
# markers as `cluster` nodes with offsets, `corr` and `note` as their own features.
# What they uniquely give is the byte-exact round trip, which is Contract A's business.
#
# TF loads a module by path: `alexsosn/TLHdig-TF/tf-provenance`, or locally by passing
# both directories as `locations`.
PROVENANCE_DIR = "tf-provenance"
PROVENANCE_FEATURES = ("srcxml", "src_span")
