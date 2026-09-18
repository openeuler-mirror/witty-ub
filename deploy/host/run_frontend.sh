#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# 前端入口（旧入口 + 两种模式分发）。
#
# 旧入口: 既有 witty-ub-frontend.service 的 ExecStart 指向本文件, 默认转发到
# Vite 模式启动器, 使已安装的 systemd user unit 无需重装即可继续工作。
# Nginx 模式: WITTY_FRONTEND_MODE=nginx, 或首个参数为 nginx / --nginx 时转发到
# run_frontend_nginx.sh (静态托管 dist/ + 反代, port 8080, 需 nginx 与 sudo)。
# 其余参数原样透传给被调用的启动器。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FRONTEND_MODE="${WITTY_FRONTEND_MODE:-vite}"
case "${1:-}" in
    nginx | --nginx)
        FRONTEND_MODE="nginx"
        shift
        ;;
esac

if [ "$FRONTEND_MODE" = "nginx" ]; then
    exec bash "$SCRIPT_DIR/run_frontend_nginx.sh" "$@"
fi

# Vite 模式: 启动前把"起不来"的原因说清楚。原先依赖缺失时只有一句
#   ./node_modules/.bin/vite: No such file or directory  (exit 127)
# 用户完全不知道下一步该干什么。
WEB_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")/src/web"
LOG_DIR="${LOG_DIR:-${WITTY_DIR:-/var/witty-ub}/logs}"

if ! command -v node >/dev/null 2>&1; then
    echo "[error] 找不到 node。请先安装 Node.js >= 20.19（前端构建与预览都需要它）" >&2
    exit 1
fi
if [ ! -x "$WEB_DIR/node_modules/.bin/vite" ]; then
    echo "[error] 前端依赖未安装：$WEB_DIR/node_modules/.bin/vite 不存在" >&2
    echo "[error] 请先执行：cd $WEB_DIR && npm install" >&2
    echo "[error] 若是通过 deploy.sh 部署，请检查 $LOG_DIR/frontend-build.log（npm install 失败会被明确报出）" >&2
    exit 1
fi

exec bash "$SCRIPT_DIR/run_frontend_vite.sh" "$@"
