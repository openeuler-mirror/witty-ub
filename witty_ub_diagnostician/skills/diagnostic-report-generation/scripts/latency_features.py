#!/usr/bin/env python3
"""从已保存的上游响应提取报告特征；不请求网络、不推测缺失测量。"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import json
import math
from pathlib import Path
import re


BUCKET_KEYS = {
    "GET": {"rpc_network", "rpc_queue", "query_meta", "urma", "data_worker",
            "cross_window", "residual", "urma_timeout"},
    "SET": {"set_urma_timeout", "set_no_evidence", "set_residual", "set_client", "set_worker"},
}
DISTRIBUTION_FIELDS = ("p50_ms", "p90_ms", "max_ms", "client_p50_ms", "client_p90_ms")
TRACE_FACT_FIELDS = ("is_anomalous", "host", "pod_ips", "src_ip", "dst_ip", "failure_codes")
STATS_REQUEST_FIELDS = {"kb_id", "log_id", "operation", "start_time", "end_time", "sample_cap"}
CORE_FIELDS = {
    "operation", "bucket_key", "metric_name", "source", "sample_cnt", "truncated", "sample_note",
    "trace_cnt", "normal_cnt", "anomalous_cnt", "bucket_share_pct", "anomalous_ratio_pct",
    "distribution", "tail_ratio_p90_p50", "note", "action", "top_traces",
    "baseline", "windows", "trace_source", "trace_coverage", "delta_p90_ms", "p90_amplification",
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value, name, integer=False):
    _require(type(value) in ((int,) if integer else (int, float))
             and math.isfinite(value) and value >= 0, f"{name}: 必须为非负有限数值")


def _ratio(numerator, denominator, scale=1):
    return round(numerator / denominator * scale, 6) if denominator > 0 else None


def _source(snapshot, endpoint, response_path):
    _require(isinstance(snapshot, dict), "快照须为 request/response 对象")
    response = snapshot.get("response")
    _require(isinstance(response, dict) and response.get("code") == 200
             and isinstance(response.get("result"), dict), "只接受上游 code=200 的完整响应")
    req = snapshot["request"]
    _require(isinstance(req, dict) and isinstance(req.get("kb_id"), str)
             and bool(req["kb_id"].strip()), "request.kb_id: 必填")
    return {"endpoint": endpoint, "request": deepcopy(req), "response_path": response_path}


def _bucket(snapshot, key):
    """只提取 /stats/stages 明确产出的字段；没有 P99、阈值或超时率。"""
    source = _source(snapshot, "/stats/stages", "result.items[0]")
    result = snapshot["response"]["result"]
    op = result["operation"]
    _require(op in BUCKET_KEYS and key in BUCKET_KEYS[op], "operation / bucket_key 不匹配")
    _require(snapshot["request"].get("operation") == op, "request.operation 必须显式填写且与响应一致")
    matches = [(i, row) for i, row in enumerate(result["items"]) if row["key"] == key]
    _require(len(matches) == 1, f"桶 {key}: 必须在响应中唯一存在")
    index, row = matches[0]
    total = result["sample_cnt"]
    _require(sum(item["trace_cnt"] for item in result["items"]) == total,
             "sample_cnt 必须等于所有互斥桶 trace_cnt 之和")
    features = {
        "operation": op, "bucket_key": key, "metric_name": row["metric_name"],
        "source": {**source, "response_path": f"result.items[{index}]"},
        "sample_cnt": total, "truncated": result["truncated"],
        "sample_note": result.get("note"),
        "trace_cnt": row["trace_cnt"], "normal_cnt": row["success_cnt"],
        "anomalous_cnt": row["fail_cnt"],
        "bucket_share_pct": _ratio(row["trace_cnt"], total, 100),
        "anomalous_ratio_pct": _ratio(row["fail_cnt"], row["trace_cnt"], 100),
        "distribution": {name: row.get(name) for name in DISTRIBUTION_FIELDS},
        "tail_ratio_p90_p50": None,
        "note": row.get("note"), "action": row.get("action"),
        "top_traces": deepcopy(row.get("top_traces", [])),
    }
    _check_core(features)
    p50, p90 = row.get("p50_ms"), row.get("p90_ms")
    if p50 is not None and p90 is not None:
        features["tail_ratio_p90_p50"] = _ratio(p90, p50)
    return features


def _check_core(f):
    _require(isinstance(f, dict), "features: 必须为对象")
    _require(not (set(f) - CORE_FIELDS), "features: 含未定义字段，不能增加没有来源的测量")
    op, key = f.get("operation"), f.get("bucket_key")
    _require(op in BUCKET_KEYS and key in BUCKET_KEYS[op], "operation / bucket_key 不匹配")
    source = f.get("source")
    _require(isinstance(source, dict) and source.get("endpoint") == "/stats/stages",
             "source.endpoint: 当前特征必须来自 /stats/stages")
    req = source.get("request")
    _require(isinstance(req, dict) and req.get("kb_id") and req.get("operation") == op,
             "source.request: 必须保留 kb_id 及一致的 operation")
    _require(not (set(req) - STATS_REQUEST_FIELDS), "source.request: 含 /stats/stages 不支持的参数")
    _require(isinstance(source.get("response_path"), str)
             and re.fullmatch(r"result\.items\[\d+\]", source["response_path"]),
             "source.response_path: 须为 result.items[i]")
    _require(isinstance(f.get("metric_name"), str) and f["metric_name"], "metric_name: 必填")
    for name in ("sample_cnt", "trace_cnt", "normal_cnt", "anomalous_cnt"):
        _number(f.get(name), name, integer=True)
    _require(f["normal_cnt"] + f["anomalous_cnt"] == f["trace_cnt"] <= f["sample_cnt"],
             "计数须满足 normal_cnt + anomalous_cnt = trace_cnt <= sample_cnt")
    _require(type(f.get("truncated")) is bool, "truncated: 必须为布尔值")
    dist = f.get("distribution")
    _require(isinstance(dist, dict) and not (set(dist) - set(DISTRIBUTION_FIELDS)),
             "distribution: 仅支持上游 P50/P90/max 及 Client P50/P90，不支持 P99")
    for name, value in dist.items():
        if value is not None:
            _number(value, f"distribution.{name}")
    for left, right in (("p50_ms", "p90_ms"), ("p90_ms", "max_ms"),
                        ("client_p50_ms", "client_p90_ms")):
        if dist.get(left) is not None and dist.get(right) is not None:
            _require(dist[left] <= dist[right], f"distribution: {left} 不得大于 {right}")
    expected = {
        "bucket_share_pct": _ratio(f["trace_cnt"], f["sample_cnt"], 100),
        "anomalous_ratio_pct": _ratio(f["anomalous_cnt"], f["trace_cnt"], 100),
    }
    for name, value in expected.items():
        _require(f.get(name) == value, f"{name}: 必须按明确分母计算；分母为零填 null")


def _window(source):
    req = source["request"]
    start, end = req.get("start_time"), req.get("end_time")
    _require(isinstance(start, str) and isinstance(end, str), "对照/时间序列须有完整 start_time/end_time")
    parsed = datetime.fromisoformat(start), datetime.fromisoformat(end)
    _require(all(t.tzinfo is None for t in parsed) and parsed[0] < parsed[1],
             "时间窗须为递增的无时区事件时间（Asia/Shanghai）")
    return parsed


def _compatible(current, other):
    for field in ("operation", "bucket_key", "metric_name"):
        _require(current[field] == other[field], f"对照的 {field} 必须一致")
    a, b = current["source"]["request"], other["source"]["request"]
    for field in ("kb_id", "log_id"):
        _require(a.get(field) == b.get(field), f"对照的 {field} 必须一致")


def _enrich_traces(f, snapshot):
    source = _source(snapshot, "/trace/list", "result.items")
    req = source["request"]
    for name in ("kb_id", "log_id", "operation", "start_time", "end_time"):
        _require(req.get(name) == f["source"]["request"].get(name), f"trace 查询的 {name} 必须与当前统计一致")
    ids = [t["trace_id"] for t in f["top_traces"]]
    _require(isinstance(req.get("trace_ids"), list) and set(ids) <= set(req["trace_ids"]),
             "trace 查询须显式包含当前桶的 top_traces trace_ids")
    _require({"topology", "failure_codes"} <= set(req.get("include", [])),
             "trace 查询须 include=[topology,failure_codes]")
    rows = snapshot["response"]["result"]["items"]
    _require(len({r["trace_id"] for r in rows}) == len(rows), "trace 响应含重复 trace_id")
    found = {r["trace_id"]: r for r in rows if r["trace_id"] in ids}
    for trace in f["top_traces"]:
        if trace["trace_id"] in found:
            row = found[trace["trace_id"]]
            _require(row.get("operation") == f["operation"], "trace 响应操作类型不匹配")
            trace.update({k: deepcopy(row[k]) for k in TRACE_FACT_FIELDS if k in row})
    f["trace_source"] = source
    f["trace_coverage"] = {
        "requested_cnt": len(ids), "returned_cnt": len(found),
        "missing_trace_ids": [tid for tid in ids if tid not in found],
    }


def build_features(snapshots):
    """输入 current/baseline/windows/traces 的 request+response 快照，输出按桶索引的特征。"""
    current = snapshots["current"]
    _source(current, "/stats/stages", "result.items[0]")
    result = current["response"]["result"]
    _require(result.get("operation") in BUCKET_KEYS, "仅支持 GET/SET 的上游统计")
    selected = snapshots.get("bucket_keys", [row["key"] for row in result["items"]])
    _require(isinstance(selected, list) and len(set(selected)) == len(selected)
             and set(selected) <= {row["key"] for row in result["items"]},
             "bucket_keys: 必须为当前响应已有桶 key 的不重复数组")
    output = {}
    for row in result["items"]:
        if row["key"] not in selected:
            continue
        f = _bucket(current, row["key"])
        if snapshots.get("baseline") is not None:
            base = _bucket(snapshots["baseline"], row["key"])
            _compatible(f, base)
            a, b = _window(f["source"]), _window(base["source"])
            _require(a[1] <= b[0] or b[1] <= a[0], "基线窗口不得与当前窗口重叠")
            now_p90, base_p90 = f["distribution"].get("p90_ms"), base["distribution"].get("p90_ms")
            base["delta_p90_ms"] = None
            base["p90_amplification"] = None
            if now_p90 is not None and base_p90 is not None:
                base["delta_p90_ms"] = round(now_p90 - base_p90, 6)
                base["p90_amplification"] = _ratio(now_p90, base_p90)
            f["baseline"] = base
        if snapshots.get("windows"):
            f["windows"] = []
            start, end = _window(f["source"])
            for snap in snapshots["windows"]:
                point = _bucket(snap, row["key"])
                _compatible(f, point)
                pstart, pend = _window(point["source"])
                _require(start <= pstart < pend <= end, "时间序列窗口须在当前窗口内")
                f["windows"].append(point)
            f["windows"].sort(key=lambda x: _window(x["source"])[0])
        if snapshots.get("traces") is not None:
            _enrich_traces(f, snapshots["traces"])
        errors = validate_features(f)
        _require(not errors, "; ".join(errors))
        output[row["key"]] = f
    return {"operation": result["operation"], "features_by_bucket": output}


def validate_features(f):
    """渲染前校验；数值/分母/GET-SET/证据来源缺失时阻止渲染。"""
    try:
        _check_core(f)
        dist = f["distribution"]
        expected = None
        if dist.get("p50_ms") is not None and dist.get("p90_ms") is not None:
            expected = _ratio(dist["p90_ms"], dist["p50_ms"])
        _require(f.get("tail_ratio_p90_p50") == expected, "tail_ratio_p90_p50: 必须为 P90/P50，零分母填 null")
        top = f.get("top_traces", [])
        _require(isinstance(top, list) and len(top) <= 5, "top_traces: 必须为最多 5 条的数组")
        ids = []
        for trace in top:
            _require(isinstance(trace, dict) and isinstance(trace.get("trace_id"), str)
                     and trace["trace_id"], "top_traces.trace_id: 必填字符串")
            _number(trace.get("evidence_ms"), "top_traces.evidence_ms")
            if trace.get("client_ms") is not None:
                _number(trace["client_ms"], "top_traces.client_ms")
            _require(trace.get("is_anomalous") is None or type(trace["is_anomalous"]) is bool,
                     "top_traces.is_anomalous: 须为布尔值或 null")
            for name in ("host", "src_ip", "dst_ip"):
                _require(trace.get(name) is None or isinstance(trace[name], str), f"top_traces.{name}: 须为字符串或 null")
            pods = trace.get("pod_ips")
            _require(pods is None or (isinstance(pods, list) and all(isinstance(p, str) for p in pods)),
                     "top_traces.pod_ips: 须为字符串数组或 null")
            codes = trace.get("failure_codes")
            _require(codes is None or isinstance(codes, list), "top_traces.failure_codes: 须为数组或 null")
            for code in codes or []:
                _require(isinstance(code, dict) and isinstance(code.get("code"), str),
                         "top_traces.failure_codes[].code: 须为字符串")
                _number(code.get("cnt"), "top_traces.failure_codes[].cnt", integer=True)
            if any(k in trace for k in TRACE_FACT_FIELDS):
                _require("trace_source" in f and "trace_coverage" in f, "拓扑/错误码须附 trace_source 和 trace_coverage")
            ids.append(trace["trace_id"])
        _require(len(ids) == len(set(ids)), "top_traces.trace_id: 不得重复")
        if "trace_source" in f or "trace_coverage" in f:
            src, cov = f["trace_source"], f["trace_coverage"]
            _require(src["endpoint"] == "/trace/list" and src["response_path"] == "result.items",
                     "trace_source: 必须来自 /trace/list result.items")
            for name in ("kb_id", "log_id", "operation", "start_time", "end_time"):
                _require(src["request"].get(name) == f["source"]["request"].get(name), f"trace_source.request.{name}: 范围不一致")
            _require(set(ids) <= set(src["request"]["trace_ids"]), "trace_source: 未指定全部 Top trace ID")
            _require({"topology", "failure_codes"} <= set(src["request"].get("include", [])), "trace_source: 缺少 include")
            _number(cov["requested_cnt"], "trace_coverage.requested_cnt", integer=True)
            _number(cov["returned_cnt"], "trace_coverage.returned_cnt", integer=True)
            missing = cov["missing_trace_ids"]
            _require(isinstance(missing, list) and len(set(missing)) == len(missing)
                     and set(missing) <= set(ids) and cov["requested_cnt"] == len(ids)
                     and cov["returned_cnt"] == len(ids) - len(missing), "trace_coverage: 计数/缺失 ID 不一致")
            _require(not any(any(k in trace for k in TRACE_FACT_FIELDS)
                             for trace in top if trace["trace_id"] in missing),
                     "未返回的 Top trace 不得填写拓扑或错误码")
        if f.get("baseline") is not None:
            base = f["baseline"]
            _require(not any(k in base for k in ("baseline", "windows")), "baseline: 不允许嵌套对照")
            _require(not validate_features(base), "baseline: 特征校验失败")
            _compatible(f, base)
            a, b = _window(f["source"]), _window(base["source"])
            _require(a[1] <= b[0] or b[1] <= a[0], "baseline: 窗口与当前重叠")
            current, previous = dist.get("p90_ms"), base["distribution"].get("p90_ms")
            delta = round(current - previous, 6) if current is not None and previous is not None else None
            amp = _ratio(current, previous) if current is not None and previous is not None else None
            _require(base.get("delta_p90_ms") == delta and base.get("p90_amplification") == amp,
                     "baseline: P90 差值/放大倍数不一致")
        if f.get("windows") is not None:
            _require(isinstance(f["windows"], list), "windows: 必须为数组")
            start, end = _window(f["source"])
            previous_end = start
            for point in f["windows"]:
                _require(not any(k in point for k in ("baseline", "windows")), "windows: 不允许嵌套对照")
                _require(not validate_features(point), "windows: 特征校验失败")
                _compatible(f, point)
                pstart, pend = _window(point["source"])
                _require(previous_end <= pstart < pend <= end, "windows: 须有序、无重叠且位于当前窗口内")
                previous_end = pend
        return []
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        return [str(exc)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="上游 request+response 快照 JSON（格式见 LATENCY_FEATURES.md）")
    parser.add_argument("output", help="按桶索引的特征 JSON；取所需桶填入 stages[].features")
    args = parser.parse_args(argv)
    try:
        result = build_features(json.loads(Path(args.input).read_text(encoding="utf-8")))
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        parser.exit(2, f"特征提取失败: {exc}\n")
    print(f"已提取 {result['operation']} {len(result['features_by_bucket'])} 个桶 → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
