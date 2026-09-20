#!/usr/bin/env python3
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
"""历史案例检索脚本（case-matching Skill 步骤 2 / 步骤 5 工具）。

输入：一份"现场特征 JSON"（六层特征，骨架见 references/FEATURE_SPEC.md）。
输出：候选案例列表，按"归一化命中率"降序，每条带 L1/L2/L3 逐级命中判定
      与命中信号明细，供 Agent 写 applicability 与待验证点。

两条通道（`--source`），结论可信度不同，**不得混为一谈**：

  library（默认）→ /diag_case_library/search
      超节点诊断案例库，只返回 status=confirmed 的案例（人工确认过，含证据、
      分步处置与验证闭环）。kb_id 可选（可跨知识库召回），operation 是服务端
      过滤字段。这是"正解通道"。

  legacy        → /diagnosis_case/search
      旧的 diagnosis_case 表：**没有人工确认关卡、内容物很薄、kb_id 必填**。
      输出一律标注"来源=diagnosis_case（未经人工确认）"，只能当线索用，
      不得作为结论依据。

为什么在本地重算分数：
  服务端 match_score 是命中信号权重之和，未按查询信号总量归一化——提交 5 个信号
  和提交 1 个信号的查询，分数尺度不同、不可比。本脚本用同一张权重表计算归一化
  命中率（score_norm = 命中权重和 / 查询权重和），并把服务端原始分数与覆盖度
  一并列出（library 通道服务端本身也会返回 score_norm，两者口径一致）。

用法:
  python3 match_cases.py /tmp/case_match/features.json
  python3 match_cases.py /tmp/case_match/features.json --source legacy
  python3 match_cases.py /tmp/case_match/features.json --top 5 --json /tmp/case_match/result.json
  python3 match_cases.py --hit <case_id>          # 命中回写（步骤 5），不读特征文件

仅依赖 Python 标准库。默认绕过 HTTP 代理（等价于 curl --noproxy）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_API_BASE = os.environ.get("WITTY_API_BASE", "http://127.0.0.1:9772")

# 两条通道：library = 已人工确认的超节点诊断案例库（正解通道）；
# legacy = 旧的 diagnosis_case 表（未经确认，只当线索）。
SOURCE_LIBRARY = "library"
SOURCE_LEGACY = "legacy"
SOURCE_ENDPOINT = {
    SOURCE_LIBRARY: "/diag_case_library",
    SOURCE_LEGACY: "/diagnosis_case",
}
SOURCE_LABEL = {
    SOURCE_LIBRARY: "diag_case_library（已人工确认）",
    SOURCE_LEGACY: "diagnosis_case（未经人工确认）",
}

# 与 latency.database.managers.diagnosis_case.DiagnosisCasePGManager._signals_for_search
# / diag_case_library.DiagCaseLibraryPGManager._signals_for_search
# 保持同源；服务端调整权重时这里必须同步，否则归一化口径会漂移。
SIGNAL_WEIGHT: dict[str, float] = {
    "status_code": 3.0,
    "failure_mode_id": 3.0,
    "src_ip": 1.5,
    "dst_ip": 1.5,
    "host": 1.5,
    "pod": 1.5,
    "cluster": 1.5,
    "latency_component": 1.5,
    "log_keyword": 1.0,
    "operation": 1.5,
}

# 特征字段 -> 检索接口请求字段（同名直通，仅 status_codes/failure_mode_ids 复数形式一致）
FEATURE_TO_REQUEST: dict[str, str] = {
    "status_codes": "status_codes",
    "failure_mode_ids": "failure_mode_ids",
    "src_ips": "src_ips",
    "dst_ips": "dst_ips",
    "hosts": "hosts",
    "pods": "pods",
    "clusters": "clusters",
    "latency_components": "latency_components",
    "log_keywords": "log_keywords",
}

# 字段 -> 信号类型（用于权重与 L 级归组）
REQUEST_TO_SIGNAL: dict[str, str] = {
    "status_codes": "status_code",
    "failure_mode_ids": "failure_mode_id",
    "src_ips": "src_ip",
    "dst_ips": "dst_ip",
    "hosts": "host",
    "pods": "pod",
    "clusters": "cluster",
    "latency_components": "latency_component",
    "log_keywords": "log_keyword",
}

# L 级归组：L1 错误码 / L2 故障域 / L3 拓扑
LEVEL_OF_SIGNAL: dict[str, str] = {
    "status_code": "L1",
    "failure_mode_id": "L1",
    "latency_component": "L2",
    "operation": "L2",
    "src_ip": "L3",
    "dst_ip": "L3",
    "host": "L3",
    "pod": "L3",
    "cluster": "L3",
    "log_keyword": "L5",
}

LEVEL_MEANING = {
    "L1": "错误码/故障模式",
    "L2": "故障域/阶段桶",
    "L3": "拓扑(IP/Pod/主机/集群)",
    "L5": "机理关键词",
}


def _normalize(value: object) -> str:
    return str(value).strip().lower()


def _http_json(url: str, payload: dict | None, timeout: int) -> dict:
    """请求 API 并返回 JSON；默认绕过代理。"""
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _load_features(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        features = json.load(handle)
    if not isinstance(features, dict):
        raise ValueError("特征文件顶层必须是 JSON 对象")
    return features


def _build_query(features: dict, source: str = SOURCE_LIBRARY) -> tuple[dict, dict[str, float]]:
    """把特征 JSON 转成检索请求 + 查询信号权重表（key 为 (signal_type, value)）。

    library 通道 kb_id 可选（留空 = 跨知识库召回），并支持服务端 operation 过滤；
    legacy 通道 kb_id 必填且不支持 operation 过滤（只作正文标注）。
    """
    query: dict = {"page_num": 1, "page_cnt": 100}
    signals: dict[tuple[str, str], float] = {}

    kb_id = features.get("kb_id")
    if source == SOURCE_LEGACY and not kb_id:
        raise ValueError("legacy 通道的 kb_id 必填，且必须是真实存在的知识库 ID")
    if kb_id:
        query["kb_id"] = kb_id

    if features.get("fault_type"):
        query["fault_type"] = features["fault_type"]  # latency/connectivity/mixed/unknown
    if features.get("min_confidence") is not None:
        query["min_confidence"] = features["min_confidence"]

    if source == SOURCE_LIBRARY:
        operation = features.get("operation")
        if operation and str(operation).strip():
            # 新库支持 operation 服务端过滤：GET/SET 不再需要靠"分两次查询"隔离，
            # 且 operation 本身也是 1.5 权重的信号，本地归一化分母要对齐。
            operation_value = _normalize(operation)
            query["operation"] = operation_value
            signals[("operation", operation_value)] = SIGNAL_WEIGHT["operation"]

    for feature_field, request_field in FEATURE_TO_REQUEST.items():
        values = [_normalize(item) for item in (features.get(feature_field) or []) if str(item).strip()]
        if not values:
            continue
        query[request_field] = values
        signal_type = REQUEST_TO_SIGNAL[feature_field]
        weight = SIGNAL_WEIGHT[signal_type]
        for value in values:
            signals[(signal_type, value)] = weight

    if not signals:
        raise ValueError(
            "特征文件未提供任何可匹配信号（status_codes/failure_mode_ids/IP/主机/Pod/集群/"
            "latency_components/log_keywords 至少给一项）"
        )
    return query, signals


def _search(api_base: str, query: dict, timeout: int, source: str = SOURCE_LIBRARY) -> dict:
    url = api_base.rstrip("/") + SOURCE_ENDPOINT[source] + "/search"
    body = _http_json(url, query, timeout)
    result = body.get("result") or {}
    return {"total": result.get("total", 0), "matches": result.get("matches") or []}


def _rerank(matches: list[dict], signals: dict[tuple[str, str], float]) -> list[dict]:
    total_weight = sum(signals.values()) or 1.0
    query_values = {key: value for key, value in signals.items()}
    rows: list[dict] = []

    for match in matches:
        case = match.get("case") or {}
        matched = match.get("matched_signals") or []
        raw = 0.0
        levels: dict[str, list[str]] = {"L1": [], "L2": [], "L3": [], "L5": []}
        for signal in matched:
            signal_type = str(signal.get("signal_type", ""))
            signal_value = _normalize(signal.get("signal_value", ""))
            key = (signal_type, signal_value)
            query_weight = query_values.get(key)
            if query_weight is None:
                continue  # 服务端已过滤，这里再对齐一次，避免把未提交的信号算进分数
            raw += min(float(signal.get("weight", 0.0) or 0.0), query_weight)
            level = LEVEL_OF_SIGNAL.get(signal_type)
            if level:
                levels[level].append(f"{signal_type}={signal_value}")

        remediation = case.get("remediation_json") or []
        remediation_brief = "; ".join(
            str(step.get("action", "")) for step in remediation if isinstance(step, dict)
        )
        rows.append(
            {
                "case_id": case.get("id"),
                "case_no": case.get("case_no"),
                "status": case.get("status"),
                "title": case.get("title"),
                "fault_type": case.get("fault_type"),
                "operation": case.get("operation"),
                "confidence": case.get("confidence"),
                "revision": case.get("revision"),
                "hit_count": case.get("hit_count"),
                "updated_at": case.get("updated_at"),
                "score_raw": round(raw, 2),
                "score_norm": round(raw / total_weight, 4),
                "server_score_norm": match.get("score_norm"),
                "signal_coverage": f"{len(matched)}/{len(signals)}",
                "levels": {key: value for key, value in levels.items() if value},
                "level_summary": "+".join(sorted(key for key, value in levels.items() if value)) or "-",
                "symptom_summary": case.get("symptom_summary"),
                # library 用 root_cause_summary + remediation_json，legacy 用 root_cause + recommendation。
                "root_cause": case.get("root_cause_summary") or case.get("root_cause"),
                "root_cause_detail": case.get("root_cause_detail"),
                "recommendation": case.get("recommendation") or remediation_brief or None,
                "verification_closed": (case.get("verification_json") or {}).get("closed_loop"),
                "verification_result": (case.get("verification_json") or {}).get(
                    "observed_result"
                ),
                "scope_limits": case.get("scope_limits"),
                "counter_evidence_count": len(case.get("counter_evidence_json") or []),
                "evidence_ref_count": len(
                    case.get("evidence_json") or case.get("evidence_refs_json") or []
                ),
                "latency_components": case.get("latency_components"),
                "log_keywords": case.get("log_keywords"),
                "fingerprint": case.get("fingerprint_json") or {},
            }
        )

    rows.sort(
        key=lambda item: (
            item["score_norm"],
            item["score_raw"],
            item["confidence"] or 0.0,
            item["hit_count"] or 0,
            item["updated_at"] or "",
        ),
        reverse=True,
    )
    return rows


def _print_rows(
    rows: list[dict],
    total: int,
    operation: str,
    query: dict,
    source: str = SOURCE_LIBRARY,
) -> None:
    print(f"检索通道: {SOURCE_LABEL[source]}")
    if source == SOURCE_LEGACY:
        print(
            "警告: 来源=diagnosis_case（未经人工确认）——该表无准入关卡，内容物只有现象/根因/建议三段，"
            "只能作为线索，不得直接写入结论；确认过的案例请查 /diag_case_library。"
        )
    print(
        f"检索操作: operation={operation or '未标注'}  "
        f"kb_id={query.get('kb_id') or '(未指定，跨知识库)'}  API total={total}"
    )
    if not rows:
        print("候选案例: 0 条（无信号命中；不代表系统健康，也不代表没有同类故障）")
        return
    print(f"候选案例: {len(rows)} 条（按归一化命中率降序）")
    for index, row in enumerate(rows, start=1):
        prefix = f"[{index}] {row['case_no']} " if row.get("case_no") else f"[{index}] "
        print(
            f"{prefix}{row['case_id']}  score_norm={row['score_norm']}  "
            f"raw={row['score_raw']}  覆盖={row['signal_coverage']}  级别={row['level_summary']}"
        )
        print(
            f"    title={row['title']}  fault_type={row['fault_type']}  "
            f"operation={row['operation']}  status={row['status']}  confidence={row['confidence']}"
        )
        for level in ("L1", "L2", "L3", "L5"):
            values = row["levels"].get(level)
            if values:
                print(f"    {level}({LEVEL_MEANING[level]}): {', '.join(values)}")
        print(f"    root_cause: {(row['root_cause'] or '')[:160]}")
        print(f"    recommendation: {(row['recommendation'] or '')[:160]}")
        if row.get("scope_limits"):
            print(f"    不适用场景: {row['scope_limits'][:160]}")
        if row.get("verification_result"):
            closed = "已闭环" if row.get("verification_closed") else "未闭环"
            print(f"    验证({closed}): {row['verification_result'][:160]}")
    print("提醒: 命中案例是待验证假设，不是本次现场证据；须回到现场证据核对后才可进结论。")


def _mark_hit(
    api_base: str, case_id: str, timeout: int, source: str = SOURCE_LIBRARY
) -> int:
    url = api_base.rstrip("/") + SOURCE_ENDPOINT[source] + f"/{case_id}/hit"
    try:
        body = _http_json(url, {}, timeout)
    except urllib.error.HTTPError as error:
        print(f"回写失败: HTTP {error.code} {error.reason}", file=sys.stderr)
        return 3
    case = ((body.get("result") or {}).get("case")) or {}
    print(f"命中回写成功: case_id={case.get('id')} hit_count={case.get('hit_count')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="历史诊断案例检索（case-matching Skill）")
    parser.add_argument("features", nargs="?", help="现场特征 JSON 路径（步骤 2）")
    parser.add_argument("--hit", metavar="CASE_ID", help="命中回写指定案例（步骤 5，可脱离特征文件单独执行）")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="API 基址，默认取 WITTY_API_BASE")
    parser.add_argument(
        "--source",
        choices=[SOURCE_LIBRARY, SOURCE_LEGACY],
        default=SOURCE_LIBRARY,
        help="检索通道：library=已人工确认的案例库（默认）；legacy=旧的未确认表",
    )
    parser.add_argument("--top", type=int, default=5, help="打印条数，默认 5")
    parser.add_argument("--page-cnt", type=int, default=100, help="服务端取回条数，默认 100")
    parser.add_argument("--timeout", type=int, default=30, help="单次请求超时（秒），默认 30")
    parser.add_argument("--json", dest="json_out", help="候选结果落盘路径")
    args = parser.parse_args(argv)

    if args.hit:
        return _mark_hit(args.api_base, args.hit, args.timeout, args.source)
    if not args.features:
        parser.error("需要提供特征 JSON 路径，或使用 --hit CASE_ID")

    try:
        features = _load_features(args.features)
        query, signals = _build_query(features, args.source)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"特征文件不可用: {error}", file=sys.stderr)
        return 2

    query["page_cnt"] = args.page_cnt
    try:
        payload = _search(args.api_base, query, args.timeout, args.source)
    except urllib.error.HTTPError as error:
        print(f"检索失败: HTTP {error.code} {error.reason}", file=sys.stderr)
        return 3
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"检索失败: {error}", file=sys.stderr)
        return 3

    rows = _rerank(payload["matches"], signals)
    _print_rows(rows[: args.top], payload["total"], features.get("operation"), query, args.source)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "source": args.source,
                    "source_confirmed": args.source == SOURCE_LIBRARY,
                    "source_label": SOURCE_LABEL[args.source],
                    "operation": features.get("operation"),
                    "query": query,
                    "api_total": payload["total"],
                    "query_signal_count": len(signals),
                    "candidates": rows,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
        print(f"结果已落盘: {args.json_out}（候选 {len(rows)} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main())