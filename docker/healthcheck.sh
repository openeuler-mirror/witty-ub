#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.

# 角色感知健康检查:
#   all / backend  -> 本机 FastAPI 9772
#   frontend       -> 远端后端
#   all / frontend -> 经 Nginx 反代检查本机 experience-skill 的 SKILL/WIKI API
set -e

check_experience() {
    local exp_type
    for exp_type in SKILL WIKI; do
        curl -sf --max-time 2 --noproxy '*' -o /dev/null \
            "http://127.0.0.1:8080/experience_api/experiences?exp_type=${exp_type}&page_size=1" || return 1
    done
}

# 启动检查复用同一接口探测，暂不要求后端已就绪。
if [ "${1:-}" = "--experience" ]; then
    check_experience
    exit $?
fi

role="${WITTY_ROLE:-all}"
if [ "$role" = "frontend" ]; then
    curl -sf --max-time 2 --noproxy '*' "${WITTY_BACKEND_URL:-http://127.0.0.1:9772}/health_check"
else
    curl -sf --max-time 2 --noproxy 127.0.0.1 http://127.0.0.1:9772/health_check
fi
if [ "$role" = "all" ] || [ "$role" = "frontend" ]; then
    check_experience
fi
