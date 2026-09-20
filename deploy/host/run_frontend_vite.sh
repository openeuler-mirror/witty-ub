#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# witty-ub 前端 Web 入口（Vite 模式）
#   存在非空 dist/ 时用 vite preview 托管构建产物, 否则回退 vite dev server;
#   监听 5173, 不需要 root。API/Agent 反代由 src/web/vite.config.ts 的 server.proxy
#   提供 (preview 继承该配置), 上游取自 VITE_DEV_API_TARGET / VITE_DEV_AGENT_TARGET。
#   Nginx 模式见 run_frontend_nginx.sh。
#
# 使用 --strictPort: 5173 被占用时立即失败, 不静默换端口。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WEB_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")/src/web"

cd "$WEB_DIR"

if [ -d dist ] && [ -n "$(ls -A dist 2>/dev/null)" ]; then
    exec ./node_modules/.bin/vite preview --host 0.0.0.0 --port 5173 --strictPort
fi

exec ./node_modules/.bin/vite --host 0.0.0.0 --port 5173 --strictPort
