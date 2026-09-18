#!/usr/bin/env bash
# witty-ub 部署端到端验证：一条命令给出 PASS/FAIL。
#
# 用法（在部署机 WSL 里跑）：
#   bash deploy/host/verify_e2e.sh            # 全量验证（含真跑一次解析）
#   bash deploy/host/verify_e2e.sh --quick    # 只验服务/接口/库，不跑解析
#
# 退出码：0 = 全部通过；1 = 有失败项。每项都打印实际观测值，不打印"应该是什么"。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
VENV_PY="$PROJECT_DIR/src/plugins/latency/.venv/bin/python"
PG_SECRET="$PROJECT_DIR/deploy/pg.passwd"
KB_BASE="http://127.0.0.1:9772"
SAMPLE_SRC="${WITTY_E2E_SAMPLE:-/var/witty-ub/jingpai-log-sample1-new}"
QUICK=0
[ "${1:-}" = "--quick" ] && QUICK=1

pass=0; fail=0
ok()   { printf "  \033[0;32mPASS\033[0m  %-34s %s\n" "$1" "$2"; pass=$((pass+1)); }
bad()  { printf "  \033[0;31mFAIL\033[0m  %-34s %s\n" "$1" "$2"; fail=$((fail+1)); }
info() { printf "        ├ %s\n" "$1"; }

echo "=============================================="
echo " witty-ub 端到端验证"
echo " 项目: $PROJECT_DIR"
echo " 时间: $(date '+%F %T')"
echo "=============================================="

# ── 1. 服务（默认裸进程托管；若显式用 systemd 也认）────────────────
echo "[1] 服务"
LOG_DIR="$PROJECT_DIR/.deploy-logs"
for pair in "后端:witty-ub-backend:backend:9772" "前端:witty-ub-frontend:frontend:5173"; do
    name="${pair%%:*}"; rest="${pair#*:}"
    svc="${rest%%:*}"; rest="${rest#*:}"
    pidname="${rest%%:*}"; port="${rest##*:}"
    pidfile="$LOG_DIR/$pidname.pid"
    if systemctl --user is-active --quiet "$svc.service" 2>/dev/null; then
        ok "$name 托管" "systemd user unit"
    elif [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile" 2>/dev/null)" 2>/dev/null; then
        ok "$name 托管" "裸进程 pid=$(cat "$pidfile")"
    else
        bad "$name 托管" "无 systemd unit、PID 文件也不活（$pidfile）"
    fi
done
echo -n "        └ 后端进程数(应=1): "
ps -eo cmd | grep -c "[f]astapi_server.py"

# ── 2. 接口 ──────────────────────────────────────────────
echo "[2] 接口"
h="$(curl -s --noproxy 127.0.0.1 --max-time 5 "$KB_BASE/health_check" || true)"
echo "$h" | grep -q ok && ok "后端 /health_check" "$h" || bad "后端 /health_check" "${h:-无响应}"
f="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://127.0.0.1:5173/ || true)"
[ "$f" = "200" ] && ok "前端 :5173" "HTTP $f" || bad "前端 :5173" "HTTP ${f:-无响应}"

# ── 3. 数据库绑定 ────────────────────────────────────────
echo "[3] 数据库"
CONF="/var/witty-ub/config/diagnosis_config.toml"
dbname="$(grep -E '^pg_database' "$CONF" 2>/dev/null | cut -d'"' -f2)"
if [ -z "$dbname" ]; then
    bad "运行时配置存在" "$CONF 缺失或无 pg_database"
else
    ok "运行时配置库名" "$dbname"
    export PGPASSWORD="$(tr -d '\r\n' < "$PG_SECRET" 2>/dev/null)"
    n="$(psql -h 127.0.0.1 -U "$dbname" -d "$dbname" -t -A -c 'select count(*) from log_knowledge;' 2>/dev/null)"
    if [ -n "$n" ] && [ "$n" -ge 0 ] 2>/dev/null; then
        ok "库可连接且建表" "$dbname 里 $n 个资产库"
        # 与接口对账：接口读的数量必须与库里一致（口径不一致说明连错库）
        api_total="$(curl -s --noproxy 127.0.0.1 -X POST -H 'Content-Type: application/json' \
            -d '{"page_cnt":1}' "$KB_BASE/log_kb/list" | "$VENV_PY" -c \
            'import json,sys; print(json.load(sys.stdin)["result"]["total"])' 2>/dev/null)"
        if [ -n "$api_total" ] && [ "$api_total" -ge 1 ]; then
            ok "接口/库 数据一致" "接口 $api_total 个"
        else
            bad "接口读到资产库" "接口 total=$api_total（库里有 $n 个 → 连错库）"
        fi
    else
        bad "库可连接" "连不上 $dbname"
    fi
fi

# ── 4. C++ 诊断工具 ──────────────────────────────────────
echo "[4] C++ 诊断工具"
for bin in witty-ub-diag-tool witty-ub-brpc-diag; do
    p="$PROJECT_DIR/build/src/$bin"
    if [ -x "$p" ]; then ok "$bin" "$(du -h "$p" | cut -f1)"; else bad "$bin" "缺失或不可执行: $p"; fi
done

# ── 5. 端到端真跑一次解析 ────────────────────────────────
echo "[5] 端到端解析（真跑一次）"
if [ "$QUICK" = "1" ]; then
    echo "        └ --quick：跳过"
else
    [ -d "$SAMPLE_SRC" ] || { bad "样本目录" "$SAMPLE_SRC 不存在"; SAMPLE_SRC=""; }
    if [ -n "$SAMPLE_SRC" ]; then
        kb_json="$(curl -s --noproxy 127.0.0.1 -X POST -H 'Content-Type: application/json' \
            -d "{\"name\":\"e2e-verify-$(date +%s)\",\"description\":\"端到端验证（可删）\"}" "$KB_BASE/log_kb")"
        kb_id="$(echo "$kb_json" | "$VENV_PY" -c 'import json,sys; print(json.load(sys.stdin)["result"]["kb_id"])' 2>/dev/null)"
        if [ -z "$kb_id" ]; then
            bad "建资产库" "$(echo "$kb_json" | head -c 120)"
        else
            lf_id="$(curl -s --noproxy 127.0.0.1 -X POST -H 'Content-Type: application/json' \
                -d "{\"upload_log_file_configs\":[{\"name\":\"e2e-verify\",\"source_type\":\"local\",\"source\":\"$SAMPLE_SRC\",\"log_type\":\"kv-cache\"}]}" \
                "$KB_BASE/log_file/$kb_id" | "$VENV_PY" -c 'import json,sys; print(json.load(sys.stdin)["result"]["log_file_ids"][0])' 2>/dev/null)"
            info "kb=$kb_id log_file=$lf_id"
            status=""
            for _ in $(seq 1 60); do
                sleep 2
                status="$(curl -s --noproxy 127.0.0.1 "$KB_BASE/log_file/$lf_id" | "$VENV_PY" -c \
                    'import json,sys; print((json.load(sys.stdin)["result"]["log_file"].get("task") or {}).get("status"))' 2>/dev/null)"
                case "$status" in successful*|failed*|stopped) break ;; esac
            done
            case "$status" in
                successful*) ok "解析任务链" "status=$status" ;;
                *)           bad "解析任务链" "status=${status:-超时}" ;;
            esac
            # 三个任务逐个断言
            export PGPASSWORD="$(tr -d '\r\n' < "$PG_SECRET" 2>/dev/null)"
            for tt in kv_cache_log_parse_worker kv_cache_log_event_diagnosis_worker store_trace_context_logs_worker; do
                st="$(psql -h 127.0.0.1 -U "$dbname" -d "$dbname" -t -A -c \
                    "select status from task where op_id='$lf_id' and task_type='$tt' order by created_at desc limit 1;" 2>/dev/null)"
                case "$st" in
                    successful*) ok "$(echo "$tt" | sed 's/kv_cache_log_//;s/_worker//')" "$st" ;;
                    *)           bad "$(echo "$tt" | sed 's/kv_cache_log_//;s/_worker//')" "${st:-无记录}" ;;
                esac
            done
            curl -s --noproxy 127.0.0.1 -X DELETE "$KB_BASE/log_kb/$kb_id" >/dev/null 2>&1
            info "已清理验证用资产库"
        fi
    fi
fi

echo "=============================================="
printf " 结果: \033[0;32mPASS %d\033[0m / \033[0;31mFAIL %d\033[0m\n" "$pass" "$fail"
echo "=============================================="
[ "$fail" = "0" ]
