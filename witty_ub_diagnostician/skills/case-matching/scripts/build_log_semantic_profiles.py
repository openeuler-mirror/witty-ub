#!/usr/bin/env python3
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
"""生成「案例 / 知识库 → 日志语义码轮廓」静态资产（case-matching Skill 兜底工具）。

状态（v2.6 起为兜底/回填工具，非主链路）
----------------------------------------
轮廓现已**随文档/案例持久化**：报告侧 `render_report.py` 生成文档时经
`POST /log_failure_event_result/log_semantic_profile` 写入 `basic_info.log_semantic_profile`；
确认建案时自动落到 `diag_case_library.log_semantic_profile` 并随 `/search` 返回；查询侧优先用
特征 JSON 内联轮廓、否则按 `kb_id` 现算。因此本脚本**不再是必需环节**，仅在以下场景使用：
  1. 回填/修复历史案例（案例库早于本改造、新列尚为空）；
  2. 为尚未重新入库的资产生成离线兜底资产（match_cases.py 在候选/查询两路都只在
     内联与现算都缺失时才回退到 references/log_semantic_profiles.json）。
抽取规则以后端 `services/log_semantic_profile.py` 为唯一权威，本脚本需与其保持一致。

用途
----
match_cases.py 的软打分有一条**次级排序通道** `log_semantic`：用查询侧与候选案例侧
「日志语义错误码轮廓」的 cosine 相似度做微弱加分（LOO 实证强化"硬件↔Worker"边界命名，
top1 66.5%→70.7%、K4 69.7%→70.7%）。本脚本把轮廓物化成
references/log_semantic_profiles.json 供 match_cases.py 兜底加载。

数据链路
--------
  diag_case_library(status=confirmed).report_id
    → reports/<report_id>.json 的 basic_info.kb_name
    → log_file.name → log_file.id (= log_id)
    → log_failure_event(level in E/W).message / raw_text
    → 语义错误码 `code: [NAME]`（如 [Not ready]、[Urma wait for completion timed out]）
      + 日志常量 token `[URMA_WAIT_TIMEOUT]`、`E2001` 等
    → 归一化单位向量轮廓

查询侧轮廓：match_cases.py 在运行时用 features.json 的 kb_name 在同一资产的
`by_kb_name` 里查；查不到则本次不启用该通道（对结果无副作用）。

依赖：psql（命令行客户端）+ 只读数据库账号。连接参数走环境变量
  PGHOST/PGPORT/PGUSER/PGDATABASE/PGPASSWORD（默认 127.0.0.1:15432 witty-ub/witty-ub，
  密码缺省从 <项目根>/deploy/pg.passwd 读取）。
报告目录走 WITTY_REPORT_DIR（默认 <项目根>/reports）。

用法:
  python3 build_log_semantic_profiles.py                 # 生成/刷新资产
  python3 build_log_semantic_profiles.py --dry-run       # 只统计不写文件
案例库有增删（新建/删除 confirmed 案例）后需重跑本脚本。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
OUT_PATH = os.path.join(SKILL_DIR, "references", "log_semantic_profiles.json")


def _project_root() -> str:
    """向上找到含 deploy/ 的项目根（默认 pg.passwd / reports 都相对它）。"""
    current = SCRIPT_DIR
    for _ in range(8):
        if os.path.isdir(os.path.join(current, "deploy")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.dirname(os.path.dirname(SKILL_DIR))


PROJECT_ROOT = _project_root()

# 语义错误码：日志原文 `code: [Not ready]` / `msg: [...]; code: [X]`
CODE_RE = re.compile(r"code:\s*\[([^\]]+)\]")
# 日志常量 token：全大写下划线标识符（URMA_WAIT_TIMEOUT / E2001 由单独规则收）
TOKEN_RE = re.compile(r"\b([A-Z][A-Z0-9_]{3,})\b")
ERRCODE_RE = re.compile(r"\bE\d{3,4}\b")
TOKEN_STOP = {"URMA", "RPC", "SHM", "UB", "TCP", "SLOW", "LOG", "ID"}

CODE_WEIGHT = 1.0
TOKEN_WEIGHT = 3.0
CODE_PREFIX = "C:"
TOKEN_PREFIX = "T:"


def _psql_path() -> str:
    found = shutil.which("psql")
    if found:
        return found
    for cand in ("/Users/zhaoyujin/miniconda3/bin/psql", "/usr/local/bin/psql", "/opt/homebrew/bin/psql"):
        if os.path.exists(cand):
            return cand
    raise SystemExit("未找到 psql，请安装 postgresql-client 或将其加入 PATH")


def _pg_env() -> dict:
    env = dict(os.environ)
    env.setdefault("PGHOST", "127.0.0.1")
    env.setdefault("PGPORT", "15432")
    env.setdefault("PGUSER", "witty-ub")
    env.setdefault("PGDATABASE", "witty-ub")
    if not env.get("PGPASSWORD"):
        pw_file = os.path.join(PROJECT_ROOT, "deploy", "pg.passwd")
        if os.path.exists(pw_file):
            env["PGPASSWORD"] = open(pw_file, encoding="utf-8").read().strip()
    return env


def q(sql: str) -> list[list[str]]:
    out = subprocess.run(
        [_psql_path(), "-tAF", "\x1f", "-c", sql],
        capture_output=True, text=True, env=_pg_env(), timeout=600,
    )
    if out.returncode != 0:
        raise SystemExit(f"SQL 执行失败: {out.stderr.strip()[:400]}")
    return [line.split("\x1f") for line in out.stdout.splitlines() if line]


def _normalize_vec(counter: Counter) -> dict[str, float]:
    norm = math.sqrt(sum(v * v for v in counter.values()))
    if not norm:
        return {}
    return {k: round(v / norm, 6) for k, v in counter.items()}


def extract_profile(messages: list[str]) -> dict[str, float]:
    """从 E/W 日志原文抽取语义码 + 常量 token 轮廓（单位向量）。"""
    counter: Counter = Counter()
    for msg in messages:
        if not msg:
            continue
        for code in CODE_RE.findall(msg):
            code = code.strip()
            if code:
                counter[CODE_PREFIX + code] += CODE_WEIGHT
        for token in TOKEN_RE.findall(msg):
            if token in TOKEN_STOP:
                continue
            counter[TOKEN_PREFIX + token] += TOKEN_WEIGHT
        for code in ERRCODE_RE.findall(msg):
            counter[TOKEN_PREFIX + code] += TOKEN_WEIGHT
    return _normalize_vec(counter)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只统计，不写资产文件")
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    reports_dir = os.environ.get("WITTY_REPORT_DIR") or os.path.join(PROJECT_ROOT, "reports")

    cases = q("select id, report_id from diag_case_library where status='confirmed';")
    print(f"confirmed 案例: {len(cases)}")
    name2log = {r[1]: r[0] for r in q("select id, name from log_file;")}
    print(f"log_file 条目: {len(name2log)}")

    report_kbname: dict[str, str] = {}
    for _, rid in cases:
        path = os.path.join(reports_dir, rid + ".json")
        if rid in report_kbname or not os.path.exists(path):
            continue
        try:
            payload = json.load(open(path, encoding="utf-8"))
            report_kbname[rid] = str((payload.get("basic_info") or {}).get("kb_name") or "")
        except (OSError, json.JSONDecodeError):
            report_kbname[rid] = ""

    case_log: list[tuple[str, str, str]] = []  # (case_id, log_id, kb_name)
    for cid, rid in cases:
        kb = report_kbname.get(rid, "")
        log_id = name2log.get(kb)
        if log_id:
            case_log.append((cid, log_id, kb))
    print(f"案例→log_id 映射成功: {len(case_log)} / {len(cases)}")

    log_ids = sorted({x[1] for x in case_log})
    inlist = ",".join("'%s'" % x for x in log_ids)
    rows = q(
        "select log_id, coalesce(message,''), coalesce(raw_text,'') "
        f"from log_failure_event where level in ('E','W') and log_id in ({inlist});"
    )
    print(f"E/W 日志事件行: {len(rows)}")
    msgs: dict[str, list[str]] = defaultdict(list)
    for log_id, message, raw in rows:
        msgs[log_id].append(message or raw)

    by_case_id: dict[str, dict[str, float]] = {}
    by_kb_name: dict[str, dict[str, float]] = {}
    by_log_id: dict[str, dict[str, float]] = {}
    n_with_profile = 0
    for cid, log_id, kb in case_log:
        vec = extract_profile(msgs.get(log_id, []))
        if not vec:
            continue
        n_with_profile += 1
        by_case_id[cid] = vec
        by_kb_name.setdefault(kb, vec)
        by_log_id.setdefault(log_id, vec)
    print(f"有语义轮廓的案例: {n_with_profile}；kb_name 索引: {len(by_kb_name)}；log_id 索引: {len(by_log_id)}")

    if args.dry_run:
        print("dry-run，未写文件")
        return
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(
        {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "log_failure_event(E/W) 语义错误码 + 日志常量 token 轮廓；单位向量",
            "code_weight": CODE_WEIGHT,
            "token_weight": TOKEN_WEIGHT,
            "by_case_id": by_case_id,
            "by_kb_name": by_kb_name,
            "by_log_id": by_log_id,
        },
        open(args.out, "w", encoding="utf-8"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    print(f"已写入 {args.out}（{os.path.getsize(args.out) / 1024:.0f} KB）")


if __name__ == "__main__":
    sys.exit(main())
