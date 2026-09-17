#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# 旧入口: 既有 witty-ub-frontend.service 的 ExecStart 指向本文件, 转发到
# Vite 模式启动器, 使已安装的 systemd user unit 无需重装即可继续工作。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/run_frontend_vite.sh" "$@"
