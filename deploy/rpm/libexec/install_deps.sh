#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub manager - 依赖检查/补装脚本
#
# 大多数系统依赖由 witty-ub-manager 子包的 Requires 自动拉装（postgresql /
# postgresql-server / systemd / python3 / curl / nginx）。本脚本仅做：
# - 验证关键二进制存在（systemctl / psql / python3 / curl / nginx）
# - 验证 witty-ub 主包已安装
# - 验证 Python venv（由主包 %post 创建）存在
# - 缺失时按 OS 调用 dnf/apt 补装
#
# 用法:
#   /usr/libexec/witty-ub-manager/install_deps.sh
#   由 manager.sh 的 install 子命令调用

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

# ──────────────────── 验证 ────────────────────

verify_deps() {
    _step_header "验证 witty-ub 依赖"

    detect_os || return 1

    local missing=()

    # 关键二进制
    for cmd in systemctl psql python3 curl nginx; do
        if _has_cmd "$cmd"; then
            _log "  $cmd ✓"
        else
            _warn "  $cmd ✗"
            missing+=("$cmd")
        fi
    done

    # 主包
    if rpm -q witty-ub >/dev/null 2>&1; then
        _log "  witty-ub 主包 ✓"
    else
        _warn "  witty-ub 主包 ✗（请先 sudo yum install -y witty-ub）"
        missing+=("witty-ub")
    fi

    # manager 子包（即本脚本所属包，自检）
    if rpm -q witty-ub-manager >/dev/null 2>&1; then
        _log "  witty-ub-manager 子包 ✓"
    else
        _warn "  witty-ub-manager 子包 ✗"
        missing+=("witty-ub-manager")
    fi

    # Python venv（由主包 %post 创建）
    local VENV_DIR="$WITTY_LATENCY_DIR/.venv"
    if [ -x "$VENV_DIR/bin/python" ]; then
        _log "  Python venv ✓"
    else
        _warn "  Python venv ✗（$VENV_DIR 不存在）"
        _info "  重新创建:"
        _info "    sudo python3 -m venv $VENV_DIR"
        _info "    sudo $VENV_DIR/bin/pip install -r $WITTY_LATENCY_DIR/deploy/requirements.txt"
        missing+=("venv")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        _warn "缺少 ${#missing[@]} 项依赖: ${missing[*]}"
        return 1
    fi
    _log "依赖完整"
    return 0
}

# ──────────────────── 补装 ────────────────────

install_missing() {
    _step_header "补装缺失系统依赖"
    detect_os || return 1
    _require_root || return 1

    local SUDO=""
    _is_root || SUDO="sudo"

    case "$OS_ID" in
        openeuler)
            _info "安装 openEuler 系统依赖（postgresql-server, python3, curl, nginx）..."
            eval "$SUDO $PM_UPDATE"
            eval "$SUDO $PM_INSTALL postgresql-server postgresql python3 curl nginx" || {
                _err "依赖补装失败"
                return 1
            }
            ;;
        ubuntu)
            _info "安装 Ubuntu 系统依赖（postgresql, python3, curl, nginx）..."
            eval "$SUDO $PM_UPDATE"
            eval "$SUDO $PM_INSTALL postgresql postgresql-client python3 python3-venv curl nginx" || {
                _err "依赖补装失败"
                return 1
            }
            ;;
    esac

    _log "系统依赖补装完成"

    # 若 venv 缺失，主动创建并装 pip 依赖
    # 前提：witty-ub 主包已安装，/var/witty-ub/latency/ 目录存在（由主包 %files 提供）
    local VENV_DIR="$WITTY_LATENCY_DIR/.venv"
    if [ ! -x "$VENV_DIR/bin/python" ]; then
        if [ ! -d "$WITTY_LATENCY_DIR" ]; then
            _err "witty-ub 主包未安装，无法创建 venv: $WITTY_LATENCY_DIR 不存在"
            _info "请先执行: sudo yum install -y witty-ub"
            return 1
        fi
        _info "创建 Python venv 并安装依赖..."
        eval "$SUDO python3 -m venv $VENV_DIR" || { _warn "venv 创建失败"; return 1; }
        if [ -f "$WITTY_LATENCY_DIR/deploy/requirements.txt" ]; then
            eval "$SUDO $VENV_DIR/bin/pip install -r $WITTY_LATENCY_DIR/deploy/requirements.txt" || {
                _warn "pip 依赖安装失败，可稍后手动重试"
            }
        else
            _warn "$WITTY_LATENCY_DIR/deploy/requirements.txt 不存在，跳过 pip 安装"
        fi
        _log "Python venv 已就绪"
    fi
}

# ──────────────────── 入口 ────────────────────

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if verify_deps; then
        exit 0
    fi
    install_missing
fi
