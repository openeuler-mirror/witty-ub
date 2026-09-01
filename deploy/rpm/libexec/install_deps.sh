#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub manager - 依赖检查/补装脚本
#
# 系统依赖由子包 Requires 自动拉装（backend: python3 + C++ 运行库;
# web: nginx + nodejs; manager: curl + systemd）。本脚本仅做：
# - 按角色验证关键二进制存在（backend: systemctl/psql/python3/venv;
#   frontend: systemctl/nginx/npm; 公共: curl）
# - 验证对应子包已安装
# - 缺失时按 OS 调用 dnf/apt 补装
# - 后端角色每次按 requirements.txt 创建/更新 Python venv
#
# 用法:
#   /usr/libexec/witty-ub-manager/install_deps.sh
#   由 manager.sh 的 deploy / deps 子命令调用

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

# 角色来源: 调用方已探测（WITTY_ROLE）> WITTY_ROLE_FORCE > 自动探测
if [ -z "${WITTY_ROLE:-}" ]; then
    detect_role || exit 1
fi
role_services || exit 1

# RPM 子包检查（非 RPM 系统（Ubuntu）无子包概念，跳过）
_pkg_installed() {
    _has_cmd rpm || return 0
    rpm -q "$1" >/dev/null 2>&1
}

# ──────────────────── 验证 ────────────────────

verify_deps() {
    _step_header "验证 witty-ub 依赖（角色: ${WITTY_ROLE}）"

    detect_os || return 1

    local missing=()
    local cmd

    # 公共二进制
    for cmd in systemctl curl; do
        if _has_cmd "$cmd"; then
            _log "  $cmd ✓"
        else
            _warn "  $cmd ✗"
            missing+=("$cmd")
        fi
    done

    # 后端角色: PG 客户端 + Python venv
    if [ "$WITTY_ROLE" != "frontend" ]; then
        for cmd in psql python3; do
            if _has_cmd "$cmd"; then
                _log "  $cmd ✓"
            else
                _warn "  $cmd ✗"
                missing+=("$cmd")
            fi
        done
        local VENV_DIR="$WITTY_LATENCY_DIR/.venv"
        if [ -x "$VENV_DIR/bin/python" ]; then
            _log "  Python venv ✓"
        else
            _warn "  Python venv ✗（$VENV_DIR 不存在）"
            missing+=("venv")
        fi
        if _pkg_installed witty-ub-backend || _pkg_installed witty-ub; then
            _log "  witty-ub-backend 子包 ✓"
        else
            _warn "  witty-ub-backend 子包 ✗（请先 sudo dnf install -y witty-ub-backend）"
            missing+=("witty-ub-backend")
        fi
    fi

    # 前端角色: nginx + node
    if [ "$WITTY_ROLE" != "backend" ]; then
        for cmd in nginx node npm; do
            if _has_cmd "$cmd"; then
                _log "  $cmd ✓"
            else
                _warn "  $cmd ✗"
                missing+=("$cmd")
            fi
        done
        if _pkg_installed witty-ub-web || _pkg_installed witty-ub; then
            _log "  witty-ub-web 子包 ✓"
        else
            _warn "  witty-ub-web 子包 ✗（请先 sudo dnf install -y witty-ub-web）"
            missing+=("witty-ub-web")
        fi
    fi

    # manager 子包（即本脚本所属包，自检）
    if _pkg_installed witty-ub-manager; then
        _log "  witty-ub-manager 子包 ✓"
    else
        _warn "  witty-ub-manager 子包 ✗"
        missing+=("witty-ub-manager")
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
    _step_header "补装缺失系统依赖（角色: ${WITTY_ROLE}）"
    detect_os || return 1
    _require_root || return 1

    local SUDO=""
    _is_root || SUDO="sudo"

    case "$OS_ID" in
    openeuler)
        local PKGS=(curl)
        [ "$WITTY_ROLE" != "frontend" ] && PKGS+=(postgresql-server postgresql python3 python3-pip)
        [ "$WITTY_ROLE" != "backend" ] && PKGS+=(nginx nodejs)
        _info "安装 openEuler 系统依赖: ${PKGS[*]}"
        eval "$SUDO $PM_UPDATE"
        eval "$SUDO $PM_INSTALL ${PKGS[*]}" || {
            _err "依赖补装失败"
            return 1
        }
        ;;
    ubuntu)
        local PKGS=(curl)
        [ "$WITTY_ROLE" != "frontend" ] && PKGS+=(postgresql postgresql-client python3 python3-venv)
        [ "$WITTY_ROLE" != "backend" ] && PKGS+=(nginx nodejs)
        _info "安装 Ubuntu 系统依赖: ${PKGS[*]}"
        eval "$SUDO $PM_UPDATE"
        eval "$SUDO $PM_INSTALL ${PKGS[*]}" || {
            _err "依赖补装失败"
            return 1
        }
        ;;
    esac

    _log "系统依赖补装完成"

}

# 与源码部署一致，每次完整部署都按 requirements.txt 更新依赖，避免 RPM
# 升级后继续使用 venv 中残留的旧版 Python 包。
install_python_deps() {
    [ "$WITTY_ROLE" = "frontend" ] && return 0

    _step_header "安装 Python 依赖"
    _require_root || return 1

    local VENV_DIR="$WITTY_LATENCY_DIR/.venv"
    local REQUIREMENTS_FILE="$WITTY_LATENCY_DIR/deploy/requirements.txt"
    local LOG_FILE="/var/log/witty-ub/pip-install.log"
    local SUDO=""
    _is_root || SUDO="sudo"

    [ -d "$WITTY_LATENCY_DIR" ] || {
        _err "witty-ub-backend 未安装: $WITTY_LATENCY_DIR 不存在"
        return 1
    }
    [ -f "$REQUIREMENTS_FILE" ] || {
        _err "Python 依赖清单不存在: $REQUIREMENTS_FILE"
        return 1
    }

    if [ ! -x "$VENV_DIR/bin/python" ]; then
        _info "创建 Python venv: $VENV_DIR"
        $SUDO python3 -m venv "$VENV_DIR" || {
            _err "venv 创建失败"
            return 1
        }
    fi

    $SUDO mkdir -p "$(dirname "$LOG_FILE")"
    _info "按 requirements.txt 安装/更新 Python 依赖..."
    if ! $SUDO "$VENV_DIR/bin/pip" install -U -r "$REQUIREMENTS_FILE" 2>&1 | \
        $SUDO tee "$LOG_FILE"; then
        _err "Python 依赖安装失败，最近日志:"
        tail -30 "$LOG_FILE" 2>/dev/null || true
        return 1
    fi
    _log "Python 依赖已就绪"
}

# ──────────────────── 入口 ────────────────────

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if ! verify_deps; then
        install_missing
    fi
    install_python_deps
fi
