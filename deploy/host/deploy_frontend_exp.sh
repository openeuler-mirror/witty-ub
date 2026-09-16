#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub 试验性前端（exp）独立部署脚本（宿主机/裸金属，源码方式）
#
# 与既有 deploy.sh 的关系：完全独立，不修改任何既有服务/端口/配置。
#   既有前端: 8080(nginx) / 5173(vite)   →  /var/witty-ub/web
#   exp  前端: 8081(nginx) / 5174(vite)  →  /var/witty-ub/web-exp
#
# 用法:
#   bash deploy/host/deploy_frontend_exp.sh install            # 构建 + 安装 + 启动（默认）
#   WITTY_BACKEND_URL=http://<后端IP>:9772 \
#     bash deploy/host/deploy_frontend_exp.sh install          # 指向后端节点
#   bash deploy/host/deploy_frontend_exp.sh stop               # 停止
#   bash deploy/host/deploy_frontend_exp.sh status             # 查看状态
#   bash deploy/host/deploy_frontend_exp.sh uninstall          # 停止并清理（含 /var/witty-ub/web-exp）
#
# 环境变量:
#   EXP_WEB_DIR             exp 前端源码目录（默认 src/web_exp，回退 src/web_new）
#   WITTY_BACKEND_URL       后端地址（默认 http://127.0.0.1:9772）
#   WITTY_AGENT_URL         OpenCode 地址（默认 http://127.0.0.1:4096）
#   WITTY_WEB_EXP_PORT      nginx 端口（默认 8081）
#   DEPLOY_PM               systemd|nohup（默认自动探测 systemd --user）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_DIR="$PROJECT_DIR/.deploy-logs"
RUN_DIR="$PROJECT_DIR/.deploy-run"
UNIT_NAME="witty-ub-frontend-exp.service"
UNIT_SRC="$SCRIPT_DIR/systemd/$UNIT_NAME"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
WEB_ROOT=/var/witty-ub/web-exp

if [ -n "${EXP_WEB_DIR:-}" ]; then
    WEB_DIR="$EXP_WEB_DIR"
elif [ -d "$PROJECT_DIR/src/web_exp" ]; then
    WEB_DIR="$PROJECT_DIR/src/web_exp"
else
    WEB_DIR="$PROJECT_DIR/src/web_new"
fi

export WITTY_BACKEND_URL="${WITTY_BACKEND_URL:-http://127.0.0.1:9772}"
export WITTY_AGENT_URL="${WITTY_AGENT_URL:-http://127.0.0.1:4096}"
export WITTY_WEB_EXP_PORT="${WITTY_WEB_EXP_PORT:-8081}"
NPM_REGISTRY="${NPM_REGISTRY:-https://mirrors.huaweicloud.com/repository/npm/}"

log() { echo "[exp-deploy] $*"; }
warn() { echo "[exp-deploy][WARN] $*" >&2; }
die() {
    echo "[exp-deploy][ERROR] $*" >&2
    exit 1
}

systemd_user_available() {
    command -v systemctl >/dev/null 2>&1 || return 1
    systemctl --user show-environment >/dev/null 2>&1
}

use_systemd() {
    case "${DEPLOY_PM:-auto}" in
    systemd) return 0 ;;
    nohup) return 1 ;;
    *) systemd_user_available ;;
    esac
}

write_env_file() {
    mkdir -p "$RUN_DIR"
    cat >"$RUN_DIR/frontend-exp.env" <<EOF
# witty-ub 试验性前端运行配置（deploy_frontend_exp.sh 生成，供 systemd 单元加载）
WITTY_BACKEND_URL=$WITTY_BACKEND_URL
WITTY_AGENT_URL=$WITTY_AGENT_URL
WITTY_WEB_EXP_PORT=$WITTY_WEB_EXP_PORT
EOF
    log "配置已写入 $RUN_DIR/frontend-exp.env"
}

build_web() {
    [ -f "$WEB_DIR/package.json" ] || die "$WEB_DIR 不是有效的前端目录"
    pushd "$WEB_DIR" >/dev/null
    log "构建 exp 前端（$WEB_DIR）"
    if [ ! -d node_modules ]; then
        npm ci --no-audit --no-fund --registry="$NPM_REGISTRY"
    fi
    npm run build-only
    [ -d dist ] || die "构建未产生 dist/"
    popd >/dev/null
}

install_unit() {
    mkdir -p "$UNIT_DIR"
    sed -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" "$UNIT_SRC" >"$UNIT_DIR/$UNIT_NAME"
    systemctl --user daemon-reload
    systemctl --user enable "$UNIT_NAME" >/dev/null 2>&1 || true
    systemctl --user restart "$UNIT_NAME"
    log "已通过 systemd user unit 启动: $UNIT_NAME"
}

start_nohup() {
    mkdir -p "$LOG_DIR" "$RUN_DIR"
    [ -f "$LOG_DIR/web-exp.pid" ] && kill "$(cat "$LOG_DIR/web-exp.pid")" 2>/dev/null || true
    nohup bash "$SCRIPT_DIR/run_frontend_exp.sh" >"$LOG_DIR/web-exp.log" 2>&1 &
    echo $! >"$LOG_DIR/web-exp.pid"
    log "已通过 nohup 启动（日志 $LOG_DIR/web-exp.log）"
}

do_install() {
    mkdir -p "$LOG_DIR" "$RUN_DIR"
    write_env_file
    if [ ! -f "$WEB_DIR/dist/index.html" ]; then
        build_web
    else
        log "复用已有 dist（$WEB_DIR/dist；如需重建先删除该目录）"
    fi

    if use_systemd; then
        install_unit
    else
        warn "systemd --user 不可用，回退 nohup 托管"
        start_nohup
    fi

    sleep 2
    local port="$WITTY_WEB_EXP_PORT"
    curl --noproxy 127.0.0.1 -sf -o /dev/null "http://127.0.0.1:${port}/" &&
        log "exp 前端就绪: http://$(hostname -I 2>/dev/null | awk '{print $1}'):${port}/" ||
        warn "exp 前端暂未响应，请查看: journalctl --user -u $UNIT_NAME -n 50 --no-pager"
    curl --noproxy '*' -sf -o /dev/null --max-time 5 "${WITTY_BACKEND_URL}/health_check" &&
        log "后端可达: ${WITTY_BACKEND_URL}/health_check" ||
        warn "后端不可达: ${WITTY_BACKEND_URL}（exp 前端页面仍可用，接口与 Agent 需后端可达）"
}

do_stop() {
    if systemctl --user list-unit-files 2>/dev/null | grep -q "$UNIT_NAME"; then
        systemctl --user stop "$UNIT_NAME" || true
    fi
    [ -f "$LOG_DIR/web-exp.pid" ] && kill "$(cat "$LOG_DIR/web-exp.pid")" 2>/dev/null || true
    rm -f "$LOG_DIR/web-exp.pid"
    log "exp 前端已停止"
}

do_status() {
    if systemctl --user is-active --quiet "$UNIT_NAME" 2>/dev/null; then
        log "service: active ($UNIT_NAME)"
    else
        log "service: inactive"
    fi
    local code
    code="$(curl --noproxy 127.0.0.1 -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${WITTY_WEB_EXP_PORT}/" || true)"
    log "http   : ${code:-000} (port $WITTY_WEB_EXP_PORT)"
    log "check  : $(curl --noproxy 127.0.0.1 -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${WITTY_WEB_EXP_PORT}/health_check" || true)"
}

do_uninstall() {
    do_stop
    systemctl --user disable "$UNIT_NAME" >/dev/null 2>&1 || true
    rm -f "$UNIT_DIR/$UNIT_NAME"
    rm -f "$RUN_DIR/frontend-exp.env"
    systemctl --user daemon-reload 2>/dev/null || true
    local SUDO=""
    [ "$(id -u)" -eq 0 ] || SUDO="sudo"
    $SUDO rm -rf "$WEB_ROOT"
    log "已卸载 exp 前端（既有前端与后端未受影响）"
}

case "${1:-install}" in
install | start) do_install ;;
stop) do_stop ;;
status) do_status ;;
uninstall | remove) do_uninstall ;;
-h | --help | help)
    sed -n '2,30p' "$0"
    ;;
*) die "未知子命令: $1（支持 install|stop|status|uninstall）" ;;
esac
