#!/bin/bash

set -e

cleanup() {
    [ -z "${MCP_PID:-}" ] || kill "$MCP_PID" 2>/dev/null || true
    [ -z "${RAG_PID:-}" ] || kill "$RAG_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

/bin/bash /rag-service/run.sh &
RAG_PID=$!

for _ in $(seq 1 120); do
    if curl -fsS http://127.0.0.1:9988/health_check >/dev/null 2>&1; then
        break
    fi
    if ! kill -0 "$RAG_PID" 2>/dev/null; then
        echo "[ERROR] RAG Core exited before becoming healthy" >&2
        wait "$RAG_PID"
        exit 1
    fi
    sleep 2
done

if ! curl -fsS http://127.0.0.1:9988/health_check >/dev/null 2>&1; then
    echo "[ERROR] RAG Core did not become healthy; MCP will not start" >&2
    exit 1
fi

echo "[INFO] Starting RAG MCP SSE service on 0.0.0.0:12312"
MCP_RUNTIME_DIR=/rag-service/rag_core/agent/rag_core_mcp
mkdir -p "$MCP_RUNTIME_DIR"
cp -a /opt/witty-rag-mcp-source/. "$MCP_RUNTIME_DIR/"
test -f "$MCP_RUNTIME_DIR/tools/access_key.py"
cd "$MCP_RUNTIME_DIR"
: >/rag-service/logs/rag-mcp.log
RAG_CORE_BASE_URL=http://127.0.0.1:9988 \
RAG_CORE_MCP_HOST=0.0.0.0 \
RAG_CORE_MCP_PORT=12312 \
    python3 server.py >>/rag-service/logs/rag-mcp.log 2>&1 &
MCP_PID=$!

while kill -0 "$RAG_PID" 2>/dev/null && kill -0 "$MCP_PID" 2>/dev/null; do
    sleep 5
done

echo "[ERROR] RAG Core or RAG MCP exited unexpectedly" >&2
exit 1
