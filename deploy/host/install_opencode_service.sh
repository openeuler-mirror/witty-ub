#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# install_opencode_service.sh - 把 OpenCode（Agent 服务）注册为 systemd **user** 服务。
#
# 背景：deploy.sh 与 RPM 管理器默认把 OpenCode 作为"裸进程 + pidfile"托管
# （deploy/deploy_opencode.sh），重启后需人工再启动。本脚本提供可选的 systemd
# user 单元托管（常驻 + 开机自启），用于：
#   * 宿主机/源码部署希望 Agent 常驻的节点；
#   * VM/容器化开发环境中需要随用户会话自动拉起 Agent 的场景。
#
# 两种托管方式互斥（都监听 4096）：切换前请先停止另一种。
#
# 用法:
#   bash deploy/host/install_opencode_service.sh install     # 安装 + 启用 + 启动
#   bash deploy/host/install_opencode_service.sh status
#   bash deploy/host/install_opencode_service.sh uninstall   # 停止 + 移除单元
#
# 环境变量:
#   OPENCODE_BIN        opencode 可执行文件（默认自动探测）
#   WITTY_API_BASE      后端地址（默认 http://127.0.0.1:9772）
#   WITTY_NO_PROXY      Agent curl 的 no_proxy（默认 127.0.0.1；后端为远端 IP 时用 *）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
UNIT_NAME="witty-ub-opencode.service"
UNIT_SRC="$SCRIPT_DIR/systemd/$UNIT_NAME"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
export WITTY_API_BASE="${WITTY_API_BASE:-http://127.0.0.1:9772}"
export WITTY_NO_PROXY="${WITTY_NO_PROXY:-127.0.0.1}"

log() { echo "[opencode-service] $*"; }
die() {
    echo "[opencode-service][ERROR] $*" >&2
    exit 1
}

detect_opencode() {
    if [ -n "${OPENCODE_BIN:-}" ]; then
        echo "$OPENCODE_BIN"
        return
    fi
    for candidate in "$(command -v opencode 2>/dev/null || true)" \
        /usr/local/bin/opencode /usr/bin/opencode /opt/node22/bin/opencode; do
        [ -n "$candidate" ] && [ -x "$candidate" ] && {
            echo "$candidate"
            return
        }
    done
    die "未找到 opencode 可执行文件，请先安装（npm i -g opencode-ai）或设置 OPENCODE_BIN"
}

systemd_user_available() {
    command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1
}

do_install() {
    systemd_user_available || die "systemctl --user 不可用（需 systemd-pam 且已 enable-linger）"
    [ -f "$UNIT_SRC" ] || die "单元模板缺失: $UNIT_SRC"
    local bin
    bin="$(detect_opencode)"
    mkdir -p "$UNIT_DIR"
    sed -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
        -e "s|__OPENCODE_BIN__|$bin|g" \
        -e "s|__WITTY_API_BASE__|$WITTY_API_BASE|g" \
        -e "s|__WITTY_NO_PROXY__|$WITTY_NO_PROXY|g" \
        "$UNIT_SRC" >"$UNIT_DIR/$UNIT_NAME"
    systemctl --user daemon-reload
    systemctl --user enable --now "$UNIT_NAME"
    sleep 1
    if curl --noproxy 127.0.0.1 -sf -o /dev/null http://127.0.0.1:4096/global/health; then
        log "OpenCode 已就绪: http://127.0.0.1:4096（bin=$bin, api=$WITTY_API_BASE）"
    else
        log "单元已启动但健康检查未通过，请查看: journalctl --user -u $UNIT_NAME -n 50 --no-pager"
    fi
}

do_status() {
    systemctl --user status "$UNIT_NAME" --no-pager 2>/dev/null | head -12 || log "未安装 $UNIT_NAME"
}

do_uninstall() {
    systemctl --user disable --now "$UNIT_NAME" >/dev/null 2>&1 || true
    rm -f "$UNIT_DIR/$UNIT_NAME"
    systemctl --user daemon-reload 2>/dev/null || true
    log "已移除 $UNIT_NAME（如需改回裸进程托管：bash deploy/deploy_opencode.sh）"
}

case "${1:-install}" in
install | start) do_install ;;
status) do_status ;;
uninstall | remove) do_uninstall ;;
*) die "未知子命令: $1（支持 install|status|uninstall）" ;;
esac
