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

    local RPM_PKGS=(
        cmake gcc-c++ make
        log4cplus-devel cpp-httplib sqlite-devel
        jsoncpp-devel tinyxml2-devel openssl-devel
        zlib-devel brotli-devel re2-devel
        postgresql postgresql-server
        python3 python3-pip
        nodejs npm git curl nginx
    )

    local APT_PKGS=(
        cmake g++ make
        liblog4cplus-dev libcpp-httplib-dev libsqlite3-dev
        libjsoncpp-dev libtinyxml2-dev libssl-dev
        zlib1g-dev libbrotli-dev libre2-dev
        postgresql postgresql-client
        python3 python3-pip python3-venv
        # 本机 nodejs 由 NodeSource 安装(Conflicts/Provides: npm, 自带 npm),
        # 发行版 npm 包无法共存, 故跳过这两个已满足的包。
        git curl nginx
        libpam-systemd
    )

    if [ "$OS_ID" = "rpm" ]; then
        if _is_root || _has_cmd sudo; then
            # 与 apt 分支对称: 非 root 但有 sudo 时同样执行安装, 否则
            # 会静默跳过全部系统依赖, 之后 cmake/g++ 缺失才在编译期报错。
            local SUDO_CMD=()
            _is_root || SUDO_CMD=(sudo)
            # systemd-pam (24.03+): pam_systemd.so 缺失 → systemctl --user 全不可用
            # 22.03 无此包 → 先探测存在才装, 避免 dnf 整批失败
            local SYSTEMD_PAM=""
            dnf list systemd-pam >/dev/null 2>&1 && SYSTEMD_PAM="systemd-pam"
            [ -n "$SYSTEMD_PAM" ] && RPM_PKGS+=("$SYSTEMD_PAM")
            "${SUDO_CMD[@]}" $PM_INSTALL "${RPM_PKGS[@]}"
            "${SUDO_CMD[@]}" systemctl enable postgresql 2>/dev/null || true
        else
            _warn "需要 root/sudo 权限安装系统包，请运行:"
            echo "  sudo $PM_INSTALL ${RPM_PKGS[*]}"
            _info "跳过系统包安装，假设已手动安装"
        fi
    elif [ "$OS_ID" = "apt" ]; then
        if _is_root || _has_cmd sudo; then
            local SUDO_CMD=()
            _is_root || SUDO_CMD=(sudo)
            "${SUDO_CMD[@]}" $PM_UPDATE
            "${SUDO_CMD[@]}" $PM_INSTALL "${APT_PKGS[@]}"
        else
            _warn "需要 sudo 权限安装系统包，请运行:"
            echo "  sudo apt-get update && sudo apt-get install -y ${APT_PKGS[*]}"
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

# ──────────────────── Agent (OpenCode) 运行时依赖 ────────────────────
# Agent 技能全部走 `uv run experience-skill ...` 检索经验库，缺 uv / 缺分词器 /
# 没 sync 都会让它卡在 "uv: command not found" 或检索为空。
# 容器镜像装过这套（Dockerfile.base），宿主机部署此前没有。

install_uv_if_missing() {
    local pip_index="${WITTY_PIP_INDEX:-https://mirrors.aliyun.com/pypi/simple/}"

    if _has_cmd uv; then
        _normalize_uv_path
        _log "uv 已就绪: $(command -v uv) ($(uv --version 2>/dev/null | head -n1))"
        return 0
    fi

    _info "安装 uv（Agent 技能依赖）..."
    if _is_root || _has_cmd sudo; then
        local SUDO_CMD=()
        _is_root || SUDO_CMD=(sudo)
        # openEuler 24.03 需 --break-system-packages；老 pip 不认则该参数回退
        "${SUDO_CMD[@]}" python3 -m pip install -U -i "$pip_index" uv --break-system-packages \
            >/dev/null 2>&1 \
            || "${SUDO_CMD[@]}" python3 -m pip install -U -i "$pip_index" uv \
            || true

        # pip 认为依赖已满足时不会补回丢失的 console script → 强制重装
        if ! _has_cmd uv; then
            "${SUDO_CMD[@]}" python3 -m pip install --force-reinstall --no-deps \
                -i "$pip_index" uv --break-system-packages >/dev/null 2>&1 \
                || "${SUDO_CMD[@]}" python3 -m pip install --force-reinstall --no-deps \
                    -i "$pip_index" uv >/dev/null 2>&1 \
                || true
        fi

        # astral 脚本装到 ~/.local/bin，服务 PATH 看不到 → 补 /usr/local/bin
        if ! _has_cmd uv && [ -x "$HOME/.local/bin/uv" ]; then
            "${SUDO_CMD[@]}" ln -sf "$HOME/.local/bin/uv" /usr/local/bin/uv || true
        fi
        if ! _has_cmd uv && _has_cmd curl; then
            _info "pip 安装失败，回退 astral 安装脚本..."
            curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1 || true
            [ -x "$HOME/.local/bin/uv" ] \
                && "${SUDO_CMD[@]}" ln -sf "$HOME/.local/bin/uv" /usr/local/bin/uv || true
        fi
    fi

    _normalize_uv_path

    if ! _has_cmd uv; then
        _err "uv 安装失败。Agent 技能会全部报 'uv: command not found'，请手动安装:"
        echo "  sudo python3 -m pip install -i $pip_index uv --break-system-packages"
        return 1
    fi
    _log "uv 安装完成: $(command -v uv)"
}

# Agent 以普通用户运行，PATH 只有 /usr/local/{s,}bin:/usr/sbin:/usr/bin，
# uv 若落在 ~/.local/bin（或 /root/...）必须复制到 /usr/local/bin
_uv_usable_by_others() {
    local target="$1" real
    [ -x "$target" ] || return 1
    real="$(readlink -f "$target" 2>/dev/null || echo "$target")"
    case "$real" in
        /usr/local/bin/* | /usr/bin/*) return 0 ;;
    esac
    return 1
}

_normalize_uv_path() {
    local uv_bin
    uv_bin="$(command -v uv 2>/dev/null || true)"

    _uv_usable_by_others /usr/local/bin/uv && return 0
    [ -n "$uv_bin" ] || return 0

    if _is_root || _has_cmd sudo; then
        local SUDO_CMD=()
        _is_root || SUDO_CMD=(sudo)
        if [ "$uv_bin" != "/usr/local/bin/uv" ]; then
            "${SUDO_CMD[@]}" rm -f /usr/local/bin/uv || true
            "${SUDO_CMD[@]}" install -m 0755 "$uv_bin" /usr/local/bin/uv || true
        fi
    fi
}

# 在指定目录执行 skill 命令；root 运行时切到仓库属主，避免产物变 root 所有
_run_skill_cmd() {
    local workdir="$1" snippet="$2"
    local owner owner_home
    owner="$(stat -c '%U' "$PROJECT_DIR" 2>/dev/null || true)"
    owner_home="$(getent passwd "$owner" 2>/dev/null | cut -d: -f6 || true)"

    if _is_root && [ -n "$owner" ] && [ "$owner" != "root" ] \
        && [ -n "$owner_home" ] && _has_cmd runuser; then
        # 用服务侧 PATH，避免带上只有 root 能进的目录（如 /root/.local/bin）
        runuser -u "$owner" -- env HOME="$owner_home" \
            PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
            bash -c "cd '$workdir' && $snippet"
    else
        (cd "$workdir" && eval "$snippet")
    fi
}

install_experience_skill_deps() {
    local SKILL_DIR="$PROJECT_DIR/witty_ub_diagnostician/skills/experience-skill"
    local SCRIPTS_DIR="$SKILL_DIR/scripts"
    local TOKENIZER_DIR="$SCRIPTS_DIR/src/experience_skill_cli/tokenizer"

    if [ ! -d "$SCRIPTS_DIR" ]; then
        _warn "未找到 experience-skill（$SCRIPTS_DIR），跳过 Agent 技能依赖"
        return 0
    fi

    mkdir -p "$LOG_DIR"

    # 1) simple FTS5 分词器（缺失时 CLI 直接报错）
    if [ ! -e "$TOKENIZER_DIR/libsimple" ] && [ ! -e "$TOKENIZER_DIR/libsimple.so" ]; then
        _info "编译 simple 分词器扩展 (libsimple)..."
        # 重定向放在 root 侧：日志目录可能属 root
        if ! _run_skill_cmd "$TOKENIZER_DIR" "bash build.sh" \
            >"$LOG_DIR/tokenizer-build.log" 2>&1; then
            _err "分词器编译失败，最近日志:"
            tail -20 "$LOG_DIR/tokenizer-build.log" 2>/dev/null || true
            return 1
        fi
    fi

    # 2) uv sync 建 .venv
    if [ ! -d "$SCRIPTS_DIR/.venv" ]; then
        _info "初始化 experience-skill 虚拟环境 (uv sync)..."
        if ! _run_skill_cmd "$SCRIPTS_DIR" "uv sync" >"$LOG_DIR/uv-sync.log" 2>&1; then
            _err "uv sync 失败，完整日志: $LOG_DIR/uv-sync.log"
            tail -20 "$LOG_DIR/uv-sync.log" 2>/dev/null || true
            return 1
        fi
    fi

    # 3) 同步经验库（幂等），否则检索恒为 0 条
    _info "同步本地经验库 (experience-skill sync)..."
    if ! _run_skill_cmd "$SCRIPTS_DIR" "uv run experience-skill sync"; then
        _err "经验库同步失败，Agent 检索会返回空结果"
        return 1
    fi
    return 0
}

install_agent_deps() {
    _step_header "安装 Agent (OpenCode) 运行时依赖"
    install_uv_if_missing || return 1
    install_experience_skill_deps || return 1
    _log "Agent 运行时依赖就绪 (uv + experience-skill + 经验库)"
}

# ──────────────────── 组合入口 ────────────────────

# deploy.sh 菜单「安装依赖」入口：系统依赖 + Python 依赖 + Agent 运行时依赖
install_deps() {
    detect_os
    install_system_deps
    install_python_deps
    install_agent_deps
}

# 独立执行入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    install_deps
fi
