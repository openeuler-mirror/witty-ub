#!/usr/bin/env bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# publish_split_release.sh - Build and publish witty-ub container images for the
# split frontend/backend deployment, as multi-arch (amd64 + arm64) manifest lists,
# into a Harbor registry.
#
# Why this exists:
#   The default `build.sh --multi` only publishes the All-in-One image. The split
#   deployment (docs/deployment/08-container.md) pulls `witty-ub:latest`,
#   `witty-ub:backend`, and `witty-ub:frontend` from the same repository. To build
#   the backend/frontend role images on a fresh machine you must first publish the
#   matching base images. This script does all of that for a given release tag.
#
# Secret-free: registry credentials are never embedded. Log in once first, e.g.
#   docker login <registry>        # or export HARBOR_USERNAME / HARBOR_PASSWORD
#
# Usage:
#   VERSION=v1.0.4-3 REGISTRY=hub-harbor.oepkgs.net PROJECT=neocopilot \
#     bash scripts/publish_split_release.sh
#
# Options (environment variables):
#   REGISTRY       registry host                          (default hub-harbor.oepkgs.net)
#   PROJECT        registry project / namespace           (default neocopilot)
#   VERSION        immutable release tag (e.g. v1.0.4-3); "latest" = dev/snapshot
#   PLATFORMS      buildx platforms                       (default linux/amd64,linux/arm64)
#   PUBLISH_BASE   1=also (re)build & push base images, 0=reuse existing base
#   PUBLISH_APP    1=build & push app role images, 0=skip
#   BUILD_DIR      source tree to build from              (default repo root)
#   BUILDER        buildx builder name                    (default witty-ub-builder)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

REGISTRY="${REGISTRY:-hub-harbor.oepkgs.net}"
PROJECT="${PROJECT:-neocopilot}"
VERSION="${VERSION:-latest}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
PUBLISH_BASE="${PUBLISH_BASE:-1}"
PUBLISH_APP="${PUBLISH_APP:-1}"
BUILD_DIR="${BUILD_DIR:-${ROOT}}"
BUILDER="${BUILDER:-witty-ub-builder}"

REPO="${REGISTRY}/${PROJECT}"
BASE_REPO="${REPO}/witty-ub-base"
BACKEND_BASE_REPO="${REPO}/witty-ub-base-backend"
FRONTEND_BASE_REPO="${REPO}/witty-ub-base-frontend"
APP_IMAGE="${REPO}/witty-ub"

log() { echo "[publish] $*"; }

require() {
  command -v docker >/dev/null 2>&1 || {
    echo "docker not found" >&2
    exit 1
  }
  docker buildx version >/dev/null 2>&1 || {
    echo "docker buildx not available" >&2
    exit 1
  }
}

ensure_builder() {
  # A docker-container buildx driver is required for cross-platform (multi-arch)
  # builds. The default "docker" driver cannot build amd64 while on arm64 (and
  # vice-versa). Note: this does NOT install QEMU/binfmt - on Linux hosts that
  # must be pre-installed (e.g. tonistiigi/binfmt); Docker Desktop bundles it.
  if docker buildx ls 2>/dev/null | grep -qE "${BUILDER}"; then
    log "using existing buildx builder '${BUILDER}'"
  else
    log "creating buildx builder '${BUILDER}' (docker-container driver)"
    docker buildx create --name "${BUILDER}" --driver docker-container --use
  fi
  docker buildx inspect --bootstrap "${BUILDER}" >/dev/null
  docker buildx use "${BUILDER}"
}

build_web() {
  # The web frontend MUST be built on the host (native arch) - it is COPY'd into
  # the image. Building it inside an emulated (QEMU) platform is slow and memory
  # heavy. The build output is src/web/dist, and .dockerignore keeps it out of
  # source control.
  local web_dir="${BUILD_DIR}/src/web"
  if [ ! -d "${web_dir}" ]; then
    echo "ERROR: src/web not found under ${BUILD_DIR}" >&2
    exit 1
  fi
  pushd "${web_dir}" >/dev/null
  log "installing web dependencies (npm)"
  npm ci --no-audit --no-fund
  log "building web frontend"
  export HUSKY=0
  npm run build-only
  [ -d dist ] || {
    echo "ERROR: web build did not produce src/web/dist" >&2
    exit 1
  }
  popd >/dev/null
  log "web dist ready"
}

publish_base() {
  log "publishing base images (multi-arch: ${PLATFORMS})"
  docker buildx build --progress=plain \
    --platform "${PLATFORMS}" --push \
    -f Dockerfile.base --target base \
    -t "${BASE_REPO}:latest" -t "${BASE_REPO}:${VERSION}" \
    "${BUILD_DIR}"
  docker buildx build --progress=plain \
    --platform "${PLATFORMS}" --push \
    -f Dockerfile.base --target base-backend \
    -t "${BACKEND_BASE_REPO}:latest" -t "${BACKEND_BASE_REPO}:${VERSION}" \
    "${BUILD_DIR}"
  docker buildx build --progress=plain \
    --platform "${PLATFORMS}" --push \
    -f Dockerfile.base --target base-frontend \
    -t "${FRONTEND_BASE_REPO}:latest" -t "${FRONTEND_BASE_REPO}:${VERSION}" \
    "${BUILD_DIR}"
}

publish_app() {
  local base_arg="${BASE_REPO}:${VERSION}"
  # All-in-One (default target). Uses the all-in-one base for the C++ toolchain.
  log "publishing All-in-One image"
  docker buildx build --progress=plain \
    --platform "${PLATFORMS}" --push \
    --build-arg "BASE_IMAGE=${base_arg}" \
    -t "${APP_IMAGE}:latest" \
    -t "${APP_IMAGE}:${VERSION}" \
    "${BUILD_DIR}"

  # Backend role image.
  log "publishing backend role image"
  docker buildx build --progress=plain \
    --platform "${PLATFORMS}" --push \
    --build-arg "BASE_IMAGE=${base_arg}" \
    --build-arg "BASE_IMAGE_BACKEND=${BACKEND_BASE_REPO}:${VERSION}" \
    --target backend \
    -t "${APP_IMAGE}:backend" \
    -t "${APP_IMAGE}:backend-${VERSION}" \
    "${BUILD_DIR}"

  # Frontend role image.
  log "publishing frontend role image"
  docker buildx build --progress=plain \
    --platform "${PLATFORMS}" --push \
    --build-arg "BASE_IMAGE=${base_arg}" \
    --build-arg "BASE_IMAGE_FRONTEND=${FRONTEND_BASE_REPO}:${VERSION}" \
    --target frontend \
    -t "${APP_IMAGE}:frontend" \
    -t "${APP_IMAGE}:frontend-${VERSION}" \
    "${BUILD_DIR}"
}

verify() {
  log "verifying published manifest lists"
  docker buildx imagetools inspect "${APP_IMAGE}:${VERSION}" >/dev/null 2>&1 ||
    {
      echo "ERROR: All-in-One manifest missing for ${VERSION}" >&2
      exit 1
    }
  docker buildx imagetools inspect "${APP_IMAGE}:backend" >/dev/null 2>&1 ||
    {
      echo "ERROR: backend manifest missing" >&2
      exit 1
    }
  docker buildx imagetools inspect "${APP_IMAGE}:frontend" >/dev/null 2>&1 ||
    {
      echo "ERROR: frontend manifest missing" >&2
      exit 1
    }
  log "OK: All-in-One / backend / frontend are multi-arch manifest lists"
}

main() {
  require
  [ "${PUBLISH_BASE}" = "1" ] || [ "${PUBLISH_APP}" = "1" ] ||
    {
      echo "nothing to do" >&2
      exit 1
    }
  if [ "${VERSION}" = "latest" ]; then
    log "WARNING: VERSION=latest means this is a moving snapshot, not a release."
  fi
  ensure_builder
  if [ "${PUBLISH_WEB:-1}" = "1" ]; then
    build_web
  fi
  [ "${PUBLISH_BASE}" = "1" ] && publish_base
  [ "${PUBLISH_APP}" = "1" ] && publish_app
  verify
  log "done. Published repo: ${REPO} (version=${VERSION}, platforms=${PLATFORMS})"
}

main "$@"
