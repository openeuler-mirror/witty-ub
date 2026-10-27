#!/bin/bash
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
#
# 源码/RPM 部署：为宿主机后端准备 RAG（openGauss + RAG Core），并写出运行时环境文件。
#
# 容器编排复用 deploy/docker/deploy_rag.sh；本脚本只负责源码部署特有的三件事：
#   1) 把密钥放到部署用户可读的项目内路径（默认 .deploy-run/rag-secrets），不依赖 /etc 写权限；
#   2) 生成 .deploy-run/rag.env，供 run_backend.sh 与 systemd unit 注入后端；
#   3) 校验/创建现象检索专用知识库并写回 RAG_PHENOMENON_KB_ID。
#
# 用法:
#   bash deploy/host/deploy_rag.sh              # 部署并写出环境文件
#   bash deploy/host/deploy_rag.sh --env-only   # 只重新生成环境文件，不动容器
#
# 配置来源: 环境变量 > deploy/deploy.conf > .deploy-run/rag.local.env（机器本地，不入库）
#
# 环境变量:
#   WITTY_RAG_ENABLE=auto|1|0   是否部署 RAG（默认 auto：有容器运行时即部署）
#   RAG_EMBEDDING_ENDPOINT      完整 /v1/embeddings 地址
#   RAG_EMBEDDING_MODEL_NAME    端点上的模型名
#   RAG_EMBEDDING_DIMENSION     向量维度上限
#   RAG_EMBEDDING_API_KEY       API Key，可留空
#   RAG_RERANK_ENABLED          是否启用 rerank（默认 0）
#   RAG_MIN_SCORE / RAG_TOP_K   检索阈值与召回数（透传给后端）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
source "$SCRIPT_DIR/_lib.sh"

RUN_DIR="${WITTY_RUN_DIR:-$PROJECT_DIR/.deploy-run}"
RAG_ENV_FILE="$RUN_DIR/rag.env"
# 机器本地覆盖：不随仓库分发，用于放本机的 embedding 端点等私有取值。
RAG_LOCAL_ENV="$RUN_DIR/rag.local.env"
RAG_SECRET_DIR="$RUN_DIR/rag-secrets"
RAG_DB_SECRET_FILE="${RAG_DB_SECRET_FILE:-$RAG_SECRET_DIR/opengauss.passwd}"
RAG_ACCESS_KEY_SECRET_FILE="${RAG_ACCESS_KEY_SECRET_FILE:-$RAG_SECRET_DIR/access-key}"
KB_FILE="$RUN_DIR/rag-phenomenon-kb"
PYTHON="$PROJECT_DIR/src/plugins/latency/.venv/bin/python"
ENV_ONLY=0
[ "${1:-}" = "--env-only" ] && ENV_ONLY=1

# 机器本地覆盖先加载并导出，让后续默认值判断与子脚本都看到本机取值。
if [ -f "$RAG_LOCAL_ENV" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$RAG_LOCAL_ENV"
    set +a
fi

CONTAINER_CLI=""
for _cli in docker podman; do
    _has_cmd "$_cli" && { CONTAINER_CLI="$_cli"; break; }
done

case "${WITTY_RAG_ENABLE:-auto}" in
0 | false | FALSE | no) _info "WITTY_RAG_ENABLE=0，跳过 RAG"; exit 0 ;;
esac
if [ -z "$CONTAINER_CLI" ]; then
    _warn "未找到 docker/podman，跳过 RAG（语义检索不可用）"
    exit 0
fi

mkdir -p "$RUN_DIR" "$RAG_SECRET_DIR"
chmod 0700 "$RAG_SECRET_DIR"

# openGauss 口令由部署生成一次并复用；格式与容器部署一致。
if [ ! -s "$RAG_DB_SECRET_FILE" ]; then
    _db_password="Og$(head -c 32 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 12)9#$(head -c 16 /dev/urandom | base64 | tr -dc 'a-z' | head -c 4)"
    (umask 077 && printf '%s' "$_db_password" >"$RAG_DB_SECRET_FILE")
    unset _db_password
    _info "已生成 openGauss 口令: $RAG_DB_SECRET_FILE"
fi
chmod 0600 "$RAG_DB_SECRET_FILE"

export RAG_DB_SECRET_FILE RAG_ACCESS_KEY_SECRET_FILE
export WITTY_RAG_CORE_HOST_PORT="${WITTY_RAG_CORE_HOST_PORT:-9990}"
# 源码部署不以 root 运行：配置与日志落在项目内，避免依赖 /opt 写权限。
export RAG_RUNTIME_DIR="${RAG_RUNTIME_DIR:-$RUN_DIR/rag-runtime}"

if [ "$ENV_ONLY" -eq 0 ]; then
    _info "部署 RAG 容器（openGauss + RAG Core）..."
    if ! RAG_ACCESS_KEY_SECRET_FILE="$RAG_ACCESS_KEY_SECRET_FILE" \
        RAG_DB_SECRET_FILE="$RAG_DB_SECRET_FILE" \
        bash "$PROJECT_DIR/deploy/docker/deploy_rag.sh"; then
        _err "RAG 部署失败；后端将以「语义检索不可用」运行"
        exit 1
    fi
fi

if [ ! -s "$RAG_ACCESS_KEY_SECRET_FILE" ]; then
    _err "RAG 访问密钥缺失: $RAG_ACCESS_KEY_SECRET_FILE"
    exit 1
fi
chmod 0600 "$RAG_ACCESS_KEY_SECRET_FILE"

RAG_CORE_URL="${RAG_CORE_URL:-http://127.0.0.1:${WITTY_RAG_CORE_HOST_PORT}}"
export RAG_CORE_URL
export RAG_ACCESS_KEY_FILE="$RAG_ACCESS_KEY_SECRET_FILE"

# 专用知识库：优先环境变量，其次落盘文件；都无效时用 CLI 创建并回写。
if [ -z "${RAG_PHENOMENON_KB_ID:-}" ] && [ -s "$KB_FILE" ]; then
    RAG_PHENOMENON_KB_ID="$(tr -d '\r\n' <"$KB_FILE")"
fi
if [ ! -x "$PYTHON" ]; then
    _warn "后端 venv 不存在: $PYTHON，跳过知识库初始化"
else
    # CLI 需要能 import latency 包；已记录 KB 时由它校验而不是再建一个新的。
    export PYTHONPATH="$PROJECT_DIR/src/plugins${PYTHONPATH:+:$PYTHONPATH}"
    export RAG_PHENOMENON_KB_ID="${RAG_PHENOMENON_KB_ID:-}"
    _kb_out="$("$PYTHON" -m latency.access.phenomenon_cli --init-kb \
        --kb-name witty-ub-phenomenon 2>/dev/null)" || _kb_out=""
    _kb_id="$(printf '%s' "$_kb_out" | "$PYTHON" -c 'import json,sys
try:
    print(json.load(sys.stdin).get("kb_id") or "")
except Exception:
    print("")' 2>/dev/null)"
    if [ -n "$_kb_id" ]; then
        RAG_PHENOMENON_KB_ID="$_kb_id"
        (umask 077 && printf '%s' "$_kb_id" >"$KB_FILE")
    else
        _warn "现象检索知识库不可用（RAG 未就绪？），语义检索将关闭"
    fi
fi

if [ -n "${RAG_PHENOMENON_KB_ID:-}" ]; then
    (umask 077 && cat >"$RAG_ENV_FILE" <<EOF
# 由 deploy/host/deploy_rag.sh 生成；后端启动时加载。
RAG_CORE_URL=$RAG_CORE_URL
RAG_ACCESS_KEY_FILE=$RAG_ACCESS_KEY_FILE
RAG_PHENOMENON_KB_ID=$RAG_PHENOMENON_KB_ID
PHENOMENON_INDEX_ENABLED=${PHENOMENON_INDEX_ENABLED:-true}
PHENOMENON_SEARCH_ENABLED=${PHENOMENON_SEARCH_ENABLED:-true}
RAG_MIN_SCORE=${RAG_MIN_SCORE:-}
RAG_TOP_K=${RAG_TOP_K:-}
EOF
    )
    _log "RAG 已就绪: $RAG_CORE_URL, KB=$RAG_PHENOMENON_KB_ID"
    _info "后端环境文件: $RAG_ENV_FILE"
else
    (umask 077 && cat >"$RAG_ENV_FILE" <<EOF
# 由 deploy/host/deploy_rag.sh 生成；RAG 不可用，语义检索关闭。
PHENOMENON_INDEX_ENABLED=false
PHENOMENON_SEARCH_ENABLED=false
EOF
    )
    _warn "已写入 $RAG_ENV_FILE，现象索引与语义检索保持关闭"
fi
