#!/usr/bin/env bash
# Stage the generated dataset for commit -- only when a build actually finished.
#
# tf/ is gitignored so that `git add -A` cannot pick up a half-written dataset. This
# script is the deliberate path. It refuses to stage anything that is not complete or
# that GitHub would reject.
set -euo pipefail
cd "$(dirname "$0")/.."
version=$(sed -n 's/^TF_VERSION = "\(.*\)"/\1/p' programs/tlhdig/__init__.py)
dir="tf/${version}"

[ -f "${dir}/BUILD-COMPLETE" ] || { echo "refusing: ${dir}/BUILD-COMPLETE missing (build unfinished?)"; exit 1; }

big=$(find "${dir}" -type f -size +100M -print -quit)
[ -z "${big}" ] || { echo "refusing: ${big} exceeds GitHub's 100 MB limit (compaction did not run?)"; exit 1; }

git add -f "${dir}"
echo "staged ${dir} ($(find "${dir}" -type f | wc -l | tr -d ' ') files, $(du -sh "${dir}" | cut -f1))"
