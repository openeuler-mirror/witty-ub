#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub 依赖安装脚本
# 系统包（dnf/apt）+ Python venv 依赖。
#
# 用法:
#   bash deploy/install_deps.sh   # 安装系统依赖 + Python 依赖
#   source deploy/install_deps.sh  # 仅定义函数，供 deploy.sh 调用

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
source "$SCRIPT_DIR/_lib.sh"

# ──────────────────── 系统依赖 ────────────────────

install_system_deps() {
    _step_header "安装系统依赖"

    local OPENEULER_PKGS=(
        cmake gcc-c++ make
        log4cplus-devel cpp-httplib sqlite-devel
        jsoncpp-devel tinyxml2-devel openssl-devel
        zlib-devel brotli-devel re2-devel
        postgresql postgresql-server
        python3 python3-pip
        nodejs npm git curl nginx
    )

    local UBUNTU_PKGS=(
        cmake g++ make
        liblog4cplus-dev libcpp-httplib-dev libsqlite3-dev
        libjsoncpp-dev libtinyxml2-dev libssl-dev
        zlib1g-dev libbrotli-dev libre2-dev
        postgresql postgresql-client
        python3 python3-pip python3-venv
        nodejs npm git curl nginx
        libpam-systemd
    )

    if [ "$OS_ID" = "openeuler" ]; then
        if _is_root; then
            # systemd-pam (24.03+): pam_systemd.so 缺失 → systemctl --user 全不可用
            # 22.03 无此包 → 先探测存在才装, 避免 dnf 整批失败
            local SYSTEMD_PAM=""
            dnf list systemd-pam >/dev/null 2>&1 && SYSTEMD_PAM="systemd-pam"
            eval "$PM_UPDATE"
            eval "$PM_INSTALL ${OPENEULER_PKGS[*]} $SYSTEMD_PAM"
            systemctl enable postgresql 2>/dev/null || true
        else
            _warn "需要 root 权限安装系统包，请运行:"
            echo "  sudo dnf install -y ${OPENEULER_PKGS[*]}"
            _info "openEuler 24.03+ 另需 systemd-pam (systemctl --user 依赖):"
            echo "  sudo dnf install -y systemd-pam"
            _info "跳过系统包安装，假设已手动安装"
        fi
    elif [ "$OS_ID" = "ubuntu" ]; then
        if _is_root || _has_cmd sudo; then
            local SUDO=""
            _is_root || SUDO="sudo"
            eval "$SUDO $PM_UPDATE"
            eval "$SUDO $PM_INSTALL ${UBUNTU_PKGS[*]}"
        else
            _warn "需要 sudo 权限安装系统包，请运行:"
            echo "  sudo apt-get update && sudo apt-get install -y ${UBUNTU_PKGS[*]}"
            _info "跳过系统包安装，假设已手动安装"
        fi
    fi
}

# ──────────────────── Python 依赖 ────────────────────

install_python_deps() {
    _step_header "安装 Python 依赖"

    local LATENCY_DIR="$PROJECT_DIR/src/plugins/latency"
    local VENV_DIR="$LATENCY_DIR/.venv"

    # 依赖安装日志会写入 LOG_DIR; clean(scope 2)会删除该目录,
    # 不重建会让 tee 写日志失败 → pipefail 误判安装失败。
    # 另: root 跑过 install_deps.sh 后日志文件归 root, 普通用户
    # 再部署时 tee 无写权限同样误判 → 先删除旧日志再由 tee 重建。
    mkdir -p "$LOG_DIR"
    rm -f "$LOG_DIR/pip-install.log"

    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
    fi

    source "$VENV_DIR/bin/activate"
    # 升级既有依赖到 requirements 声明的版本（全新环境一次装好；
    # 旧环境避免因残留旧版 polars/numpy 导致 ImportError）。
    # tee 流式回显 + 留档: 依赖安装耗时最长, 静默会让部署看起来像假死。
    if ! pip install -U -r "$LATENCY_DIR/deploy/requirements.txt" 2>&1 | tee "$LOG_DIR/pip-install.log"; then
        _err "Python 依赖安装失败，最近日志:"
        tail -30 "$LOG_DIR/pip-install.log"
        return 1
    fi
    _log "Python 依赖安装完成"
}

# 独立执行入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    detect_os
    install_system_deps
    install_python_deps
fi
