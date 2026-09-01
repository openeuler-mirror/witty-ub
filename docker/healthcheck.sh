#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.

# 角色感知健康检查:
#   all / backend  -> 本机 FastAPI 9772
#   frontend       -> 经 Nginx 反代探测远端后端
role="${WITTY_ROLE:-all}"
if [ "$role" = "frontend" ]; then
    exec curl -sf --noproxy '*' "${WITTY_BACKEND_URL:-http://127.0.0.1:9772}/health_check"
else
    exec curl -sf --noproxy 127.0.0.1 http://127.0.0.1:9772/health_check
fi
