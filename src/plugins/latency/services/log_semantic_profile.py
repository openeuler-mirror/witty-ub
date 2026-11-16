# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""日志语义码轮廓：后端唯一的抽取实现。

「日志语义错误码轮廓」是案例检索的次级排序信号（见 case-matching Skill 的
``LOG_SEMANTIC_*`` 通道）：对某个资产/案例的 E/W 日志原文抽取语义错误码
（``code: [Not ready]``）与日志常量 token（``URMA_WAIT_TIMEOUT``、``E2001`` 等），
归一化为单位向量后做 cosine 比较。

轮廓随文档/案例一起持久化（报告的 ``basic_info.log_semantic_profile``、案例的
``diag_case_library.log_semantic_profile``），检索期直接读取，无需离线资产。
本模块同时提供 DB 兜底：文档未带该字段时，按 ``kb_name``/``log_id`` 现算。

抽取规则与权重必须与离线脚本
``witty_ub_diagnostician/skills/case-matching/scripts/build_log_semantic_profiles.py``
保持一致（语义码 ``C:`` 权重 1.0、常量 token ``T:`` 权重 3.0）。
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from latency.database.engine import PGManager

# 语义错误码：日志原文 `code: [Not ready]` / `msg: [...]; code: [X]`
CODE_RE = re.compile(r"code:\s*\[([^\]]+)\]")
# 日志常量 token：全大写下划线标识符（URMA_WAIT_TIMEOUT 等）
TOKEN_RE = re.compile(r"\b([A-Z][A-Z0-9_]{3,})\b")
# 错误码常量：E2001 / E112 等
ERRCODE_RE = re.compile(r"\bE\d{3,4}\b")
TOKEN_STOP = {"URMA", "RPC", "SHM", "UB", "TCP", "SLOW", "LOG", "ID"}

CODE_WEIGHT = 1.0
TOKEN_WEIGHT = 3.0
CODE_PREFIX = "C:"
TOKEN_PREFIX = "T:"

# 单次现算的日志原文条数上限：轮廓是词频统计，取前若干条失败日志已足够稳定，
# 也避免超长资产把建案事务拖慢。
MAX_EVENTS = 5000

_LEVELS = ("E", "W")


def build_profile(messages: list[str]) -> dict[str, float]:
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
    norm = math.sqrt(sum(value * value for value in counter.values()))
    if not norm:
        return {}
    return {key: round(value / norm, 6) for key, value in counter.items()}


def profile_from_basic(basic: dict[str, Any] | None) -> dict[str, float]:
    """读取报告 ``basic_info.log_semantic_profile``（文档自带轮廓），缺失返回 {}。"""
    if not isinstance(basic, dict):
        return {}
    raw = basic.get("log_semantic_profile")
    if not isinstance(raw, dict):
        return {}
    return _clean_profile(raw)


def _clean_profile(raw: dict[Any, Any]) -> dict[str, float]:
    """只保留 key:str / value:float 的合法项，丢弃脏数据。"""
    profile: dict[str, float] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        profile[key] = float(value)
    return profile


async def _resolve_log_ids(
    session: AsyncSession,
    kb_name: str | None,
    kb_id: str | None,
    log_id: str | None,
) -> list[str]:
    """解析资产对应的 log_id 列表。

    与离线生成器一致：``basic_info.kb_name`` 即 ``log_file.name``，优先按名解析；
    ``log_file.kb_id`` 可能为空（部分资产无归属），仅作兜底。
    """
    if log_id:
        return [log_id]
    if kb_name:
        result = await session.execute(
            text("SELECT id FROM log_file WHERE name = :name"),
            {"name": kb_name},
        )
        ids = [row for row in result.scalars().all()]
        if ids:
            return ids
    if kb_id:
        result = await session.execute(
            text("SELECT id FROM log_file WHERE kb_id = :kb_id"),
            {"kb_id": kb_id},
        )
        return [row for row in result.scalars().all()]
    return []


async def resolve_profile(
    kb_name: str | None = None,
    log_id: str | None = None,
    kb_id: str | None = None,
) -> dict[str, float]:
    """按资产现算日志语义码轮廓；无日志或无 E/W 事件时返回 {}。

    三个定位参数都缺省时直接返回 {}（通道自动关闭，无副作用）。
    """
    if not kb_name and not log_id and not kb_id:
        return {}
    async with PGManager.session() as session:
        log_ids = await _resolve_log_ids(session, kb_name, kb_id, log_id)
        if not log_ids:
            return {}
        rows = await session.execute(
            text(
                "SELECT coalesce(message, '') AS m, coalesce(raw_text, '') AS r "
                "FROM log_failure_event "
                "WHERE log_id = ANY(:log_ids) AND level = ANY(:levels) "
                "LIMIT :limit"
            ),
            {"log_ids": log_ids, "levels": list(_LEVELS), "limit": MAX_EVENTS},
        )
        messages = [row.m or row.r for row in rows]
    return build_profile(messages)
