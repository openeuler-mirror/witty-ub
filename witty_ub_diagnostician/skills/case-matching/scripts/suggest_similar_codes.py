#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""未见故障码 → 相近已知码建议器。

场景：新日志里出现了案例库从未收录过的故障码。案例库的检索特征是按
status_codes 匹配的，直接拿未见码去召回必然空转。本脚本按「含义 + 分类」
给出该码的语义，并按三个依据推荐库内**已有案例**的相近码，供 Agent 选定后
写入检索特征的 relaxed_status_codes（0.5 降权参与软打分）。

判定依据与优先级（高→低）：
  1. 人工映射表  references/similar_code_map.json（可随手修订，直接覆盖）
  2. 同码段家族  通用[0,39] / RPC传输[1000,1012] / 对象[2000,2009] / 流[3000,3010] / 异构设备[5000,5004]
  3. 同知识库故障域  kvcache_failure_mode.json 里 错误码→故障域

含义来源：data/kvcache/kvcache_error_code_info.json（故障现象/故障原因）。
已知码来源：案例库 API（diag_case_library/search），即真正有案例可召回的码。

用法：
  python3 suggest_similar_codes.py --codes "1005,1007"
  python3 suggest_similar_codes.py --features /tmp/features.json
  python3 suggest_similar_codes.py --features /tmp/features.json --pick "1004,1009" --apply
  python3 suggest_similar_codes.py --codes 1005 --json /tmp/similar.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter

DEFAULT_API_BASE = os.environ.get("WITTY_API_BASE", "http://127.0.0.1:9772")
SEARCH_ENDPOINT = "/diag_case_library/search"
PAGE_CNT = 100
MAX_PAGES = 30

# 码段家族：覆盖 status.h 的全部码段
SEGMENTS: tuple[tuple[int, int, str], ...] = (
    (0, 39, "通用"),
    (1000, 1012, "RPC/传输"),
    (2000, 2009, "对象"),
    (3000, 3010, "流"),
    (5000, 5004, "异构设备"),
)

MAX_CANDIDATES = 5


def _repo_root() -> str:
    """脚本位于 <repo>/witty_ub_diagnostician/skills/case-matching/scripts/。"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def _data_dir() -> str:
    witty_dir = os.environ.get("WITTY_DIR") or _repo_root()
    return os.path.join(witty_dir, "data", "kvcache")


def _map_path() -> str:
    return os.path.join(os.path.dirname(__file__), "..", "references", "similar_code_map.json")


def _as_code(value: object) -> str:
    """故障码在特征里可能带前缀（如 code=1004），归一成纯数字串。"""
    text = str(value).strip()
    for sep in ("=", ":"):
        if sep in text:
            text = text.split(sep)[-1].strip()
    return text


def _segment_of(code: str) -> str | None:
    try:
        number = int(code)
    except ValueError:
        return None
    for low, high, name in SEGMENTS:
        if low <= number <= high:
            return name
    return None


def load_code_knowledge() -> dict[str, dict]:
    """故障码含义：{code: {"symptom":..., "root_cause":...}}。"""
    path = os.path.join(_data_dir(), "kvcache_error_code_info.json")
    try:
        raw = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"故障码知识文件不可用: {path}: {error}", file=sys.stderr)
        return {}
    return {
        str(code): {
            "symptom": info.get("故障现象", ""),
            "root_cause": info.get("故障原因", ""),
        }
        for code, info in raw.items()
        if isinstance(info, dict)
    }


def load_failure_domains() -> dict[str, set[str]]:
    """错误码 → 知识库故障域集合（同一个码可能挂在多条故障模式上）。"""
    path = os.path.join(_data_dir(), "kvcache_failure_mode.json")
    try:
        raw = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"故障模式知识文件不可用: {path}: {error}", file=sys.stderr)
        return {}
    domains: dict[str, set[str]] = {}
    for row in raw if isinstance(raw, list) else []:
        code = row.get("错误码")
        domain = str(row.get("故障域") or "").strip()
        if code is None or not domain:
            continue
        domains.setdefault(_as_code(code), set()).add(domain)
    return domains


def load_manual_map() -> dict[str, list[str]]:
    try:
        raw = json.load(open(_map_path(), encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    table = raw.get("map") if isinstance(raw, dict) else None
    if not isinstance(table, dict):
        return {}
    return {
        _as_code(code): [_as_code(v) for v in values if str(v).strip()]
        for code, values in table.items()
        if isinstance(values, list)
    }


def _http_json(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def load_known_codes(api_base: str, timeout: int) -> dict[str, dict]:
    """案例库里真正有案例的故障码：{code: {"cases": n, "labels": [...]}}。"""
    seen: dict[str, dict] = {}
    url = api_base.rstrip("/") + SEARCH_ENDPOINT
    for page in range(1, MAX_PAGES + 1):
        try:
            body = _http_json(url, {"page_num": page, "page_cnt": PAGE_CNT}, timeout)
        except (urllib.error.URLError, OSError, ValueError) as error:
            print(f"案例库 API 不可用: {error}", file=sys.stderr)
            break
        result = body.get("result") or {}
        matches = result.get("matches") or []
        for match in matches:
            case = match.get("case") or {}
            label = str(case.get("first_level_label") or "")
            for raw_code in case.get("status_codes") or []:
                code = _as_code(raw_code)
                if not code:
                    continue
                entry = seen.setdefault(code, {"cases": 0, "labels": Counter()})
                entry["cases"] += 1
                if label:
                    entry["labels"][label] += 1
        if page * PAGE_CNT >= int(result.get("total") or 0) or not matches:
            break
    return seen


def rank_candidates(
    code: str,
    known: dict[str, dict],
    knowledge: dict[str, dict],
    domains: dict[str, set[str]],
    manual: dict[str, list[str]],
) -> list[dict]:
    """按 人工映射表 > 同码段 > 同故障域 推荐相近的已知码。"""
    segment = _segment_of(code)
    code_domains = domains.get(code, set())
    ranked: list[dict] = []
    used: set[str] = set()

    for target in manual.get(code, []):
        if target in known and target not in used:
            used.add(target)
            ranked.append(_candidate(target, "人工映射表", "人工维护的等价/同类码", known, knowledge))

    for target, info in sorted(known.items(), key=lambda kv: (-kv[1]["cases"], kv[0])):
        if target in used or target == code or len(ranked) >= MAX_CANDIDATES:
            continue
        if segment and _segment_of(target) == segment:
            used.add(target)
            ranked.append(_candidate(target, f"同码段({segment})", "同一码段家族", known, knowledge))

    for target, info in sorted(known.items(), key=lambda kv: (-kv[1]["cases"], kv[0])):
        if target in used or target == code or len(ranked) >= MAX_CANDIDATES:
            continue
        shared = code_domains & domains.get(target, set())
        if shared:
            used.add(target)
            ranked.append(
                _candidate(target, f"同故障域({'/'.join(sorted(shared))})", "知识库故障域相同", known, knowledge)
            )

    return ranked[:MAX_CANDIDATES]


def _candidate(
    code: str, basis: str, reason: str, known: dict[str, dict], knowledge: dict[str, dict]
) -> dict:
    info = known.get(code) or {}
    labels = info.get("labels") or Counter()
    return {
        "code": code,
        "basis": basis,
        "reason": reason,
        "case_count": int(info.get("cases") or 0),
        "case_labels": [name for name, _ in labels.most_common(3)],
        "symptom": (knowledge.get(code) or {}).get("symptom", ""),
    }


def _collect_unseen(features: dict, known: dict[str, dict]) -> list[str]:
    codes = [_as_code(v) for v in (features.get("status_codes") or [])]
    return [code for code in dict.fromkeys(codes) if code and code not in known]


def _apply_picks(features_path: str, picks: list[str]) -> None:
    features = json.load(open(features_path, encoding="utf-8"))
    real = {_as_code(v) for v in (features.get("status_codes") or [])}
    merged = list(dict.fromkeys(
        [*(features.get("relaxed_status_codes") or []), *[p for p in picks if p not in real]]
    ))
    features["relaxed_status_codes"] = merged
    with open(features_path, "w", encoding="utf-8") as stream:
        json.dump(features, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="未见故障码 → 相近已知码建议")
    parser.add_argument("--codes", default="", help="待查的故障码，逗号分隔")
    parser.add_argument("--features", help="特征 JSON；自动取其中案例库未收录的码")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--pick", default="", help="与 --apply 搭配：Agent 选定的相近码，逗号分隔")
    parser.add_argument("--apply", action="store_true", help="把 --pick 写入--features 的 relaxed_status_codes")
    parser.add_argument("--json", dest="json_out", help="把建议写入 JSON 文件")
    args = parser.parse_args(argv)

    features: dict = {}
    if args.features:
        try:
            features = json.load(open(args.features, encoding="utf-8"))
        except (OSError, ValueError) as error:
            print(f"特征文件不可用: {error}", file=sys.stderr)
            return 2

    knowledge = load_code_knowledge()
    domains = load_failure_domains()
    manual = load_manual_map()
    known = load_known_codes(args.api_base, args.timeout)

    codes = [_as_code(c) for c in args.codes.split(",") if c.strip()]
    if not codes and features:
        codes = _collect_unseen(features, known)
    if not codes:
        print("未提供待查故障码，且特征中也没有案例库未收录的码")
        return 0

    report = {"known_code_vocabulary": sorted(known, key=lambda c: (len(c), c)), "items": []}
    for code in codes:
        if code in known:
            print(f"[{code}] 案例库已有 {known[code]['cases']} 个案例，无需相近码扩展")
            report["items"].append({"code": code, "known": True})
            continue
        info = knowledge.get(code, {})
        code_domains = sorted(domains.get(code, set()))
        candidates = rank_candidates(code, known, knowledge, domains, manual)
        report["items"].append({
            "code": code,
            "known": False,
            "symptom": info.get("symptom", ""),
            "root_cause": info.get("root_cause", ""),
            "failure_domains": code_domains,
            "segment": _segment_of(code),
            "candidates": candidates,
        })
        print(f"\n[{code}] 案例库未收录 码段={_segment_of(code) or '未知'} 故障域={code_domains or '未知'}")
        print(f"  故障现象: {info.get('symptom') or '（知识库无该码）'}")
        print(f"  故障原因: {info.get('root_cause') or '（知识库无该码）'}")
        if not candidates:
            print("  无可推荐的相近码（库内没有同码段/同故障域的案例）")
        for rank, item in enumerate(candidates, 1):
            print(
                f"  {rank}. {item['code']}  [{item['basis']}] 库内 {item['case_count']} 例"
                f" 标签={item['case_labels']} 现象={item['symptom'][:40]}"
            )
    print(
        "\n选中的码用 `--pick \"a,b\" --apply --features <特征文件>` 写入 relaxed_status_codes，"
        "检索时按 0.5 降权参与软打分。"
    )

    if args.pick and args.apply:
        if not args.features:
            print("--apply 需要同时给 --features", file=sys.stderr)
            return 2
        picks = [_as_code(c) for c in args.pick.split(",") if c.strip()]
        _apply_picks(args.features, picks)
        print(f"已写入 relaxed_status_codes={picks} → {args.features}")

    if args.json_out:
        json.dump(report, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"建议明细已写入 {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
