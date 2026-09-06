#!/usr/bin/env bash
# Stage the generated dataset for commit only after the full release gate certified it.
#
# tf/ is gitignored so `git add -A` cannot pick up a half-written dataset. This script
# is the deliberate publication path and refuses legacy census-only BUILD-COMPLETE
# stamps as well as stale/mismatched certification.
set -euo pipefail
cd "$(dirname "$0")/.."
version=$(sed -n 's/^TF_VERSION = "\([^"]*\)".*/\1/p' programs/tlhdig/__init__.py)
[ -n "${version}" ] || { echo "refusing: could not read TF_VERSION from programs/tlhdig/__init__.py"; exit 1; }
case "${version}" in *[!0-9.]*) echo "refusing: TF_VERSION parsed as '${version}', which is not a version"; exit 1;; esac
dir="tf/${version}"

# A new release must have passed release_check.py. check_stamp recomputes the artifact
# digest and also verifies the cryptographically-bound RELEASE-CERTIFICATION.json.
python3 programs/check_stamp.py --require-full || exit 1

# The binary cache TF compiles on load is derived, machine-specific and larger than the
# dataset; committing it would ship megabytes nobody can use.
rm -rf "${dir}/.tf"

big=$(find "${dir}" -type f -size +100M -print -quit)
[ -z "${big}" ] || { echo "refusing: ${big} exceeds GitHub's 100 MB limit (compaction did not run?)"; exit 1; }

# The provenance module ships too -- it is just not loaded unless asked for.
prov="tf-provenance/${version}"
rm -rf "${prov}/.tf"
git add -f "${dir}"
[ -d "${prov}" ] && git add -f "${prov}"
echo "staged ${dir} ($(find "${dir}" -type f | wc -l | tr -d ' ') files, $(du -sh "${dir}" | cut -f1))"
[ -d "${prov}" ] && echo "staged ${prov} ($(find "${prov}" -type f | wc -l | tr -d ' ') files, $(du -sh "${prov}" | cut -f1))"
