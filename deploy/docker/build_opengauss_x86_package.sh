#!/bin/bash
# Build an AVX2 openGauss package from the exact source used by the
# current RAG database image. Image assembly/publishing remains a separate CI
# step; production hosts never run this script during deployment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
EXPECTED_COMMIT="22b8cbffbd33023b7be11e17297c11972ab2e378"
PATCH_FILE="${PROJECT_DIR}/deploy/patches/opengauss/22b8cbff-datavec-avx2.patch"

usage() {
    cat <<'EOF'
Usage:
  build_opengauss_x86_package.sh SOURCE_DIR BINARYLIBS_DIR

Environment:
  OPENGAUSS_BUILD_JOBS   Parallel build jobs (default: 2)

The source checkout must be at commit
22b8cbffbd33023b7be11e17297c11972ab2e378. The script applies the repository
patch once, builds a release package, and prints generated package paths.
EOF
}

[ "$#" -eq 2 ] || { usage >&2; exit 2; }

case "$(uname -m)" in
x86_64 | amd64) ;;
*)
    echo "This builder only supports x86_64/amd64 hosts; got $(uname -m)" >&2
    exit 1
    ;;
esac

SOURCE_DIR="$(cd "$1" && pwd)"
BINARYLIBS_DIR="$(cd "$2" && pwd)"
BUILD_JOBS="${OPENGAUSS_BUILD_JOBS:-2}"

case "$BUILD_JOBS" in
'' | *[!0-9]* | 0) echo "OPENGAUSS_BUILD_JOBS must be a positive integer" >&2; exit 2 ;;
esac

[ -x "$SOURCE_DIR/build.sh" ] || { echo "Missing executable build.sh in $SOURCE_DIR" >&2; exit 1; }
[ -f "$PATCH_FILE" ] || { echo "Missing patch: $PATCH_FILE" >&2; exit 1; }

ACTUAL_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD)"
if [ "$ACTUAL_COMMIT" != "$EXPECTED_COMMIT" ]; then
    echo "Source commit mismatch: expected $EXPECTED_COMMIT, got $ACTUAL_COMMIT" >&2
    exit 1
fi

if git -C "$SOURCE_DIR" apply --check "$PATCH_FILE"; then
    git -C "$SOURCE_DIR" apply "$PATCH_FILE"
elif git -C "$SOURCE_DIR" apply --reverse --check "$PATCH_FILE"; then
    echo "CPU target patch is already applied"
else
    echo "CPU target patch does not apply cleanly to $SOURCE_DIR" >&2
    exit 1
fi

export OPENGAUSS_BUILD_JOBS="$BUILD_JOBS"
export MAKEFLAGS="${MAKEFLAGS:--j${BUILD_JOBS}}"

echo "Building openGauss commit $EXPECTED_COMMIT for AVX2+FMA"
bash "$SOURCE_DIR/build.sh" \
    -m release \
    -3rd "$BINARYLIBS_DIR" \
    -wrap \
    -pm opengauss \
    --cmake

echo "Generated packages:"
find "$SOURCE_DIR" -maxdepth 4 -type f \
    \( -name 'openGauss-Server-*.tar.bz2' -o -name 'openGauss-Server-*.tar.gz' \) \
    -print
