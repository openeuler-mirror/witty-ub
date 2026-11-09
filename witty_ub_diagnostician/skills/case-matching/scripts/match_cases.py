#!/usr/bin/env python3
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
"""历史案例检索脚本（case-matching Skill 步骤 2 / 步骤 5 工具）。

输入：一份"现场特征 JSON"（分布特征，骨架见 references/FEATURE_SPEC.md）。
输出：候选案例列表，按"分布特征软匹配分"降序，每条带 L1/L2/L5 逐级命中判定
      与命中明细，供 Agent 写 applicability 与待验证点。

匹配口径（v2：分布特征软匹配）：
  身份特征（src_ip/dst_ip/host/pod/cluster 的具体名字）不再参与打分——不同
  故障现场的 IP/Pod 必然不同，按名字精确匹配既难命中也不可迁移。匹配改用
  "分布/语义" 特征做软打分（相对权重参考 Web 前端"相似案例分析"模块
  services/similarity.py：failure_mode 6.0 / status_code 4.0 / 段排名·时延形态
  2~4 / 超时段 2.0 / 弱特征 0.5~1.5，见 references/FEATURE_SPEC.md）：

    L1 故障模式       failure_mode_ids   4.0          精确语义，跨现场可迁移（最强）
    L1 错误码分布     status_codes       3.0 × share  主导错误码权重次之
    L2 超时时延段     latency_components 2.0 × share  时延故障核心特征（归因桶）
    L2 操作域         operation          1.0          查询 GET/SET 与案例一致（MIXED 部分），宽召回已过滤故弱化
    L5 机理关键词     log_keywords       1.0          现场日志原文短语
    L2 时间形态       time_shape         1.0          突发单点/短时簇发/持续劣化 相等加分
    L2 影响范围       affected_scope     0.5          single_pod/few_pods/multi_pod 相等加分
    L2 拓扑形状       topology_shape     0.5          link_pair（源目链路对 A↔B，两侧同源可提取）相等加分

  share ∈ (0,1]，表示该特征在本次故障中的贡献占比（如归因桶 trace 占比、
  主导错误码占比），由 Agent 从 /stats/stages、错误码统计中提取。

  召回改为"宽召回"：按 operation + fault_type + kb_id（可选）拉回候选，不再
  依赖服务端"至少一个信号精确命中"（v1 口径）；相似度由本脚本软打分决定。
  score_norm = Σ(命中特征 base×share) / Σ(全部查询特征 base×share)，0~1。
  宽召回后剔除一级标签为 Coordinator故障 / UB管控面故障 的候选（LOO 全量评估
  实证：这类候选在软打分维度与 Worker/硬件报告高度重叠、吸走 top1 位置，而
  对应查询报告本身判别特征不足，保留 C 候选只引入干扰），不参与软打分与投票。

  v3 文本相似度破平局：特征文件可提供 query_text（诊断中途草稿——只含现象确认与
  阶段定位等 confirmed=True 的推理步文本，不含候选根因/反证/结论/处置）。本脚本对
  query_text 与案例表现文本（symptom_summary / fault_shape / latency_components /
  log_keywords / evidence_json.excerpt 前 6 条现场证据锚点）做词级 cosine 相似度，
  错误码/日志常量词（K_URMA_ERROR、E112 等）权重 ×3；cosine 作为 score_norm 并列时的
  次级排序键，用于修正"软打分满分但文本完全不符"的通用案例霸榜问题。未提供
  query_text 时该维度为 0，排序退化为 v2 行为。

  P2 文本翻盘：top1 与候选 score_norm 差 <0.2 且候选 text_sim 显著更高（>0.15）时，
  将文本匹配最强的候选提到第 1 位，修正 norm 本身错位但文本高度吻合的误排。
  （LOO 消融：evidence 扩展 + 常量词加权 + 翻盘 总体 60.8% / 不含管控 68.3%。）

两条通道（--source），结论可信度不同，**不得混为一谈**：

  library（默认）→ /diag_case_library/search
      超节点诊断案例库，只返回 status=confirmed 的案例（人工确认过，含证据、
      分步处置与验证闭环）。kb_id 可选（可跨知识库召回），operation 是服务端
      过滤字段。这是"正解通道"。

  legacy        → /diagnosis_case/search
      旧的 diagnosis_case 表：**没有人工确认关卡、内容物很薄、kb_id 必填**。
      输出一律标注"来源=diagnosis_case（未经人工确认）"，只能当线索用，
      不得作为结论依据。

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
import math
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter

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

# 分布特征软匹配权重表（v2）。身份特征（IP/Pod/主机/集群名）不参与打分。
# 相对权重参考 Web 前端"相似案例分析"模块（src/plugins/latency/services/similarity.py：
# failure_mode 6.0 / status_code 4.0 / 操作·段排名 3.0 / 超时段·时延形态 2.0 / scope 1.0）：
# failure_mode 应高于 status_code，段权重居中，形态/规模为弱加分。
# operation 在 library 通道已被服务端过滤隔离，故仅给弱加分（区分 MIXED/GET/SET）。
SOFT_WEIGHT: dict[str, float] = {
    "failure_mode_id": 4.0,
    "status_code": 3.0,
    "latency_component": 2.0,
    "log_keyword": 1.0,
    "operation": 1.0,
    "time_shape": 1.0,
    "affected_scope": 0.5,
    "topology_shape": 0.5,
}

# 生产候选排除：Coordinator/UB管控面 一级标签的案例不进入候选集合。
# LOO 全量评估（120 报告 / 126 案例）实证：这两类候选在软打分维度与 Worker/硬件
# 报告高度重叠、吸走 top1（保留时不含C top1=63.4%，剔除后 68.3%）；且 C 类查询
# 报告本身判别特征不足、label_vote 几乎全 miss，保留 C 候选只引入干扰。
EXCLUDED_FIRST_LEVEL_LABELS: tuple[str, ...] = ("Coordinator故障", "UB管控面故障")

# L 级归组（报告/结论书写用）
LEVEL_OF_FEATURE: dict[str, str] = {
    "status_code": "L1",
    "failure_mode_id": "L1",
    "latency_component": "L2",
    "operation": "L2",
    "time_shape": "L2",
    "affected_scope": "L2",
    "topology_shape": "L2",
    "log_keyword": "L5",
}

LEVEL_MEANING = {
    "L1": "错误码/故障模式",
    "L2": "故障域/阶段桶/时间形态/影响范围",
    "L5": "机理关键词",
}


def _normalize(value: object) -> str:
    return str(value).strip().lower()


def _normalize_operation(value: object) -> str:
    """operation 归一化：服务端枚举为 GET/SET/N/A，大小写敏感，不能走小写化的 _normalize。"""
    return str(value).strip().upper()


_CONST_RE = re.compile(r"(?:K_[A-Z][A-Z0-9_]{2,}|E\d{1,4}|[A-Z0-9]{2,6}_[A-Z0-9_]{3,})")


def _tokenize_weighted(text: str, const_weight: float = 3.0) -> Counter:
    """词级切分（带常量词加权）：英文标识符、3~6 位数字（归一 numXXX）、中文二元组。

    错误码/日志常量词（K_URMA_ERROR、E112、URMA_WAIT_TIMEOUT 等）权重 ×const_weight，
    提升它们在 cosine 中的判别作用。与 LOO 消融实验"草稿Q/表现C"口径（59.2%）一致。
    """
    counter: Counter = Counter()
    if not text:
        return counter
    text = str(text)
    for match in re.findall(r"[A-Za-z][A-Za-z0-9_]{1,}", text):
        weight = const_weight if _CONST_RE.match(match) else 1.0
        counter[match.lower()] += weight
    for match in re.findall(r"\b\d{3,6}\b", text):
        counter["num" + match] += 1.0
    for seg in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(seg) >= 2:
            for i in range(len(seg) - 1):
                counter[seg[i : i + 2]] += 1.0
    return counter


def _text_cosine(a: str, b: str) -> float:
    """两个文本的词级 cosine 相似度（0~1）。任一文本为空返回 0。"""
    ca = _tokenize_weighted(a)
    cb = _tokenize_weighted(b)
    if not ca or not cb:
        return 0.0
    dot = sum(ca[token] * cb[token] for token in set(ca) & set(cb))
    norm_a = math.sqrt(sum(v * v for v in ca.values()))
    norm_b = math.sqrt(sum(v * v for v in cb.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _case_symptom_text(case: dict) -> str:
    """案例侧表现文本：表现字段 + 现场证据锚点（evidence.excerpt），不含根因/处置。

    证据锚点是故障现象的原始现场描述，属于"只用故障表现"合法口径；剔除案例自身
    标签词避免标签直配。
    """
    parts: list[str] = []
    for field in ("symptom_summary", "fault_shape"):
        value = case.get(field)
        if value:
            parts.append(str(value))
    for field in ("latency_components", "log_keywords"):
        for value in case.get(field) or []:
            if str(value).strip():
                parts.append(str(value))
    for evidence in (case.get("evidence_json") or [])[:6]:
        if isinstance(evidence, dict) and evidence.get("excerpt"):
            parts.append(str(evidence["excerpt"]))
    text = " ".join(parts)
    for label in (case.get("first_level_label"), case.get("second_level_label")):
        if label:
            text = text.replace(str(label), "")
    return text


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


def _values_with_shares(features: dict, field: str, shares_field: str | None) -> list[dict]:
    """取特征值列表，若提供了 share 映射则按值取占比（缺省 1.0）。"""
    values = [_normalize(item) for item in (features.get(field) or []) if str(item).strip()]
    shares = {
        _normalize(key): float(value)
        for key, value in ((features.get(shares_field) or {}).items() if shares_field else {})
    }
    return [{"value": value, "share": shares.get(value, 1.0)} for value in values]


def _extract_soft_features(features: dict) -> dict:
    """把特征 JSON 转成软匹配特征（值 + 贡献占比 share）。"""
    return {
        "status_codes": _values_with_shares(features, "status_codes", "status_code_shares"),
        "failure_mode_ids": _values_with_shares(features, "failure_mode_ids", None),
        "latency_components": _values_with_shares(features, "latency_components", "latency_component_shares"),
        "log_keywords": _values_with_shares(features, "log_keywords", None),
        "operation": _normalize_operation(features["operation"]) if features.get("operation") else None,
        "time_shape": _normalize(features["time_shape"]) if features.get("time_shape") else None,
        "affected_scope": _normalize(features["affected_scope"]) if features.get("affected_scope") else None,
        # 保守版仅 link_pair 参与打分；其余形状（bi_pair/conc/spread）案例侧暂无法提取，置空不参与。
        "topology_shape": "link_pair" if _normalize(features["topology_shape"]) == "link_pair" else None,
    }


def _soft_feature_count(soft: dict) -> int:
    return (
        len(soft["status_codes"])
        + len(soft["failure_mode_ids"])
        + len(soft["latency_components"])
        + len(soft["log_keywords"])
        + (1 if soft["operation"] else 0)
        + (1 if soft["time_shape"] else 0)
        + (1 if soft["affected_scope"] else 0)
        + (1 if soft["topology_shape"] else 0)
    )


def _build_recall_query(features: dict, source: str = SOURCE_LIBRARY) -> dict:
    """构建宽召回查询：只带过滤头（kb_id/fault_type/min_confidence/operation），
    不带任何匹配信号——服务端按过滤条件返回候选，软打分在本脚本完成。

    library 通道 kb_id 可选（留空 = 跨知识库召回），并支持服务端 operation 过滤；
    legacy 通道 kb_id 必填（旧表不支持 operation 过滤，只作正文标注）。
    """
    query: dict = {"page_num": 1, "page_cnt": 100}

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
            query["operation"] = _normalize_operation(operation)

    return query


def _classify_scope(case: dict) -> str:
    """按案例记录的影响规模（Pod+Host 去重数）分类，避免把具体名字当特征。"""
    identities = set()
    for field in ("pods", "hosts"):
        for item in case.get(field) or []:
            for part in str(item).split("/"):
                part = part.strip()
                if part:
                    identities.add(part)
    count = len(identities)
    if count <= 1:
        return "single_pod"
    if count <= 4:
        return "few_pods"
    return "multi_pod"


# 保守弱特征：受影响实体呈"源目链路对"（A ↔ B / A → B）时判 link_pair。
# LOO 实测该形状 100% 指向硬件故障（client_*_tcp_down / scale_in_tcp_down 等），
# 且两侧同源可提取：查询侧从报告 statistics.top_pods 判，案例侧从 case.pods 判。
# 仅 link_pair 参与打分（0.5 最低档）；bi_pair/conc/spread 需浓度 pct，案例侧
# pods 字段无 pct 无法提取，当前不参与（FEATURE_SPEC 预留）。
_PAIR_RE = re.compile(r"(↔|→|->|⟷|⇄|⇒)")


def _topology_shape_from_pods(pods: list | None) -> str | None:
    """从受影响 Pod 列表判拓扑形状：任一实体为源目链路对 → link_pair。"""
    for pod in pods or []:
        if _PAIR_RE.search(str(pod)):
            return "link_pair"
    return None


def _soft_score(case: dict, soft: dict) -> tuple[float, float, dict[str, list[str]], int]:
    """对单个候选案例做分布特征软打分。

    返回 (raw, norm, matched_by_level, matched_count)。norm 在 0~1 之间：
    raw = Σ(命中特征 base×share)；norm = raw / Σ(全部查询特征 base×share)。
    """
    matched: dict[str, list[str]] = {"L1": [], "L2": [], "L5": []}
    raw = 0.0

    def _list_hit(feature_items: list[dict], case_field: str, level: str, label: str) -> None:
        nonlocal raw
        case_values = {_normalize(value) for value in (case.get(case_field) or [])}
        for item in feature_items:
            if item["value"] in case_values:
                contribution = SOFT_WEIGHT[label] * item["share"]
                raw += contribution
                matched[level].append(f"{label}={item['value']}(share={item['share']})")

    _list_hit(soft["status_codes"], "status_codes", "L1", "status_code")
    _list_hit(soft["failure_mode_ids"], "failure_mode_ids", "L1", "failure_mode_id")
    _list_hit(soft["latency_components"], "latency_components", "L2", "latency_component")
    _list_hit(soft["log_keywords"], "log_keywords", "L5", "log_keyword")

    if soft["operation"]:
        case_op = _normalize_operation(case.get("operation") or "")
        if case_op == soft["operation"]:
            raw += SOFT_WEIGHT["operation"]
            matched["L2"].append(f"operation={soft['operation']}")
        elif case_op == "MIXED":
            raw += SOFT_WEIGHT["operation"] * 0.5
            matched["L2"].append("operation=MIXED(部分)")

    if soft["time_shape"] and case.get("fault_shape") and _normalize(case["fault_shape"]) == soft["time_shape"]:
        raw += SOFT_WEIGHT["time_shape"]
        matched["L2"].append(f"time_shape={soft['time_shape']}")

    if soft["affected_scope"] and _classify_scope(case) == soft["affected_scope"]:
        raw += SOFT_WEIGHT["affected_scope"]
        matched["L2"].append(f"affected_scope={soft['affected_scope']}")

    # 拓扑形状：查询与案例均为源目链路对（link_pair）才加分；其余形状不参与。
    if soft["topology_shape"] and _topology_shape_from_pods(case.get("pods")) == soft["topology_shape"]:
        raw += SOFT_WEIGHT["topology_shape"]
        matched["L2"].append(f"topology_shape={soft['topology_shape']}")

    denominator = (
        sum(SOFT_WEIGHT["status_code"] * item["share"] for item in soft["status_codes"])
        + sum(SOFT_WEIGHT["failure_mode_id"] * item["share"] for item in soft["failure_mode_ids"])
        + sum(SOFT_WEIGHT["latency_component"] * item["share"] for item in soft["latency_components"])
        + sum(SOFT_WEIGHT["log_keyword"] * item["share"] for item in soft["log_keywords"])
        + (SOFT_WEIGHT["operation"] if soft["operation"] else 0.0)
        + (SOFT_WEIGHT["time_shape"] if soft["time_shape"] else 0.0)
        + (SOFT_WEIGHT["affected_scope"] if soft["affected_scope"] else 0.0)
        + (SOFT_WEIGHT["topology_shape"] if soft["topology_shape"] else 0.0)
    )
    norm = raw / denominator if denominator else 0.0
    matched_count = len(matched["L1"]) + len(matched["L2"]) + len(matched["L5"])
    return raw, norm, matched, matched_count


def _search(api_base: str, query: dict, timeout: int, source: str = SOURCE_LIBRARY) -> dict:
    url = api_base.rstrip("/") + SOURCE_ENDPOINT[source] + "/search"
    body = _http_json(url, query, timeout)
    result = body.get("result") or {}
    return {"total": result.get("total", 0), "matches": result.get("matches") or []}


def _exclude_control_plane(matches: list[dict]) -> tuple[list[dict], int]:
    """从宽召回结果中剔除 Coordinator/UB管控面 一级标签候选。

    返回 (保留的候选, 剔除条数)。仅按 first_level_label 判，不影响其余候选；
    first_level_label 为空/缺失的候选正常保留。
    """
    kept: list[dict] = []
    dropped = 0
    for match in matches:
        case = match.get("case") or {}
        if case.get("first_level_label") in EXCLUDED_FIRST_LEVEL_LABELS:
            dropped += 1
        else:
            kept.append(match)
    return kept, dropped


def _rerank(matches: list[dict], soft: dict, query_text: str = "") -> list[dict]:
    """对宽召回结果做软打分并排序（score_norm 降序，并列时按文本余弦破平局）。

    v4 增强：查询文本自动拼接查询侧 log_keywords（现场日志机理关键词），使
    日志常量词（E2001/E112/URMA_* 等）进入文本余弦；与案例侧 log_keywords
    （回填自真实日志）形成对称比较，_tokenize_weighted 已对常量词 ×3 加权。
    """
    feature_count = _soft_feature_count(soft)
    text_query = query_text
    log_keywords_from_query = [
        item["value"]
        for item in soft["log_keywords"]
        if str(item["value"]).strip()
    ]
    if log_keywords_from_query:
        text_query = f"{query_text} {' '.join(log_keywords_from_query)}".strip()
    rows: list[dict] = []
    for match in matches:
        case = match.get("case") or {}
        raw, norm, matched, matched_count = _soft_score(case, soft)
        remediation = case.get("remediation_json") or []
        remediation_brief = "; ".join(
            str(step.get("action", "")) for step in remediation if isinstance(step, dict)
        )
        text_sim = _text_cosine(text_query, _case_symptom_text(case)) if text_query else 0.0
        rows.append(
            {
                "case_id": case.get("id"),
                "case_no": case.get("case_no"),
                "first_level_label": case.get("first_level_label"),
                "second_level_label": case.get("second_level_label"),
                "status": case.get("status"),
                "title": case.get("title"),
                "fault_type": case.get("fault_type"),
                "operation": case.get("operation"),
                "confidence": case.get("confidence"),
                "revision": case.get("revision"),
                "hit_count": case.get("hit_count"),
                "updated_at": case.get("updated_at"),
                "score_raw": round(raw, 2),
                "score_norm": round(norm, 4),
                "text_sim": round(text_sim, 4),
                "feature_coverage": f"{matched_count}/{feature_count}",
                "levels": {key: value for key, value in matched.items() if value},
                "level_summary": "+".join(sorted(key for key, value in matched.items() if value)) or "-",
                "symptom_summary": case.get("symptom_summary"),
                "root_cause": case.get("root_cause_summary") or case.get("root_cause"),
                "root_cause_detail": case.get("root_cause_detail"),
                "recommendation": case.get("recommendation") or remediation_brief or None,
                "verification_closed": (case.get("verification_json") or {}).get("closed_loop"),
                "verification_result": (case.get("verification_json") or {}).get("observed_result"),
                "scope_limits": case.get("scope_limits"),
                "counter_evidence_count": len(case.get("counter_evidence_json") or []),
                "evidence_ref_count": len(case.get("evidence_json") or case.get("evidence_refs_json") or []),
                "latency_components": case.get("latency_components"),
                "status_codes": case.get("status_codes"),
                "failure_mode_ids": case.get("failure_mode_ids"),
                "fault_shape": case.get("fault_shape"),
                "log_keywords": case.get("log_keywords"),
                "fingerprint": case.get("fingerprint_json") or {},
            }
        )

    rows.sort(
        key=lambda item: (
            item["score_norm"],
            item["text_sim"],
            item["confidence"] or 0.0,
            item["hit_count"] or 0,
            item["updated_at"] or "",
        ),
        reverse=True,
    )
    _apply_text_override(rows)
    return rows


def _apply_text_override(rows: list[dict]) -> None:
    """P2 文本翻盘：top1 与候选 norm 差 <0.2 且候选 text_sim 显著更高（>0.15）时，
    把文本匹配最强的候选提到第 1 位，修正"软打分并列但文本完全不符"的误排。
    仅在候选非空且确实存在显著文本优势时生效，其余情况保持原排序。"""
    if not rows:
        return
    top = rows[0]
    override = None
    for candidate in rows[1:]:
        if top["score_norm"] - candidate["score_norm"] < 0.2 and (
            candidate["text_sim"] > top["text_sim"] + 0.15
        ):
            if override is None or candidate["text_sim"] > override["text_sim"]:
                override = candidate
    if override is not None:
        rows.remove(override)
        rows.insert(0, override)


def _label_vote(rows: list[dict], top_k: int = 14, margin: float = 0.1) -> dict:
    """topK 一级标签投票（混合决策，生产剔C口径 K 网格最优：K=14 → 不含C 72.3%）。

    top1 与 top2 的 score_norm 差 > margin 时，top1 明显胜出，直接取 top1 标签；
    否则对 topK 候选中一级标签做等权多数投票，缓解"并列候选标签分歧"下的误选。
    返回 {"label", "method", "distribution"}；method ∈ top1_margin / topK_vote /
    fallback_top1（无有效标签候选）/ empty。
    """
    if not rows:
        return {"label": None, "method": "empty", "distribution": {}}
    top10_distribution = Counter(
        row.get("first_level_label") for row in rows[:top_k] if row.get("first_level_label")
    )
    if len(rows) >= 2 and rows[0]["score_norm"] - rows[1]["score_norm"] > margin:
        return {
            "label": rows[0].get("first_level_label"),
            "method": "top1_margin",
            "distribution": dict(top10_distribution.most_common(8)),
        }
    counts = Counter(
        row.get("first_level_label") for row in rows[:top_k] if row.get("first_level_label")
    )
    if not counts:
        return {
            "label": rows[0].get("first_level_label"),
            "method": "fallback_top1",
            "distribution": {},
        }
    return {
        "label": counts.most_common(1)[0][0],
        "method": "topK_vote",
        "distribution": dict(counts.most_common(8)),
    }


def _print_soft_features(soft: dict) -> None:
    parts = []
    for category, label in (
        ("status_codes", "错误码"),
        ("failure_mode_ids", "故障模式"),
        ("latency_components", "超时时延段"),
        ("log_keywords", "机理关键词"),
    ):
        for item in soft[category]:
            parts.append(f"{label}={item['value']}(×{SOFT_WEIGHT[category_to_signal(category)]}×share={item['share']})")
    if soft["operation"]:
        parts.append(f"操作域={soft['operation']}(×{SOFT_WEIGHT['operation']})")
    if soft["time_shape"]:
        parts.append(f"时间形态={soft['time_shape']}(×{SOFT_WEIGHT['time_shape']})")
    if soft["affected_scope"]:
        parts.append(f"影响范围={soft['affected_scope']}(×{SOFT_WEIGHT['affected_scope']})")
    if soft["topology_shape"]:
        parts.append(f"拓扑形状={soft['topology_shape']}(×{SOFT_WEIGHT['topology_shape']})")
    print("分布特征:", "；".join(parts) if parts else "(未提供，打分全为 0)")


def category_to_signal(category: str) -> str:
    return {
        "status_codes": "status_code",
        "failure_mode_ids": "failure_mode_id",
        "latency_components": "latency_component",
        "log_keywords": "log_keyword",
    }[category]


def _print_rows(
    rows: list[dict],
    total: int,
    operation: str,
    query: dict,
    soft: dict,
    source: str = SOURCE_LIBRARY,
    vote: dict | None = None,
) -> None:
    print(f"检索通道: {SOURCE_LABEL[source]}")
    if source == SOURCE_LEGACY:
        print(
            "警告: 来源=diagnosis_case（未经人工确认）——该表无准入关卡，内容物只有现象/根因/建议三段，"
            "只能作为线索，不得直接写入结论；确认过的案例请查 /diag_case_library。"
        )
    print(
        f"检索操作: operation={operation or '未标注'}  "
        f"kb_id={query.get('kb_id') or '(未指定，跨知识库)'}  API total={total}（宽召回候选）"
    )
    _print_soft_features(soft)
    if not rows:
        print("候选案例: 0 条（宽召回下仍为空，说明库内无同类故障；不代表系统健康）")
        return
    print(f"候选案例: {len(rows)} 条（按分布特征软匹配分降序，并列时按文本余弦破平局）")
    if vote and vote.get("label"):
        method_label = {
            "top1_margin": "top1 明显胜出，直接采用",
            "topK_vote": "top1 并列，top10 一级标签多数投票",
            "fallback_top1": "无有效标签候选，回退 top1",
        }
        print(
            f"一级标签投票: {vote['label']}（{method_label.get(vote['method'], vote['method'])}；"
            f"top10 分布 {vote['distribution']}）"
        )
    for index, row in enumerate(rows, start=1):
        prefix = f"[{index}] {row['case_no']} " if row.get("case_no") else f"[{index}] "
        print(
            f"{prefix}{row['case_id']}  score_norm={row['score_norm']}  text_sim={row['text_sim']}  "
            f"raw={row['score_raw']}  覆盖={row['feature_coverage']}  级别={row['level_summary']}"
        )
        print(
            f"    title={row['title']}  fault_type={row['fault_type']}  "
            f"operation={row['operation']}  status={row['status']}  confidence={row['confidence']}"
        )
        for level in ("L1", "L2", "L5"):
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
    parser.add_argument("--page-cnt", type=int, default=100, help="服务端宽召回条数，默认 100")
    parser.add_argument("--timeout", type=int, default=30, help="单次请求超时（秒），默认 30")
    parser.add_argument("--json", dest="json_out", help="候选结果落盘路径")
    args = parser.parse_args(argv)

    if args.hit:
        return _mark_hit(args.api_base, args.hit, args.timeout, args.source)
    if not args.features:
        parser.error("需要提供特征 JSON 路径，或使用 --hit CASE_ID")

    try:
        features = _load_features(args.features)
        query = _build_recall_query(features, args.source)
        soft = _extract_soft_features(features)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"特征文件不可用: {error}", file=sys.stderr)
        return 2

    if not _soft_feature_count(soft):
        print("警告: 特征文件未提供任何分布特征，软打分全部为 0（仍按 confidence/hit_count 排序）")

    query["page_cnt"] = args.page_cnt
    try:
        payload = _search(args.api_base, query, args.timeout, args.source)
    except urllib.error.HTTPError as error:
        print(f"检索失败: HTTP {error.code} {error.reason}", file=sys.stderr)
        return 3
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"检索失败: {error}", file=sys.stderr)
        return 3

    matches, dropped = _exclude_control_plane(payload["matches"])
    if dropped:
        print(
            f"已剔除 {dropped} 条 Coordinator/UB管控面 候选（不参与软打分与投票）；"
            f"API total={payload['total']}，实际候选 {len(matches)} 条"
        )
    rows = _rerank(matches, soft, features.get("query_text") or "")
    vote = _label_vote(rows)
    _print_rows(
        rows[: args.top],
        payload["total"],
        features.get("operation"),
        query,
        soft,
        args.source,
        vote,
    )

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "source": args.source,
                    "source_confirmed": args.source == SOURCE_LIBRARY,
                    "source_label": SOURCE_LABEL[args.source],
                    "operation": features.get("operation"),
                    "query_text": features.get("query_text"),
                    "recall_query": query,
                    "soft_features": soft,
                    "api_total": payload["total"],
                    "excluded_control_plane": dropped,
                    "candidates": rows,
                    "label_vote": vote,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
        print(f"结果已落盘: {args.json_out}（候选 {len(rows)} 条，一级标签投票 {vote['label'] or '无'}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
