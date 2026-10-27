#!/usr/bin/env python3
"""从已保存的错误码时间聚合响应生成 faults[].error；不联网、不关联时延阶段。"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import sys


ENDPOINT = "/log_failure_event_result/list_time_aggregated_failure_events"
INTERVALS = {"second": 1, "minute": 60, "hour": 3600}
SCOPE_FIELDS = ("kb_id", "operation", "start_time", "end_time",
                "cluster_name", "host", "pod_ip", "src_ip", "dst_ip")
REQUEST_FIELDS = set(SCOPE_FIELDS) | {"interval", "sort_by", "sort_desc", "sort_fields", "page_num", "page_cnt"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _count(value, name):
    _require(type(value) is int and value >= 0, f"{name}: 必须为非负整数")
    return value


def _time(value):
    _require(isinstance(value, str), "时间须为无偏移事件时间字符串")
    result = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return result


def _stamp(value):
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _floor(value, seconds):
    epoch = datetime(1970, 1, 1)
    return epoch + timedelta(seconds=int((value - epoch).total_seconds() // seconds) * seconds)


def _request(req):
    _require(isinstance(req, dict) and not (set(req) - REQUEST_FIELDS), "request: 非对象或含接口不支持的参数")
    _require(isinstance(req.get("kb_id"), str) and req["kb_id"].strip(), "request.kb_id: 必填")
    _require(req.get("operation") in ("GET", "SET"), "request.operation: 必须显式区分 GET/SET")
    start, end = _time(req.get("start_time")), _time(req.get("end_time"))
    _require(start < end, "request: start_time 须早于 end_time")
    _require(req.get("interval", "minute") in INTERVALS, "request.interval: second/minute/hour")
    for name in ("page_num", "page_cnt"):
        _require(_count(req.get(name, 1 if name == "page_num" else 10), name) > 0, f"{name}: 须大于零")
    for name in SCOPE_FIELDS:
        _require(req.get(name) is None or isinstance(req[name], str), f"request.{name}: 须为字符串或 null")
    return start, end


def _signature(req):
    """仅页码可以不同；排序及 page_cnt 变化会造成跨页漏数/重复。"""
    return {**{key: req.get(key) for key in SCOPE_FIELDS},
            "interval": req.get("interval", "minute"), "page_cnt": req.get("page_cnt", 10),
            "sort_by": req.get("sort_by", "timestamp"), "sort_desc": req.get("sort_desc", False),
            "sort_fields": req.get("sort_fields") or []}


def _pages(pages):
    _require(isinstance(pages, list) and pages, "每套操作须有非空 pages[]")
    signature, total = None, None
    sources, rows, seen_pages, codes = [], {}, set(), set()
    for page in pages:
        _require(isinstance(page, dict), "page: 须为 request/response 对象")
        req, response = page.get("request"), page.get("response")
        start, end = _request(req)
        _require(isinstance(response, dict) and response.get("code") == 200
                 and isinstance(response.get("result"), dict), "只接受上游 code=200 的完整响应")
        result = response["result"]
        this_total = _count(result.get("total"), "result.total")
        sig = _signature(req)
        _require(signature is None or signature == sig, "分页请求的范围、操作、粒度、排序和 page_cnt 必须一致")
        _require(total is None or total == this_total, "分页 result.total 变化，请重新取得一致快照")
        signature, total = sig, this_total
        num, size = req.get("page_num", 1), req.get("page_cnt", 10)
        _require(num not in seen_pages, "重复页码，不得重复累计")
        seen_pages.add(num)
        events = result.get("events")
        _require(isinstance(events, list), "result.events: 须为数组")
        _require(len(events) == min(size, max(0, total - (num - 1) * size)),
                 "分页返回条数与 total/page_num/page_cnt 不符")
        err_codes = result.get("err_codes")
        _require(isinstance(err_codes, list) and all(isinstance(c, str) and c for c in err_codes),
                 "result.err_codes: 须为错误码字符串数组")
        codes.update(c for c in err_codes if c != "all")
        seconds = INTERVALS[sig["interval"]]
        for event in events:
            _require(isinstance(event, dict), "events[]: 须为对象")
            left, right = _time(event.get("start_time")), _time(event.get("end_time"))
            _require(_floor(left, seconds) == left and right - left == timedelta(seconds=seconds)
                     and left < end and right > start, "聚合桶边界、粒度或查询时间范围不符")
            _require(left not in rows, "分页中存在重复时间桶，不得重复累计")
            counts = event.get("status_code_cnt")
            _require(isinstance(counts, dict) and "all" in counts, "status_code_cnt: 须含 all")
            for code, count in counts.items():
                _require(isinstance(code, str) and code, "错误码须为非空字符串")
                _count(count, f"status_code_cnt.{code}")
                _require(code == "all" or code in err_codes, "时间桶错误码未列入 err_codes")
            _require(counts["all"] == sum(v for c, v in counts.items() if c != "all"),
                     "all 须等于逐码命中计数之和，不能作为去重失败请求数")
            rows[left] = {c: v for c, v in counts.items() if c != "all"}
        sources.append({"request": deepcopy(req), "response_path": "result.events",
                        "total_windows": total, "returned_windows": len(events)})
    _require(len(rows) <= total, "返回时间桶数超过 total")
    return signature, total, rows, codes, sources


def _breakdown(series, top_n, max_windows):
    _require(isinstance(series, dict) and not (set(series) - {"pages", "codes"}), "series[]: 仅支持 pages / codes")
    sig, total, rows, codes, sources = _pages(series.get("pages"))
    selected = series.get("codes")
    _require(selected is None or (isinstance(selected, list) and selected
             and all(isinstance(c, str) and c and c != "all" for c in selected)
             and len(selected) == len(set(selected))), "codes: 须为非空、去重的原始错误码数组，不含 all")
    selected_codes = set(selected) if selected is not None else codes
    complete = len(rows) == total
    totals = Counter({code: 0 for code in selected_codes})
    for counts in rows.values():
        totals.update({code: count for code, count in counts.items() if code in selected_codes})
    ranked = sorted(totals, key=lambda code: (-totals[code], code))[:top_n]
    total_count = sum(totals.values())
    other_codes = selected_codes - set(ranked)
    # 只对同一请求范围内的相邻原始桶求和，不抽点、不跨操作归并。
    start, end = _time(sig["start_time"]), _time(sig["end_time"])
    base = INTERVALS[sig["interval"]]
    origin = _floor(start, base)
    slots = math.ceil((end - origin).total_seconds() / base)
    factor = max(1, math.ceil(slots / max_windows))
    display_seconds = base * factor
    groups = {}
    for left, counts in rows.items():
        index = int((left - origin).total_seconds() // display_seconds)
        group = groups.setdefault(index, {"observed": 0, "counts": Counter()})
        group["observed"] += 1
        group["counts"].update({c: v for c, v in counts.items() if c in selected_codes})
    windows = []
    for index in range(math.ceil(slots / factor)):
        left = origin + timedelta(seconds=index * display_seconds)
        right = min(end, left + timedelta(seconds=display_seconds))
        expected = min(factor, slots - index * factor)
        group = groups.get(index)
        known = complete or (group is not None and group["observed"] == expected)
        counts = group["counts"] if group else Counter()
        observed_counts = {code: counts[code] if known or group else None for code in ranked}
        windows.append({"start_time": _stamp(max(left, start)), "end_time": _stamp(right),
                        "complete": known, "counts": observed_counts,
                        "other_count": sum(counts[c] for c in other_codes) if known or group else None})
    return {
        "operation": sig["operation"], "scope": {k: sig[k] for k in SCOPE_FIELDS if sig.get(k) is not None},
        "code_filter": deepcopy(selected), "unit": "trace_code_occurrence",
        "source": {"endpoint": ENDPOINT, "pages": sources},
        "coverage": {"complete": complete, "returned_windows": len(rows), "total_windows": total},
        "code_distribution": {"total_count": total_count,
            "items": [{"code": code, "count": totals[code],
                       "share_pct": round(totals[code] / total_count * 100, 6) if complete and total_count else None}
                      for code in ranked],
            "other_count": sum(totals[c] for c in other_codes)},
        "timeline": {"interval_seconds": display_seconds, "windows": windows},
    }


def build_error(snapshot, top_n=5, max_windows=48):
    """输入 series[]：每项为一种 operation 的真实分页响应，可选 codes 限定本故障。"""
    _require(type(top_n) is int and 1 <= top_n <= 10, "top_n: 1~10")
    _require(type(max_windows) is int and 1 <= max_windows <= 120, "max_windows: 1~120")
    _require(isinstance(snapshot, dict) and isinstance(snapshot.get("series"), list)
             and snapshot["series"], "须提供非空 series[]")
    result = {"breakdowns": [_breakdown(s, top_n, max_windows) for s in snapshot["series"]], "conclusion": ""}
    errors = validate_error(result)
    _require(not errors, "; ".join(errors))
    return result


def validate_error(error):
    """旧报告可省略；新块检查计数、分母、缺失窗口及来源隔离。"""
    if error is None or error == {}:
        return []
    try:
        _require(isinstance(error, dict) and not (set(error) - {"metrics", "breakdowns", "conclusion"}),
                 "error: 仅支持 metrics / breakdowns / conclusion")
        _require(isinstance(error.get("conclusion", ""), str), "conclusion: 须为字符串")
        metrics = error.get("metrics", [])
        _require(isinstance(metrics, list), "metrics: 须为数组")
        for metric in metrics:
            _require(isinstance(metric, dict) and isinstance(metric.get("label"), str)
                     and isinstance(metric.get("value"), str), "metrics[]: 须含 label/value 字符串")
        breakdowns = error.get("breakdowns")
        _require(isinstance(breakdowns, list) and breakdowns, "breakdowns: 须为非空数组")
        operations = set()
        for bd in breakdowns:
            _require(isinstance(bd, dict), "breakdowns[]: 须为对象")
            _require(not (set(bd) - {"operation", "scope", "code_filter", "unit", "source", "coverage", "code_distribution", "timeline"}),
                     "breakdowns[]: 含未定义字段；不承载时延阶段或业务失败率")
            op = bd.get("operation")
            _require(op in ("GET", "SET") and op not in operations, "breakdowns.operation: GET/SET 各一套，不得重复或混合")
            operations.add(op)
            _require(bd.get("unit") == "trace_code_occurrence", "unit: 须为 trace_code_occurrence（逐码命中次数）")
            scope, source, coverage = bd["scope"], bd["source"], bd["coverage"]
            _require(isinstance(scope, dict) and scope.get("operation") == op
                     and not (set(scope) - set(SCOPE_FIELDS)), "scope: 范围字段或 operation 不符")
            _require(source["endpoint"] == ENDPOINT and isinstance(source["pages"], list)
                     and source["pages"], "source: 须保留时间聚合接口及真实分页请求")
            signature, page_numbers, returned = None, set(), 0
            total = _count(coverage["total_windows"], "coverage.total_windows")
            for page in source["pages"]:
                req = page["request"]
                _request(req)
                _require(all(req.get(k) == scope.get(k) for k in SCOPE_FIELDS), "source.request 与 scope 范围不一致")
                sig = _signature(req)
                _require(signature is None or signature == sig, "source 分页范围、粒度、排序不一致")
                signature = sig
                num, size = req.get("page_num", 1), req.get("page_cnt", 10)
                _require(num not in page_numbers, "source 页码重复")
                page_numbers.add(num)
                _require(page["response_path"] == "result.events" and page["total_windows"] == total,
                         "source: 响应路径或 total 不一致")
                n = _count(page["returned_windows"], "source.returned_windows")
                _require(n == min(size, max(0, total - (num - 1) * size)), "source 分页返回条数不符")
                returned += n
            _require(type(coverage["complete"]) is bool and returned == coverage["returned_windows"] <= total
                     and coverage["complete"] == (returned == total), "coverage: 完整性或计数不符")
            dist, timeline = bd["code_distribution"], bd["timeline"]
            items = dist["items"]
            _require(isinstance(items, list) and len(items) <= 10, "code_distribution.items: 最多 10 个错误码")
            codes = [item["code"] for item in items]
            _require(all(isinstance(c, str) and c and c != "all" for c in codes)
                     and len(codes) == len(set(codes)), "code_distribution.code: 须为去重原始错误码，不含 all")
            selected = bd.get("code_filter")
            _require(selected is None or (isinstance(selected, list) and selected
                     and all(isinstance(c, str) and c and c != "all" for c in selected)
                     and len(selected) == len(set(selected)) and set(codes) <= set(selected)), "code_filter: 错误码选择不符")
            total_count = _count(dist["total_count"], "total_count")
            other_count = _count(dist["other_count"], "other_count")
            for item in items:
                count = _count(item["count"], "items.count")
                expected = round(count / total_count * 100, 6) if coverage["complete"] and total_count else None
                share = item.get("share_pct")
                _require(share is None if expected is None else type(share) in (int, float) and share == expected,
                         "share_pct: 须按同范围完整 total_count 计算；未知或零分母填 null")
            _require(sum(item["count"] for item in items) + other_count == total_count, "Top 错误码 + 其他 须等于 total_count")
            interval = _count(timeline["interval_seconds"], "timeline.interval_seconds")
            base = INTERVALS[signature["interval"]]
            _require(interval > 0 and interval % base == 0, "展示粒度须为原始粒度的整数倍")
            windows = timeline["windows"]
            _require(isinstance(windows, list) and 1 <= len(windows) <= 120, "timeline.windows: 1~120 个连续展示窗")
            _require(coverage["complete"] or any(w.get("complete") is False for w in windows),
                     "分页不全时不能把全部时间窗标成完整")
            start, end = _time(scope["start_time"]), _time(scope["end_time"])
            origin = _floor(start, base)
            _require(len(windows) == math.ceil((end - origin).total_seconds() / interval), "时间窗须覆盖完整查询范围")
            sums, other_sum = Counter(), 0
            for index, window in enumerate(windows):
                left = origin + timedelta(seconds=index * interval)
                _require(_time(window["start_time"]) == max(left, start)
                         and _time(window["end_time"]) == min(left + timedelta(seconds=interval), end),
                         "时间窗须连续、有序且与查询范围、展示粒度一致")
                _require(type(window["complete"]) is bool and (not coverage["complete"] or window["complete"]),
                         "窗口 complete 与整体 coverage 不符")
                counts = window["counts"]
                _require(isinstance(counts, dict) and set(counts) == set(codes), "时间窗错误码须与构成表一致")
                values = list(counts.values()) + [window["other_count"]]
                _require(all(v is None for v in values) or all(v is not None for v in values), "未知窗口所有计数须同时为 null")
                for value in values:
                    if value is None:
                        _require(not window["complete"], "完整窗口不能有未知计数")
                    else:
                        _count(value, "timeline.count")
                sums.update({code: value for code, value in counts.items() if value is not None})
                other_sum += window["other_count"] or 0
            _require(all(sums[item["code"]] == item["count"] for item in items)
                     and other_sum == other_count, "时间分布累计值须与错误码构成一致")
        return []
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        return [str(exc)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", help="series[].pages[] 请求/响应快照 JSON")
    parser.add_argument("output", help="可整体填入 faults[].error 的 JSON")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--max-windows", type=int, default=48)
    args = parser.parse_args(argv)
    try:
        result = build_error(json.loads(Path(args.snapshot).read_text(encoding="utf-8")), args.top_n, args.max_windows)
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        print(f"错误码分布提取失败: {exc}", file=sys.stderr)
        return 2
    print(f"已提取 {len(result['breakdowns'])} 套操作分布 → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
