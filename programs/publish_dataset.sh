#!/usr/bin/env bash
# Stage the generated dataset for commit -- only when a build actually finished.
#
# tf/ is gitignored so that `git add -A` cannot pick up a half-written dataset. This
# script is the deliberate path. It refuses to stage anything that is not complete or
# that GitHub would reject.
set -euo pipefail
cd "$(dirname "$0")/.."
# `s/.../\1/p` replaces only the matched span and prints the whole line, so a greedy
# pattern left the trailing `# comment` glued to the version and every path was wrong.
# Match the quoted value exactly and consume the rest of the line.
version=$(sed -n 's/^TF_VERSION = "\([^"]*\)".*/\1/p' programs/tlhdig/__init__.py)
[ -n "${version}" ] || { echo "refusing: could not read TF_VERSION from programs/tlhdig/__init__.py"; exit 1; }
case "${version}" in *[!0-9.]*) echo "refusing: TF_VERSION parsed as '${version}', which is not a version"; exit 1;; esac
dir="tf/${version}"

# census.py writes this marker, and only after loading the compacted files in a fresh
# process and passing every invariant -- so its presence means verified, not just
# written. A dataset straight out of build.py will not have it.
[ -f "${dir}/BUILD-COMPLETE" ] || { echo "refusing: ${dir}/BUILD-COMPLETE missing (run programs/census.py to verify and stamp)"; exit 1; }

# The binary cache TF compiles on load is derived, machine-specific and larger than the
# dataset; committing it would ship megabytes nobody can use.
rm -rf "${dir}/.tf"

big=$(find "${dir}" -type f -size +100M -print -quit)
[ -z "${big}" ] || { echo "refusing: ${big} exceeds GitHub's 100 MB limit (compaction did not run?)"; exit 1; }

git add -f "${dir}"
echo "staged ${dir} ($(find "${dir}" -type f | wc -l | tr -d ' ') files, $(du -sh "${dir}" | cut -f1))"
