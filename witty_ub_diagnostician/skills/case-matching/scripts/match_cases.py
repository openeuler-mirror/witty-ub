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
    L2 操作域         operation          1.0          查询 GET/SET 与案例一致（MIXED 部分），服务端过滤默认关闭，改由此弱化
    L5 机理关键词     log_keywords       1.0          现场日志原文短语
    L2 时间形态       time_shape         1.0          突发单点/短时簇发/持续劣化 相等加分
    L2 影响范围       affected_scope     0.5          single_pod/few_pods/multi_pod 相等加分
    L2 拓扑形状       topology_shape     0.0          link_pair（源目链路对 A↔B，两侧同源可提取）相等加分（LOO 实证为净负，已归零）

  share ∈ (0,1]，表示该特征在本次故障中的贡献占比（如归因桶 trace 占比、
  主导错误码占比），由 Agent 从 /stats/stages、错误码统计中提取。

  召回改为"宽召回"：按 operation + fault_type + kb_id（可选）拉回候选，不再
  依赖服务端"至少一个信号精确命中"（v1 口径）；相似度由本脚本软打分决定。
  score_norm = Σ(命中特征 base×share) / Σ(全部查询特征 base×share)，0~1。
  宽召回后剔除一级标签为 Coordinator故障 / UB管控面故障 的候选（LOO 全量评估
  实证：这类候选在软打分维度与 Worker/硬件报告高度重叠、吸走 top1 位置，而
  对应查询报告本身判别特征不足，保留 C 候选只引入干扰），不参与软打分与投票。

  宽召回改为"拉全"（v2.6）：按过滤头翻页收满服务端返回的全部候选，不再受单页
  page_cnt 上限截断。原因是宽召回请求不带匹配信号，服务端对零信号查询按
  (confidence, hit_count, updated_at) 排序返回——与查询内容无关，单页截断只会
  盲删相关候选。此时 page_cnt 仅作为分页大小，实际候选数由 _search_all 翻页收满。

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
      分步处置与验证闭环）。kb_id 可选（可跨知识库召回）；operation 服务端过滤
      默认关闭（--operation-filter 可开启）。这是"正解通道"。

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
# operation 的服务端过滤默认关闭（见 OPERATION_FILTER_ENABLED），宽召回后候选操作域
# 可能不一致，故给弱加分（1.0）用于区分 GET/SET/MIXED。
SOFT_WEIGHT: dict[str, float] = {
    "failure_mode_id": 4.0,
    "status_code": 3.0,
    "latency_component": 2.0,
    "log_keyword": 1.0,
    "operation": 1.0,
    "time_shape": 1.0,
    "affected_scope": 0.5,
    # topology_shape 曾由 0.5 提升到 1.5。训练集 1110 LOO 消融显示其为净负特征：
    # 置 0 后 K4 70.2%→70.7%、top1 69.7%→71.3%，且两套召回口径（95篇pre库 / 188条LOO）
    # 结论一致，故归零。提取逻辑 _topology_shape_from_pods 保留，后续引入浓度 pct 再评估。
    "topology_shape": 0.0,
}

# 服务端 operation 过滤开关（默认关闭）。
# 关闭时召回不下发 operation，候选操作域交由 operation 特征（权重 1.0）软处理。
# 1112 文档集 LOO 复评（margin=0.05）：关闭后 top1 70.1%→71.6%、K4 70.6%→72.2%，
# 与「全量池」口径一致。开启（--operation-filter）则复刻旧的服务端硬过滤。
OPERATION_FILTER_ENABLED = False

# 生产候选排除：Coordinator/UB管控面 一级标签的案例不进入候选集合。
# LOO 全量评估（120 报告 / 126 案例）实证：这两类候选在软打分维度与 Worker/硬件
# 报告高度重叠、吸走 top1（保留时不含C top1=63.4%，剔除后 68.3%）；且 C 类查询
# 报告本身判别特征不足、label_vote 几乎全 miss，保留 C 候选只引入干扰。
EXCLUDED_FIRST_LEVEL_LABELS: tuple[str, ...] = ("Coordinator故障", "UB管控面故障")

# 「用户相关故障/使用问题」硬判定。查询侧错误码一旦命中 USER_USAGE_FAULT_CODES，
# 本次故障即锁定为 用户相关故障/使用问题，并只召回该标签的案例，不再与其他类别竞争。
# 码集 = KVCache 故障模式知识库「故障域=用户」的 16 个码，加上语义同属使用问题的
# 17/28/3004/3007/3009，并剔除 2/8/36——这三个码在现有案例库中分别挂在硬件/Worker/
# 容器/Coordinator 场景上，不具备用户使用问题的判别力；再剔除 0——0 是「无错误/成功」
# 码，在硬件故障报告里同样会出现，纳入会误触发硬判定。
USER_USAGE_FIRST_LEVEL = "用户相关故障"
USER_USAGE_SECOND_LEVEL = "使用问题"
USER_USAGE_FAULT_CODES: frozenset[str] = frozenset({
    "1", "3", "9", "12", "17", "28",
    "2000", "2001", "2004", "2006",
    "3000", "3001", "3002", "3004", "3006", "3007", "3009",
})

# 未见码经 suggest_similar_codes.py 折算出的相近已知码，按此占比降权参与软打分：
# 让检索能沾上相似案例，但不至于把不相干的候选顶上来。
RELAXED_STATUS_CODE_SHARE = 0.5

# v2.4 打分改造（训练集 1110 LOO 实证：不含C/不含集群 top1 68.6%→70.8%、K14 67.6%→68.6%）：
# 原等权打分下 82.2% 的查询 top1 与其它候选 score_norm 完全并列（55.7% 跨一级标签），
# 最终靠 text_sim 抛硬币，这是"硬件↔Worker 互混"的主因。三条正交改造：
#   ① status_codes 改用 F1 计分（兼顾召回与精度）：候选码集越不精确、得分越低，
#      使"码集完全命中"的精确案例压过"码多且杂"的宽泛案例，打破并列；
#   ② 错误码→故障域先验：按候选池内 码/故障模式→一级标签 分布对**查询真实特征**投票，
#      命中预测域的候选加 DOMAIN_PRIOR_WEIGHT × 投票占比 的加分（相近码降权参与；
#      故障模式通道权重 0.1，由 PRIOR_CHANNEL_WEIGHT 控制）；
#   ③ topology_shape 权重曾 0.5→1.5，后经 LOO 消融证伪为净负，已归零（见 SOFT_WEIGHT 注释）。
# 错误码→故障域先验：错误码通道权重 + 故障模式通道权重（后者为辅助，权重须远小于前者）。
# 实测（237 案例真库 LOO 网格）：总权重 0.2 时最优（K4 69.1%→69.7%，131/188）；0.35 次之
# （69.1%），0.5/0.7 单调下滑（68.1%）。故障模式通道仍取 0.1 辅助。
# 两通道权重之和即注入软打分的总权重（见 _soft_score 的 prior_denom）。
DOMAIN_PRIOR_WEIGHT = 0.2
PRIOR_CHANNEL_WEIGHT: dict[str, float] = {"status_codes": 0.25, "failure_mode_ids": 0.1}

# v2.5 日志语义码通道：查询侧与候选案例侧「日志语义错误码轮廓」的 cosine 相似度。
# 轮廓来自 log_failure_event(E/W) 原文里的语义错误码（code: [Not ready] /
# [Urma wait for completion timed out]）与日志常量 token（URMA_WAIT_TIMEOUT、E2001 等）。
# 候选案例侧 log_id 未落库（diag_case_library.source_log_ids 为空），故轮廓由离线脚本
# build_log_semantic_profiles.py 物化到 references/log_semantic_profiles.json；
# 查询侧优先按 features.json 的 log_id 查资产 by_log_id，回退 kb_name → by_kb_name。
# 生产资产实测（188 条不含C / 237 案例池）：top1 66.5%→70.7%（+8 条），K4 69.7%→70.7%（+2 条）；
# 收益全部落在"硬件↔Worker"边界（URMA 时延族 vs Not ready/RPC peer dead 族），
# 对小类（SDK/OS/容器无 E/W 日志）无影响。故仅作加性次级通道，两侧都有轮廓时才生效。
LOG_SEMANTIC_WEIGHT = 0.5
LOG_SEMANTIC_ENABLED = True
LOG_SEMANTIC_ASSET = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "references",
    "log_semantic_profiles.json",
)
_LOG_SEMANTIC_CACHE: dict | None = None

# v2.7 判别加权：轮廓是纯 TF 归一化，高频泛码（URMA_WRITE 69/246、E112 60/246、
# RPC peer dead 55/246…）横跨所有类别，会淹没稀疏但有判别力的码
# （UNKNOWN_TYPE 7/246、QUERY_AND_GET_DELAY_RELEASE_ADD 5/246…），使各类轮廓趋同、
# cosine 分不开。故在检索期按候选池的 df 做 IDF 重加权（df 是语料相对的，不能烘进
# 持久化轮廓），并剔除哈希/UUID 噪声 token。置 False 即退回纯 TF 行为（消融开关）。
LOG_SEMANTIC_IDF = True
# 噪声 token：32 位十六进制哈希 / UUID（含 T: 前缀），跨现场不可能一致。
LOG_SEMANTIC_NOISE_RE = re.compile(r"^(?:[Tc]:)?[0-9A-Fa-f]{16,}$")

# v2.8 码→标签先验通道（实验性，默认关闭）：统计候选池内「日志语义码 → 一级标签」
# 分布，对查询侧语义码投票出最可能的一级标签，命中该标签的候选按得票占比加分。设计
# 意图是与 cosine 通道互补（cosine 在「轮廓饱和」时并列、加同常数不改次序）。
# 1112 文档集 LOO 复评（139 条带轮廓查询）结论为**负**：投票标签本身命中真值仅 64.7%
# （泛码 URMA_WRITE/E112/RPC peer dead 横跨硬件/Worker，票只落在两个大类上），全量
# top1 72.2%→68.0%（误伤 11/救回 3）；仅用「判别码」（纯度≥0.8）时为中性、且只覆盖
# 25% 查询；加置信门限（票占比≥0.7）时 +1 条（噪声内）。故默认关闭、暂不启用，仅留作
# 后续在时间留出池上复评的开关。
LOG_SEMANTIC_PRIOR_ENABLED = False
LOG_SEMANTIC_PRIOR_WEIGHT = 0.2


def _log_semantic_asset() -> dict:
    """懒加载日志语义码轮廓资产；缺失或损坏时返回空（通道自动关闭，不影响其余打分）。"""
    global _LOG_SEMANTIC_CACHE
    if _LOG_SEMANTIC_CACHE is None:
        try:
            with open(LOG_SEMANTIC_ASSET, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            data = {}
        _LOG_SEMANTIC_CACHE = data if isinstance(data, dict) else {}
    return _LOG_SEMANTIC_CACHE


def _log_semantic_cosine(query_profile: dict | None, case_profile: dict | None) -> float:
    """两个已归一化单位向量的点积（等价 cosine）；任一为空返回 0。"""
    if not query_profile or not case_profile:
        return 0.0
    if len(query_profile) > len(case_profile):
        query_profile, case_profile = case_profile, query_profile
    return sum(weight * case_profile.get(key, 0.0) for key, weight in query_profile.items())


def _log_semantic_idf(profiles: list[dict]) -> dict[str, float]:
    """按候选池统计每个码的 IDF：idf = ln(N/df) + 1。

    出现越普遍的码（E112、URMA_WRITE…）权重越低，稀疏且集中的码（UNKNOWN_TYPE、
    QUERY_AND_GET_DELAY_RELEASE_ADD…）权重越高。无候选时返回空（等价不重加权）。
    """
    total = len(profiles)
    if not total:
        return {}
    df: Counter = Counter()
    for profile in profiles:
        for key in profile:
            df[key] += 1
    return {key: math.log(total / count) + 1.0 for key, count in df.items()}


def _log_semantic_reweight(profile: dict | None, idf: dict[str, float]) -> dict | None:
    """按 IDF 重加权并剔除噪声 token，重新归一化为单位向量；空轮廓原样返回。"""
    if not profile:
        return profile
    weighted: dict[str, float] = {}
    for key, value in profile.items():
        if LOG_SEMANTIC_NOISE_RE.match(key):
            continue
        weighted[key] = value * idf.get(key, 1.0)
    norm = math.sqrt(sum(v * v for v in weighted.values()))
    if not norm:
        return None
    return {key: value / norm for key, value in weighted.items()}


def _log_semantic_prior(
    labeled_profiles: list[tuple[dict | None, str | None]],
    query_profile: dict | None,
) -> tuple[str | None, float]:
    """统计候选池「日志语义码 → 一级标签」分布，对查询侧语义码投票。

    每个码对某标签的贡献 = P(label|code) × 查询侧该码权重，再加权求和；权重取查询
    轮廓里该码的现值（已归一化的 TF/IDF），故稀疏判别码比泛码更能左右投票。返回
    (预测标签, 该标签得票占比 0~1)；无有效票返回 (None, 0.0)。
    """
    dist: dict[str, Counter] = {}
    for profile, label in labeled_profiles:
        if not profile or not label:
            continue
        for code in profile:
            dist.setdefault(code, Counter())[label] += 1
    if not dist or not query_profile:
        return None, 0.0
    votes: Counter = Counter()
    for code, weight in query_profile.items():
        counts = dist.get(code)
        if not counts:
            continue
        total = sum(counts.values())
        for label, count in counts.items():
            votes[label] += weight * count / total
    if not votes:
        return None, 0.0
    total = sum(votes.values())
    label, count = votes.most_common(1)[0]
    return label, count / total


def _query_log_semantic_profile(soft: dict) -> dict | None:
    """查询侧轮廓：优先用特征 JSON 内联的自带轮廓，其次按 log_id / kb_name 查静态资产。"""
    inline = soft.get("log_semantic_profile")
    if inline:
        return inline
    log_id = soft.get("log_id")
    if log_id:
        profile = (_log_semantic_asset().get("by_log_id") or {}).get(str(log_id))
        if profile:
            return profile
    kb_name = soft.get("kb_name")
    if kb_name:
        return (_log_semantic_asset().get("by_kb_name") or {}).get(kb_name) or None
    return None


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
    """把特征 JSON 转成软匹配特征（值 + 贡献占比 share）。

    status_codes 只装本次日志真实出现的码；relaxed_status_codes 装 Agent 为未见码
    选定的相近已知码（由 suggest_similar_codes.py 产出），以 0.5 降权并入软打分，
    但不参与用户使用问题硬判定。
    """
    status_codes = _values_with_shares(features, "status_codes", "status_code_shares")
    real = {item["value"] for item in status_codes}
    relaxed = [
        {"value": _normalize(code), "share": RELAXED_STATUS_CODE_SHARE}
        for code in (features.get("relaxed_status_codes") or [])
        if str(code).strip() and _normalize(code) not in real
    ]
    return {
        "status_codes": status_codes + relaxed,
        "relaxed_status_codes": relaxed,
        "failure_mode_ids": _values_with_shares(features, "failure_mode_ids", None),
        "latency_components": _values_with_shares(features, "latency_components", "latency_component_shares"),
        "log_keywords": _values_with_shares(features, "log_keywords", None),
        "operation": _normalize_operation(features["operation"]) if features.get("operation") else None,
        "time_shape": _normalize(features["time_shape"]) if features.get("time_shape") else None,
        "affected_scope": _normalize(features["affected_scope"]) if features.get("affected_scope") else None,
        # 保守版仅 link_pair 参与打分；其余形状（bi_pair/conc/spread）案例侧暂无法提取，置空不参与。
        "topology_shape": "link_pair" if _normalize(features["topology_shape"]) == "link_pair" else None,
        # 日志语义码通道的查询侧索引（见 LOG_SEMANTIC_*）：优先 log_id，回退报告 basic_info.kb_name。
        "log_id": str(features.get("log_id") or "").strip() or None,
        "kb_name": (
            str(features.get("kb_name") or (features.get("basic_info") or {}).get("kb_name") or "").strip()
            or None
        ),
        # 文档 / 特征 JSON 自带的日志语义码轮廓（内联优先），缺失再回退静态资产。
        "log_semantic_profile": (
            features.get("log_semantic_profile")
            or (features.get("basic_info") or {}).get("log_semantic_profile")
            or None
        ),
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


def _user_usage_hit(features: dict) -> list[str]:
    """查询侧**真实**错误码命中的用户使用问题码（相近码不参与判定）。"""
    values = {_normalize(code) for code in (features.get("status_codes") or [])}
    return sorted(values & USER_USAGE_FAULT_CODES, key=lambda v: (len(v), v))


def _build_recall_query(features: dict, source: str = SOURCE_LIBRARY, user_usage: bool = False) -> dict:
    """构建宽召回查询：只带过滤头（kb_id/fault_type/min_confidence/operation），
    不带任何匹配信号——服务端按过滤条件返回候选，软打分在本脚本完成。

    返回的是单页请求参数（page_cnt 为分页大小）；实际按页收满全部候选由
    _search_all 负责，故 page_num/page_cnt 这里只作为初值。

    library 通道 kb_id 可选（留空 = 跨知识库召回）；operation 服务端过滤默认关闭，
    仅当 OPERATION_FILTER_ENABLED 开启（--operation-filter）时才下发；legacy 通道
    kb_id 必填（旧表不支持 operation 过滤，只作正文标注）。

    user_usage=True 时额外锁定一级/二级标签为 用户相关故障/使用问题，命中该规则的
    故障只召回同类案例（当前案例库该类为 0 条，检索结果即为空，符合"严格只召回"口径）。
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
        if OPERATION_FILTER_ENABLED and operation and str(operation).strip():
            query["operation"] = _normalize_operation(operation)
        if user_usage:
            query["first_level_label"] = USER_USAGE_FIRST_LEVEL
            query["second_level_label"] = USER_USAGE_SECOND_LEVEL

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


def _domain_prior(matches: list[dict], soft: dict) -> tuple[str | None, float]:
    """从候选池统计「特征值→一级标签」分布，对查询真实特征投票出最可能的一级标签。

    两个通道：status_codes（主，权重 0.5）与 failure_mode_ids（辅，权重 0.1；LOO 网格实测
    仅小权重有正收益）。每个码/模式对某标签的贡献 = 该值在池里属于该标签的比例
    （行归一化 P(label|value)，即 n(值,标签)/n(值)）。票再按查询侧 share 加权，故 Agent
    折算的相近码（share=0.5）只发挥一半影响。返回 (预测标签, 该标签得票占比 0~1)；
    无有效票返回 (None, 0.0)。
    """
    dist_by_value: dict[str, dict[str, Counter]] = {key: {} for key in PRIOR_CHANNEL_WEIGHT}
    for match in matches:
        case = match.get("case") or {}
        label = case.get("first_level_label")
        if not label:
            continue
        for key in dist_by_value:
            for value in (case.get(key) or []):
                dist_by_value[key].setdefault(_normalize(value), Counter())[label] += 1
    votes: Counter = Counter()
    for key, channel_weight in PRIOR_CHANNEL_WEIGHT.items():
        for item in soft[key]:
            dist = dist_by_value[key].get(item["value"])
            if not dist:
                continue
            total = sum(dist.values())
            for label, count in dist.items():
                votes[label] += item["share"] * channel_weight * count / total
    if not votes:
        return None, 0.0
    total = sum(votes.values())
    label, count = votes.most_common(1)[0]
    return label, count / total


def _soft_score(case: dict, soft: dict,
                prior: tuple[str | None, float] | None = None) -> tuple[float, float, dict[str, list[str]], int]:
    """对单个候选案例做分布特征软打分。

    返回 (raw, norm, matched_by_level, matched_count)。norm 在 0~1 之间：
    raw = Σ(命中特征 base×share)；norm = raw / Σ(全部查询特征 base×share)。
    status_codes 用 F1（精度×召回）计分；prior 为错误码→故障域先验（见 _domain_prior）。
    """
    matched: dict[str, list[str]] = {"L1": [], "L2": [], "L5": []}
    raw = 0.0

    def _list_hit(feature_items: list[dict], case_field: str, level: str, label: str,
                  use_f1: bool = False) -> None:
        nonlocal raw
        case_values = {_normalize(value) for value in (case.get(case_field) or [])}
        hits = [item for item in feature_items if item["value"] in case_values]
        if not hits:
            return
        if use_f1 and case_values:
            precision = len(hits) / len(case_values)
            recall = len(hits) / len(feature_items) if feature_items else 0.0
            score = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
            raw += SOFT_WEIGHT[label] * score
        else:
            for item in hits:
                raw += SOFT_WEIGHT[label] * item["share"]
        for item in hits:
            matched[level].append(f"{label}={item['value']}(share={item['share']})")

    _list_hit(soft["status_codes"], "status_codes", "L1", "status_code", use_f1=True)
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

    # 错误码→故障域先验：命中候选池投票出的最可能一级标签 → 注入正交加分，打破并列。
    prior_denom = 0.0
    if prior and prior[0]:
        prior_denom = DOMAIN_PRIOR_WEIGHT
        if case.get("first_level_label") == prior[0]:
            raw += DOMAIN_PRIOR_WEIGHT * prior[1]
            matched["L1"].append(f"domain_prior={prior[0]}(p={prior[1]:.2f})")

    denominator = (
        sum(SOFT_WEIGHT["status_code"] * item["share"] for item in soft["status_codes"])
        + sum(SOFT_WEIGHT["failure_mode_id"] * item["share"] for item in soft["failure_mode_ids"])
        + sum(SOFT_WEIGHT["latency_component"] * item["share"] for item in soft["latency_components"])
        + sum(SOFT_WEIGHT["log_keyword"] * item["share"] for item in soft["log_keywords"])
        + (SOFT_WEIGHT["operation"] if soft["operation"] else 0.0)
        + (SOFT_WEIGHT["time_shape"] if soft["time_shape"] else 0.0)
        + (SOFT_WEIGHT["affected_scope"] if soft["affected_scope"] else 0.0)
        + (SOFT_WEIGHT["topology_shape"] if soft["topology_shape"] else 0.0)
        + prior_denom
    )
    norm = raw / denominator if denominator else 0.0
    matched_count = len(matched["L1"]) + len(matched["L2"]) + len(matched["L5"])
    return raw, norm, matched, matched_count


def _fetch_log_semantic_profile(api_base: str, params: dict, timeout: int) -> dict:
    """按资产向后端现算日志语义码轮廓；失败返回 {}（不阻断检索）。

    用于查询侧资产无内联轮廓、也不在静态资产里时（新资产在线定界），使该通道
    无需任何人工步骤即可自动启用。``params`` 传 kb_name / log_id / kb_id（非空项）。
    """
    url = api_base.rstrip("/") + "/log_failure_event_result/log_semantic_profile"
    body = {k: v for k, v in params.items() if v}
    if not body:
        return {}
    try:
        resp = _http_json(url, body, timeout)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        return {}
    result = resp.get("result") if isinstance(resp, dict) else None
    profile = result.get("profile") if isinstance(result, dict) else None
    return profile if isinstance(profile, dict) else {}


def _search(api_base: str, query: dict, timeout: int, source: str = SOURCE_LIBRARY) -> dict:
    url = api_base.rstrip("/") + SOURCE_ENDPOINT[source] + "/search"
    body = _http_json(url, query, timeout)
    result = body.get("result") or {}
    return {"total": result.get("total", 0), "matches": result.get("matches") or []}


# 拉全口径的安全上限：正常库远小于此页数，仅防服务端 total 异常导致死循环。
SEARCH_MAX_PAGES = 200


def _search_all(api_base: str, query: dict, timeout: int, source: str = SOURCE_LIBRARY) -> dict:
    """按页收满全部候选（拉全），返回 {"total", "matches"}。

    宽召回不带匹配信号，单页返回的候选与查询无关，截断会盲删相关案例；
    故逐页翻到底，直到返回空页或收满 total。page_cnt 复用为分页大小。
    """
    page_size = max(1, int(query.get("page_cnt") or 100))
    collected: list[dict] = []
    total = 0
    page_num = 1
    while page_num <= SEARCH_MAX_PAGES:
        page_query = dict(query, page_num=page_num, page_cnt=page_size)
        payload = _search(api_base, page_query, timeout, source)
        total = payload["total"]
        batch = payload["matches"]
        collected.extend(batch)
        if not batch or len(collected) >= total:
            break
        page_num += 1
    return {"total": total, "matches": collected}


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
    prior = _domain_prior(matches, soft)
    rows: list[dict] = []
    for match in matches:
        case = match.get("case") or {}
        raw, norm, matched, matched_count = _soft_score(case, soft, prior)
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

    # v2.5 日志语义码通道 / v2.8 码→标签先验通道：都依赖两侧的日志轮廓。
    # 放在排序前，使其既影响排序也影响 label_vote 的 margin 判定（与 LOO 验证口径一致）。
    if LOG_SEMANTIC_ENABLED or LOG_SEMANTIC_PRIOR_ENABLED:
        query_profile = _query_log_semantic_profile(soft)
        if query_profile:
            fallback_profiles = _log_semantic_asset().get("by_case_id") or {}
            case_profiles = {
                (match.get("case") or {}).get("id"): (
                    (match.get("case") or {}).get("log_semantic_profile")
                    or fallback_profiles.get((match.get("case") or {}).get("id"))
                )
                for match in matches
            }
            if LOG_SEMANTIC_IDF:
                # v2.7：先按候选池 IDF 重加权（含噪声剔除），再算 cosine，压泛码、抬判别码。
                idf = _log_semantic_idf(
                    [profile for profile in case_profiles.values() if profile]
                )
                query_profile = _log_semantic_reweight(query_profile, idf)
                if query_profile:
                    case_profiles = {
                        case_id: _log_semantic_reweight(profile, idf)
                        for case_id, profile in case_profiles.items()
                    }
            if LOG_SEMANTIC_ENABLED and query_profile:
                for row in rows:
                    similarity = _log_semantic_cosine(query_profile, case_profiles.get(row["case_id"]))
                    row["log_semantic_sim"] = round(similarity, 4)
                    if similarity:
                        row["score_norm"] = round(row["score_norm"] + LOG_SEMANTIC_WEIGHT * similarity, 4)
            if LOG_SEMANTIC_PRIOR_ENABLED and query_profile:
                # v2.8：按池内码→一级标签分布投票，命中预测标签的候选加分（轮廓饱和时 cosine 失效）。
                labeled_profiles = [
                    (
                        case_profiles.get((match.get("case") or {}).get("id")),
                        (match.get("case") or {}).get("first_level_label"),
                    )
                    for match in matches
                ]
                sem_label, sem_prob = _log_semantic_prior(labeled_profiles, query_profile)
                if sem_label:
                    for row in rows:
                        row["log_semantic_prior"] = f"{sem_label}(p={sem_prob:.2f})"
                        if row["first_level_label"] == sem_label:
                            row["score_norm"] = round(
                                row["score_norm"] + LOG_SEMANTIC_PRIOR_WEIGHT * sem_prob, 4
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


def _label_vote(rows: list[dict], top_k: int = 4, margin: float = 0.05) -> dict:
    """topK 一级标签投票（混合决策，生产剔C口径 K 网格最优：K=4、margin=0.05 → 不含C 69.7%（131/188））。

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
        f"kb_id={query.get('kb_id') or '(未指定，跨知识库)'}  API total={total}（宽召回已拉全）"
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
    parser.add_argument("--page-cnt", type=int, default=100, help="分页大小（拉全时按此逐页收满），默认 100")
    parser.add_argument(
        "--operation-filter",
        action="store_true",
        help="启用服务端 operation 过滤（默认关闭：拉全后由 operation 特征软处理操作域）",
    )
    parser.add_argument("--timeout", type=int, default=30, help="单次请求超时（秒），默认 30")
    parser.add_argument(
        "--no-log-semantic",
        action="store_true",
        help="关闭日志语义码次级通道（默认为开启，用于消融对比）",
    )
    parser.add_argument(
        "--no-log-semantic-idf",
        action="store_true",
        help="日志语义码通道退回纯 TF（不按 IDF 重加权，用于消融对比）",
    )
    parser.add_argument(
        "--log-semantic-prior",
        action="store_true",
        help="启用「码→标签先验」通道（默认关闭：按池内 语义码→一级标签 分布投票加分）",
    )
    parser.add_argument("--json", dest="json_out", help="候选结果落盘路径")
    args = parser.parse_args(argv)

    global LOG_SEMANTIC_ENABLED, LOG_SEMANTIC_IDF, LOG_SEMANTIC_PRIOR_ENABLED, OPERATION_FILTER_ENABLED
    if args.no_log_semantic:
        LOG_SEMANTIC_ENABLED = False
    if args.no_log_semantic_idf:
        LOG_SEMANTIC_IDF = False
    if args.log_semantic_prior:
        LOG_SEMANTIC_PRIOR_ENABLED = True
    OPERATION_FILTER_ENABLED = args.operation_filter

    if args.hit:
        return _mark_hit(args.api_base, args.hit, args.timeout, args.source)
    if not args.features:
        parser.error("需要提供特征 JSON 路径，或使用 --hit CASE_ID")

    try:
        features = _load_features(args.features)
        soft = _extract_soft_features(features)
        user_usage_codes = _user_usage_hit(features)
        query = _build_recall_query(features, args.source, user_usage=bool(user_usage_codes))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"特征文件不可用: {error}", file=sys.stderr)
        return 2

    if user_usage_codes:
        print(
            f"命中用户使用问题规则（错误码 {'/'.join(user_usage_codes)}），"
            f"直接判定为 {USER_USAGE_FIRST_LEVEL}/{USER_USAGE_SECOND_LEVEL}，仅召回该标签案例"
        )

    if not _soft_feature_count(soft):
        print("警告: 特征文件未提供任何分布特征，软打分全部为 0（仍按 confidence/hit_count 排序）")

    # 查询侧日志语义码轮廓：优先用特征 JSON 内联；否则按 kb_id 向后端现算
    # （新资产尚未进离线资产时也能自动启用该通道，无需人工步骤）。
    if (
        (LOG_SEMANTIC_ENABLED or LOG_SEMANTIC_PRIOR_ENABLED)
        and not soft.get("log_semantic_profile")
        and _query_log_semantic_profile(soft) is None
    ):
        params = {
            "kb_name": soft.get("kb_name"),
            "log_id": soft.get("log_id"),
            "kb_id": features.get("kb_id"),
        }
        if any(params.values()):
            profile = _fetch_log_semantic_profile(args.api_base, params, args.timeout)
            if profile:
                soft["log_semantic_profile"] = profile
                label = params.get("kb_name") or params.get("log_id") or params.get("kb_id")
                print(f"已按资产 {label} 现算日志语义码轮廓（{len(profile)} 个语义项）")

    query["page_cnt"] = args.page_cnt
    try:
        payload = _search_all(args.api_base, query, args.timeout, args.source)
    except urllib.error.HTTPError as error:
        print(f"检索失败: HTTP {error.code} {error.reason}", file=sys.stderr)
        return 3
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"检索失败: {error}", file=sys.stderr)
        return 3

    if len(payload["matches"]) < payload["total"]:
        print(
            f"警告: 已达翻页上限 {SEARCH_MAX_PAGES} 页，仅拉回 "
            f"{len(payload['matches'])}/{payload['total']} 条候选",
            file=sys.stderr,
        )

    matches, dropped = _exclude_control_plane(payload["matches"])
    if dropped:
        print(
            f"已剔除 {dropped} 条 Coordinator/UB管控面 候选（不参与软打分与投票）；"
            f"API total={payload['total']}，实际候选 {len(matches)} 条"
        )
    if user_usage_codes and not matches:
        print(
            f"案例库暂无 {USER_USAGE_FIRST_LEVEL}/{USER_USAGE_SECOND_LEVEL} 案例，"
            "按「严格只召回」口径返回空候选（不回退到其他类别）"
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
                    "user_usage_codes": user_usage_codes,
                    "relaxed_status_codes": features.get("relaxed_status_codes") or [],
                    "fault_label_override": (
                        {"first_level_label": USER_USAGE_FIRST_LEVEL,
                         "second_level_label": USER_USAGE_SECOND_LEVEL}
                        if user_usage_codes else None
                    ),
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
