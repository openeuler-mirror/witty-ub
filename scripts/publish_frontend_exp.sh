#!/usr/bin/env bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# publish_frontend_exp.sh - 构建并推送"试验性前端（exp）"nightly 镜像。
#
# 设计要点（详见 docs/deployment/09-experimental-frontend.md）：
#   * 后端与既有前端镜像只从 release tag 构建，本脚本不碰它们；
#   * exp 镜像 = 当前 release 前端镜像 + 当日 exp 前端静态产物；
#   * exp 版本用日期管理：frontend-exp-<YYYYMMDD>（不可变）+ frontend-exp（移动标签）；
#   * 载荷内写入 BUILD_INFO（base_release / source_commit / build_date），便于追溯与回滚。
#
# 用法:
#   bash scripts/publish_frontend_exp.sh                 # 当天 nightly，默认推送到 Harbor
#   BASE_RELEASE=v1.0.4-5 EXP_DATE=20260916 bash scripts/publish_frontend_exp.sh
#   PUSH=0 bash scripts/publish_frontend_exp.sh          # 只本地构建，不推送（调试）
#   SKIP_BUILD=1 bash scripts/publish_frontend_exp.sh    # 复用已有 dist，只重打镜像
#
# 环境变量:
#   REGISTRY       镜像仓主机           (默认 hub-harbor.oepkgs.net)
#   PROJECT        镜像仓项目           (默认 neocopilot)
#   APP_IMAGE      应用镜像名           (默认 <registry>/<project>/witty-ub)
#   BASE_RELEASE   exp 镜像的 release 底座 (默认取仓库最新 v* tag)
#   EXP_DATE       exp 版本日期 YYYYMMDD (默认当天)
#   EXP_SOURCE_DIR exp 前端源码目录      (默认 src/web_exp，缺失时回退 src/web_new)
#   PLATFORMS      构建平台             (默认 linux/amd64,linux/arm64)
#   BUILDER        buildx builder 名称  (默认 witty-ub-builder)
#   NPM_REGISTRY   npm 源               (默认 https://mirrors.huaweicloud.com/repository/npm/)
#   PUSH           1=推送 0=只本地加载   (默认 1)
#   SKIP_BUILD     1=跳过 npm 构建      (默认 0)
#   KEEP_CONTEXT   1=保留临时构建上下文 (默认 0)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

REGISTRY="${REGISTRY:-hub-harbor.oepkgs.net}"
PROJECT="${PROJECT:-neocopilot}"
APP_IMAGE="${APP_IMAGE:-${REGISTRY}/${PROJECT}/witty-ub}"
BASE_RELEASE="${BASE_RELEASE:-}"
EXP_DATE="${EXP_DATE:-$(date +%Y%m%d)}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
BUILDER="${BUILDER:-witty-ub-builder}"
NPM_REGISTRY="${NPM_REGISTRY:-https://mirrors.huaweicloud.com/repository/npm/}"
PUSH="${PUSH:-1}"
SKIP_BUILD="${SKIP_BUILD:-0}"
KEEP_CONTEXT="${KEEP_CONTEXT:-0}"

# 本地加载（PUSH=0）不支持多平台产物，默认收敛到本机架构
if [ "${PUSH}" != "1" ] && [ "${PLATFORMS}" = "linux/amd64,linux/arm64" ]; then
    case "$(uname -m)" in
    arm64 | aarch64) PLATFORMS="linux/arm64" ;;
    x86_64 | amd64) PLATFORMS="linux/amd64" ;;
    esac
fi

log() { echo "[exp] $*"; }
die() {
    echo "[exp][ERROR] $*" >&2
    exit 1
}

resolve_source_dir() {
    if [ -n "${EXP_SOURCE_DIR:-}" ]; then
        echo "${EXP_SOURCE_DIR}"
        return
    fi
    if [ -d "${ROOT}/src/web_exp" ]; then
        echo "${ROOT}/src/web_exp"
    elif [ -d "${ROOT}/src/web_new" ]; then
        # 目录改名（src/web_new → src/web_exp）落地前的兼容路径
        echo "${ROOT}/src/web_new"
    else
        die "找不到 exp 前端源码目录（src/web_exp 或 src/web_new）"
    fi
}

resolve_base_release() {
    if [ -n "${BASE_RELEASE}" ]; then
        echo "${BASE_RELEASE}"
        return
    fi
    local tag
    tag="$(git -C "${ROOT}" tag -l 'v*' --sort=-v:refname 2>/dev/null | head -1 || true)"
    [ -n "${tag}" ] || die "无法自动识别 release tag，请显式设置 BASE_RELEASE=<tag>"
    echo "${tag}"
}

require_tools() {
    command -v docker >/dev/null 2>&1 || die "docker 未安装"
    docker buildx version >/dev/null 2>&1 || die "docker buildx 不可用"
    if [ "${PUSH}" = "1" ]; then
        docker buildx inspect "${BUILDER}" >/dev/null 2>&1 ||
            die "buildx builder '${BUILDER}' 不存在：docker buildx create --name ${BUILDER} --driver docker-container --use"
    fi
}

build_web() {
    local web_dir="$1"
    [ -f "${web_dir}/package.json" ] || die "${web_dir} 不是有效的前端目录"
    pushd "${web_dir}" >/dev/null
    log "安装依赖并构建前端（node $(node -v 2>/dev/null || echo '?')）"
    npm ci --no-audit --no-fund --registry="${NPM_REGISTRY}"
    npm run build-only
    [ -d dist ] || die "构建未产生 ${web_dir}/dist"
    popd >/dev/null
}

main() {
    local web_dir base_release git_commit base_image exp_version created

    require_tools
    web_dir="$(resolve_source_dir)"
    base_release="$(resolve_base_release)"
    base_image="${APP_IMAGE}:frontend-${base_release}"
    exp_version="exp-${EXP_DATE}"
    created="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    git_commit="$(git -C "${ROOT}" rev-parse HEAD 2>/dev/null || echo unknown)"

    [ "${SKIP_BUILD}" = "1" ] || build_web "${web_dir}"
    [ -f "${web_dir}/dist/index.html" ] || die "${web_dir}/dist 不存在或不完整（可用 SKIP_BUILD=0 重新构建）"

    log "base release : ${base_release} (${base_image})"
    log "web source   : ${web_dir}"
    log "commit       : ${git_commit}"
    log "exp version  : ${exp_version}"

    # 组装最小构建上下文：dist/ + 指向 web-exp 的 nginx 模板
    CTX_DIR="$(mktemp -d "${TMPDIR:-/tmp}/witty-ub-exp-XXXXXX")"
    if [ "${KEEP_CONTEXT}" = "1" ]; then
        log "保留构建上下文: ${CTX_DIR}"
    else
        trap 'rm -rf "${CTX_DIR:-}"' EXIT
    fi

    mkdir -p "${CTX_DIR}/dist"
    cp -R "${web_dir}/dist/." "${CTX_DIR}/dist/"
    # 镜像内 nginx 沿用 release 前端容器的运行路径（/run/witty-ub-web、/var/log/witty-ub-web，
    # 由 docker/entrypoint.sh 创建），只把静态根指向 exp 产物目录。
    sed 's|root /var/witty-ub/web;|root /var/witty-ub/web-exp;|' \
        "${ROOT}/packaging/nginx/witty-ub-web.conf.template" \
        >"${CTX_DIR}/nginx.conf.template"
    grep -q 'root /var/witty-ub/web-exp;' "${CTX_DIR}/nginx.conf.template" ||
        die "生成 exp 版 nginx 模板失败（未替换静态根）"

    {
        echo "base_release=${base_release}"
        echo "base_image=${base_image}"
        echo "source_commit=${git_commit}"
        echo "source_dir=$(basename "${web_dir}")"
        echo "build_date=$(date +%Y-%m-%d)"
        echo "build_kind=nightly"
    } >"${CTX_DIR}/dist/BUILD_INFO"

    local -a extra=()
    if [ "${PUSH}" = "1" ]; then
        extra+=(--push)
    else
        extra+=(--load)
    fi

    log "构建 overlay 镜像（${PLATFORMS}）"
    docker buildx build --builder "${BUILDER}" "${extra[@]}" \
        --platform "${PLATFORMS}" \
        --build-arg "BASE_IMAGE=${base_image}" \
        --build-arg "EXP_VERSION=${exp_version}" \
        --build-arg "EXP_REVISION=${git_commit}" \
        --build-arg "EXP_BUILD_DATE=${created}" \
        --build-arg "BASE_RELEASE=${base_release}" \
        -f "${ROOT}/deploy/docker/Dockerfile.frontend-exp" \
        -t "${APP_IMAGE}:frontend-exp-${EXP_DATE}" \
        -t "${APP_IMAGE}:frontend-exp" \
        "${CTX_DIR}"

    if [ "${PUSH}" = "1" ]; then
        log "校验已推送的 manifest"
        docker buildx imagetools inspect "${APP_IMAGE}:frontend-exp-${EXP_DATE}" >/dev/null
        log "完成：${APP_IMAGE}:frontend-exp-${EXP_DATE}（移动标签 frontend-exp 已更新）"
    else
        log "完成（本地镜像）：${APP_IMAGE}:frontend-exp-${EXP_DATE}"
    fi
}

main "$@"
