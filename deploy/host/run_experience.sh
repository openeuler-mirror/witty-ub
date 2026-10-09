#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# experience-skill Web 服务启动器（知识库 Skill/Wiki 管理 API）
#
# 启动 experience-skill 的 Web 管理服务，提供 Skill 和 Wiki 的 CRUD API。
# 端口默认 8082，避免与 Nginx(8080) 和试验性前端(8081) 冲突。
#
# 被 deploy.sh 以 nohup 调用，也可直接执行：
#   bash deploy/host/run_experience.sh
#
# 环境变量:
#   EXPERIENCE_HOST   监听地址 (默认 0.0.0.0)
#   EXPERIENCE_PORT   监听端口 (默认 8082)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

EXPERIENCE_SKILL_DIR="$PROJECT_DIR/witty_ub_diagnostician/skills/experience-skill/scripts"
EXPERIENCE_PORT="${EXPERIENCE_PORT:-8082}"
EXPERIENCE_HOST="${EXPERIENCE_HOST:-0.0.0.0}"

if [ ! -d "$EXPERIENCE_SKILL_DIR" ]; then
    echo "[error] experience-skill 目录不存在: $EXPERIENCE_SKILL_DIR" >&2
    echo "[error] 请先运行: bash deploy/host/install_deps.sh" >&2
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "[error] uv 未安装。请先运行: bash deploy/host/install_deps.sh" >&2
    exit 1
fi

if [ ! -d "$EXPERIENCE_SKILL_DIR/.venv" ]; then
    echo "[error] experience-skill 虚拟环境不存在。请先运行: bash deploy/host/install_deps.sh" >&2
    exit 1
fi

# root 部署时切到仓库属主，避免 venv / DB 文件变 root 所有导致权限问题。
# 使用 exec runuser 替换当前进程，使 PID 文件指向 runuser（kill 时能传播到子进程）。
_owner="$(stat -c '%U' "$PROJECT_DIR" 2>/dev/null || true)"
_owner_home="$(getent passwd "$_owner" 2>/dev/null | cut -d: -f6 || true)"

if [ "$(id -u)" -eq 0 ] && [ -n "$_owner" ] && [ "$_owner" != "root" ] \
    && [ -n "$_owner_home" ] && command -v runuser >/dev/null 2>&1; then
    exec runuser -u "$_owner" -- env HOME="$_owner_home" \
        PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
        bash -c "cd '$EXPERIENCE_SKILL_DIR' && uv run experience-skill sync && exec uv run experience-skill web --host $EXPERIENCE_HOST --port $EXPERIENCE_PORT --no-browser"
fi

cd "$EXPERIENCE_SKILL_DIR"
uv run experience-skill sync
exec uv run experience-skill web --host "$EXPERIENCE_HOST" --port "$EXPERIENCE_PORT" --no-browser
