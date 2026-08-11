#!/bin/bash
# witty-ub 前端启动器 (供 systemd user unit 调用)
#
# 策略:
#   - 存在非空 dist/ → vite preview 托管静态构建产物 (生产模式)
#   - 否则            → vite dev server (首次构建前 / 开发兜底)
#
# 使用 --strictPort: 5173 被占用时立即失败, 避免静默换端口。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WEB_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")/src/web"

cd "$WEB_DIR"

if [ -d dist ] && [ -n "$(ls -A dist 2>/dev/null)" ]; then
    exec ./node_modules/.bin/vite preview --host 0.0.0.0 --port 5173 --strictPort
fi

exec ./node_modules/.bin/vite --host 0.0.0.0 --port 5173 --strictPort
