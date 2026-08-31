#!/usr/bin/env python3
"""
统计 KVCache 接口日志中按毫秒的读写请求并发数，输出 HTML 文件。

用法:
    python para_cnt.py <日志文件夹目录> [--output OUTPUT]

示例:
    python para_cnt.py /data/logs --output report.html

日志文件格式: ds_client_access_*.log (或 .log.gz)
日志行格式:
    2026-04-12T09:00:00.123456 | E | urma_manager.cpp:347 | worker2-kvclient-2 | 5678:872 | trace-id | cluster-2 | 2 | DS_KV_CLIENT_GET | 2410 | 8388608 | message
    字段(以 | 分割): [0]时间 [3]pod名 [8]操作(GET=读 / SET=写)
"""

import argparse
import json
import sys
from pathlib import Path

import polars as pl


# ── 日志文件查找 ──────────────────────────────────────────────

def find_log_files(directory: str) -> list[Path]:
    """递归查找 ds_client_access_*.log(.gz) 文件"""
    base = Path(directory)
    files: list[Path] = []
    for pat in ("ds_client_access_*.log", "ds_client_access_*.log.gz"):
        files.extend(base.rglob(pat))
    return sorted(set(files))


# ── 单文件解析 ────────────────────────────────────────────────

def _process_file(path: Path) -> pl.DataFrame:
    """处理单个日志文件，返回 (ts_ms, pod, read, write) 聚合 DataFrame。

    使用 Polars scan_csv 以 \x01 为分隔符读取整行（\x01 不出现在文本日志中），
    再按 "|" 分割提取字段，等价于 Python line.split("|")。
    """
    lf = pl.scan_csv(
        str(path),
        separator="\x01",          # 不会出现在日志中的单字节分隔符
        has_header=False,
        new_columns=["line"],
        quote_char=None,            # 禁用引号处理，避免日志中的 " 干扰
        encoding="utf8-lossy",      # 等价于 errors='replace'
    )

    # 快速过滤：有效日志行以 "2" 开头（年份 2000+）
    lf = lf.filter(pl.col("line").str.starts_with("2"))

    # 按 "|" 分割并提取字段 [0]时间 [3]pod [8]操作
    lf = lf.with_columns(
        pl.col("line").str.split("|").alias("parts"),
    )
    lf = lf.with_columns(
        pl.col("parts").list.get(0, null_on_oob=True).str.strip_chars().alias("ts_str"),
        pl.col("parts").list.get(3, null_on_oob=True).str.strip_chars().alias("pod"),
        pl.col("parts").list.get(8, null_on_oob=True).str.strip_chars().alias("op"),
    )

    # 过滤：字段非空 + 操作为 GET/SET
    lf = lf.filter(
        pl.col("ts_str").is_not_null() & (pl.col("ts_str") != "")
        & pl.col("pod").is_not_null() & (pl.col("pod") != "")
        & pl.col("op").is_in(["DS_KV_CLIENT_GET", "DS_KV_CLIENT_SET"])
    )

    # 解析时间戳：自动检测格式，兼容 T/空格分隔符及带/不带小数秒
    lf = lf.with_columns(
        pl.col("ts_str").str.to_datetime(strict=False).alias("ts_dt")
    )
    lf = lf.filter(pl.col("ts_dt").is_not_null())

    # 转为 epoch 毫秒（截断微秒）
    lf = lf.with_columns(
        pl.col("ts_dt").dt.epoch(time_unit="ms").cast(pl.Int64).alias("ts_ms")
    )

    # 标记读/写
    lf = lf.with_columns(
        pl.when(pl.col("op") == "DS_KV_CLIENT_GET").then(1).otherwise(0).cast(pl.Int32).alias("read"),
        pl.when(pl.col("op") == "DS_KV_CLIENT_SET").then(1).otherwise(0).cast(pl.Int32).alias("write"),
    )

    # 按 (毫秒, pod) 聚合
    return lf.group_by(["ts_ms", "pod"]).agg(
        pl.sum("read").alias("read"),
        pl.sum("write").alias("write"),
    ).collect()


# ── 全量解析与聚合 ─────────────────────────────────────────────

def parse_and_aggregate(files: list[Path]) -> pl.DataFrame:
    """解析所有日志文件并跨文件聚合"""
    frames: list[pl.DataFrame] = []
    for f in files:
        try:
            agg = _process_file(f)
            if agg.height > 0:
                frames.append(agg)
                print(f"  已处理: {f.name} ({agg.height} 条聚合记录)")
        except Exception as e:
            print(f"  警告: 跳过文件 {f}: {e}", file=sys.stderr)

    if not frames:
        return pl.DataFrame(schema={
            "ts_ms": pl.Int64, "pod": pl.Utf8, "read": pl.Int32, "write": pl.Int32,
        })

    # 跨文件二次聚合
    return (
        pl.concat(frames, how="vertical_relaxed")
        .group_by(["ts_ms", "pod"])
        .agg(
            pl.sum("read").alias("read"),
            pl.sum("write").alias("write"),
        )
        .sort(["ts_ms", "pod"])
    )


# ── 输出数据构建 ──────────────────────────────────────────────

def build_output_data(agg_df: pl.DataFrame) -> dict:
    """将聚合 DataFrame 转为紧凑 JSON 结构供 HTML 嵌入"""
    if agg_df.is_empty():
        return {"minTs": 0, "maxTs": 0, "pods": [], "records": []}

    pods = agg_df.select("pod").unique().sort("pod").to_series().to_list()
    pod_index = {p: i for i, p in enumerate(pods)}

    min_ts = agg_df.select(pl.col("ts_ms").min()).item()
    max_ts = agg_df.select(pl.col("ts_ms").max()).item()

    # 使用 iter_rows(named=True) 降低内存占用（遵循项目约定）
    records = []
    for row in agg_df.iter_rows(named=True):
        records.append([row["ts_ms"], pod_index[row["pod"]], row["read"], row["write"]])

    return {"minTs": min_ts, "maxTs": max_ts, "pods": pods, "records": records}


# ── HTML 模板 ──────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KVCache 读写并发数统计</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0f172a;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:16px;min-height:100vh}
.controls{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-bottom:16px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}
.controls label{display:flex;align-items:center;gap:6px;font-size:13px;color:#94a3b8;white-space:nowrap}
.controls input,.controls select{background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:6px 10px;border-radius:4px;font-size:13px;outline:none}
.controls input:focus,.controls select:focus{border-color:#3b82f6}
.controls button{background:#3b82f6;border:none;color:#fff;padding:7px 16px;border-radius:4px;cursor:pointer;font-size:13px;transition:background .2s}
.controls button:hover{background:#2563eb}
.controls button.secondary{background:#475569}
.controls button.secondary:hover{background:#64748b}
.summary{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:13px;color:#94a3b8;line-height:1.8}
.summary strong{color:#e2e8f0}
.chart-group{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-bottom:16px}
.chart-group h3{color:#f1f5f9;font-size:16px;font-weight:600;margin-bottom:4px}
.chart-group h4{color:#94a3b8;font-size:13px;font-weight:400;margin-top:16px;margin-bottom:4px}
.chart{width:100%;height:400px}
.warning{color:#f59e0b;font-size:12px;margin:4px 0 12px;padding:8px 12px;background:rgba(245,158,11,.08);border-radius:4px}
.no-data{text-align:center;padding:64px;color:#64748b;font-size:16px}
</style>
</head>
<body>
<div class="controls">
<label>起始时间 <input type="datetime-local" id="start-time" step="0.001"></label>
<label>结束时间 <input type="datetime-local" id="end-time" step="0.001"></label>
<label>时间尺度
<select id="scale">
<option value="ms">毫秒</option>
<option value="10ms">10毫秒</option>
<option value="100ms">100毫秒</option>
<option value="s" selected>秒</option>
<option value="min">分</option>
<option value="h">时</option>
</select>
</label>
<label>聚合方法
<select id="agg">
<option value="pmax">pmax (峰值)</option>
<option value="avg">avg (平均)</option>
<option value="median">median (中位数)</option>
</select>
</label>
<button class="secondary" id="reset">重置时间范围</button>
<button id="download">下载统计数据 (CSV)</button>
</div>
<div class="summary" id="summary"></div>
<div id="warning" class="warning" style="display:none"></div>
<div class="chart-group">
<h3>读 + 写总和</h3>
<h4>所有节点总并发数</h4>
<div class="chart" id="chart-total-all"></div>
<h4>各 Pod 并发数分布</h4>
<div class="chart" id="chart-total-pod"></div>
</div>
<div class="chart-group">
<h3>读请求</h3>
<h4>所有节点总并发数</h4>
<div class="chart" id="chart-read-all"></div>
<h4>各 Pod 并发数分布</h4>
<div class="chart" id="chart-read-pod"></div>
</div>
<div class="chart-group">
<h3>写请求</h3>
<h4>所有节点总并发数</h4>
<div class="chart" id="chart-write-all"></div>
<h4>各 Pod 并发数分布</h4>
<div class="chart" id="chart-write-pod"></div>
</div>
<script>
const RAW_DATA = __DATA_PLACEHOLDER__;
(function(){
"use strict";

const pods = RAW_DATA.pods;
const records = RAW_DATA.records;

/* ── 构建毫秒级索引 ── */
const msTotal = new Map();   // ts -> {r, w, t}
const msPod   = new Map();   // ts -> Map<podIdx, {r, w, t}>
const sortedTs = [];

for (const rec of records) {
    const ts = rec[0], podIdx = rec[1], r = rec[2], w = rec[3], t = r + w;
    if (!msTotal.has(ts)) {
        msTotal.set(ts, {r:0, w:0, t:0});
        msPod.set(ts, new Map());
        sortedTs.push(ts);
    }
    const tot = msTotal.get(ts);
    tot.r += r; tot.w += w; tot.t += t;
    if (!msPod.get(ts).has(podIdx)) msPod.get(ts).set(podIdx, {r:0, w:0, t:0});
    const p = msPod.get(ts).get(podIdx);
    p.r += r; p.w += w; p.t += t;
}
sortedTs.sort(function(a, b){ return a - b; });

const minTs = RAW_DATA.minTs || (sortedTs.length ? sortedTs[0] : 0);
const maxTs = RAW_DATA.maxTs || (sortedTs.length ? sortedTs[sortedTs.length - 1] : 0);

/* ── 图表实例 ── */
const charts = {};
const chartIds = [
    "chart-total-all","chart-total-pod",
    "chart-read-all","chart-read-pod",
    "chart-write-all","chart-write-pod"
];

function initCharts() {
    for (const id of chartIds) charts[id] = echarts.init(document.getElementById(id));
    window.addEventListener("resize", function(){
        for (const id of chartIds) if (charts[id]) charts[id].resize();
    });
}

/* ── 时间格式化（使用 UTC 方法以匹配日志时间戳） ── */
function pad(n, l) { l = l || 2; return String(n).padStart(l, "0"); }

function tsParts(ts) {
    const d = new Date(ts);
    return {
        y:d.getUTCFullYear(), mo:d.getUTCMonth()+1, d:d.getUTCDate(),
        h:d.getUTCHours(), mi:d.getUTCMinutes(), s:d.getUTCSeconds(), ms:d.getUTCMilliseconds()
    };
}

function fmtLabel(ts, bucketSize) {
    const p = tsParts(ts);
    if (bucketSize >= 3600000) return pad(p.mo)+"-"+pad(p.d)+" "+pad(p.h)+":"+pad(p.mi);
    if (bucketSize >= 60000)   return pad(p.h)+":"+pad(p.mi)+":"+pad(p.s);
    if (bucketSize >= 1000)    return pad(p.h)+":"+pad(p.mi)+":"+pad(p.s);
    return pad(p.h)+":"+pad(p.mi)+":"+pad(p.s)+"."+pad(p.ms,3);
}

function fmtFull(ts) {
    const p = tsParts(ts);
    return p.y+"-"+pad(p.mo)+"-"+pad(p.d)+" "+pad(p.h)+":"+pad(p.mi)+":"+pad(p.s)+"."+pad(p.ms,3);
}

function tsToInput(ts) {
    const p = tsParts(ts);
    return p.y+"-"+pad(p.mo)+"-"+pad(p.d)+"T"+pad(p.h)+":"+pad(p.mi)+":"+pad(p.s)+"."+pad(p.ms,3);
}

function inputToTs(str) {
    if (!str) return null;
    var m = str.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?$/);
    if (!m) return null;
    var ms = m[7] ? parseInt(m[7].padEnd(3,"0"), 10) : 0;
    return Date.UTC(+m[1], +m[2]-1, +m[3], +m[4], +m[5], +m[6], ms);
}

/* ── 聚合函数 ── */
function aggregate(values, msCount, method) {
    if (method === "pmax") {
        var mx = 0;
        for (var i = 0; i < values.length; i++) if (values[i] > mx) mx = values[i];
        return mx;
    }
    if (method === "avg") {
        if (msCount === 0) return 0;
        var sum = 0;
        for (var i = 0; i < values.length; i++) sum += values[i];
        return sum / msCount;
    }
    // median：构造 [0]*(msCount-len) + sorted(values)，取中位数
    if (msCount === 0) return 0;
    var sorted = values.slice().sort(function(a,b){return a-b;});
    var zeros = msCount - sorted.length;
    function getVal(i) { return i < zeros ? 0 : (sorted[i - zeros] || 0); }
    if (msCount % 2 === 1) return getVal(Math.floor(msCount / 2));
    return (getVal(msCount/2 - 1) + getVal(msCount/2)) / 2;
}

/* ── 计算图表数据 ── */
var currentData = null;

function computeData(startTs, endTs, bucketSize, method) {
    var isMs = bucketSize === 1;
    var startBucket = Math.floor(startTs / bucketSize) * bucketSize;
    var endBucket   = Math.ceil(endTs / bucketSize) * bucketSize;

    var bucketCount = (endBucket - startBucket) / bucketSize;
    var warnEl = document.getElementById("warning");
    if (bucketCount > 50000) {
        warnEl.style.display = "block";
        warnEl.textContent = "警告: 当前时间尺度下约 " + bucketCount.toLocaleString() +
            " 个数据点，渲染可能较慢。建议使用更粗的时间尺度或缩小时间范围。";
    } else {
        warnEl.style.display = "none";
    }

    var buckets = new Map();
    function getBucket(b) {
        if (!buckets.has(b)) {
            buckets.set(b, {
                tV:[], rV:[], wV:[],
                pT:new Map(), pR:new Map(), pW:new Map(),
                mc:0
            });
        }
        return buckets.get(b);
    }

    // 预计算每个 bucket 的 msCount（数据范围内的毫秒数，含 0 值）
    if (!isMs) {
        for (var b = startBucket; b < endBucket; b += bucketSize) {
            var bEnd = b + bucketSize;
            var msStart = Math.max(b, startTs);
            var msEnd   = Math.min(bEnd, endTs);
            getBucket(b).mc = Math.max(0, msEnd - msStart);
        }
    }

    // 将数据点分配到各 bucket
    for (var ti = 0; ti < sortedTs.length; ti++) {
        var ts = sortedTs[ti];
        if (ts < startTs || ts >= endTs) continue;
        var bStart = Math.floor(ts / bucketSize) * bucketSize;
        var bk = getBucket(bStart);
        if (isMs) bk.mc = 1;

        var tot = msTotal.get(ts);
        if (tot) {
            if (tot.t > 0) bk.tV.push(tot.t);
            if (tot.r > 0) bk.rV.push(tot.r);
            if (tot.w > 0) bk.wV.push(tot.w);
        }

        var pm = msPod.get(ts);
        if (pm) {
            pm.forEach(function(vals, podIdx) {
                if (!bk.pT.has(podIdx)) {
                    bk.pT.set(podIdx, []);
                    bk.pR.set(podIdx, []);
                    bk.pW.set(podIdx, []);
                }
                if (vals.t > 0) bk.pT.get(podIdx).push(vals.t);
                if (vals.r > 0) bk.pR.get(podIdx).push(vals.r);
                if (vals.w > 0) bk.pW.get(podIdx).push(vals.w);
            });
        }
    }

    // 汇总输出
    var bStarts = Array.from(buckets.keys()).sort(function(a,b){return a-b;});
    var labels = bStarts.map(function(b){ return fmtLabel(b, bucketSize); });

    var result = {
        labels: labels, bucketStarts: bStarts, bucketSize: bucketSize,
        total: { all: [], pods: pods.map(function(){return [];}) },
        read:  { all: [], pods: pods.map(function(){return [];}) },
        write: { all: [], pods: pods.map(function(){return [];}) }
    };

    for (var bi = 0; bi < bStarts.length; bi++) {
        var bk = buckets.get(bStarts[bi]);
        var mc = bk.mc;
        result.total.all.push(aggregate(bk.tV, mc, method));
        result.read.all.push(aggregate(bk.rV, mc, method));
        result.write.all.push(aggregate(bk.wV, mc, method));
        for (var pi = 0; pi < pods.length; pi++) {
            result.total.pods[pi].push(aggregate(bk.pT.get(pi) || [], mc, method));
            result.read.pods[pi].push(aggregate(bk.pR.get(pi) || [], mc, method));
            result.write.pods[pi].push(aggregate(bk.pW.get(pi) || [], mc, method));
        }
    }
    return result;
}

/* ── 图表渲染 ── */
var COLORS = ["#3b82f6","#ef4444","#10b981","#f59e0b","#8b5cf6","#ec4899",
             "#06b6d4","#84cc16","#f97316","#6366f1","#14b8a6","#e11d48",
             "#a855f7","#0ea5e9","#22c55e","#f43f5e","#eab308","#64748b"];

function baseOption(labels) {
    return {
        animation: labels.length <= 300,
        tooltip: { trigger: "axis", appendToBody: true },
        grid: { top: 48, right: 24, bottom: 72, left: 62, containLabel: true },
        dataZoom: [
            { type: "inside", start: 0, end: 100 },
            { type: "slider", start: 0, end: 100, height: 20, bottom: 8 }
        ],
        xAxis: {
            type: "category", data: labels,
            axisLabel: { color: "#cbd5e1", fontSize: 10, rotate: 35, hideOverlap: true },
            axisLine: { lineStyle: { color: "#e2e8f0" } }
        },
        yAxis: {
            type: "value", min: 0, name: "请求数",
            nameTextStyle: { color: "#64748b" },
            axisLabel: { color: "#64748b", fontSize: 11 },
            splitLine: { lineStyle: { color: "#e2e8f0" } }
        }
    };
}

function renderAllChart(id, name, labels, values, color) {
    var opt = baseOption(labels);
    opt.tooltip.formatter = function(params) {
        var p = Array.isArray(params) ? params[0] : params;
        if (!p) return "";
        return '<div style="font-weight:600;margin-bottom:2px">' + p.axisValueLabel +
            '</div><div>' + name + ': <b style="color:' + color + '">' + p.value + "</b></div>";
    };
    opt.series = [{
        name: name, type: "line", data: values,
        showSymbol: false,
        lineStyle: { width: 1.5, color: color },
        itemStyle: { color: color },
        areaStyle: { opacity: 0.08, color: color },
        large: true, largeThreshold: 1000
    }];
    charts[id].setOption(opt, true);
}

function renderPodChart(id, name, labels, podsData) {
    var opt = baseOption(labels);
    opt.tooltip.order = "valueDesc";
    opt.tooltip.formatter = function(params) {
        var items = Array.isArray(params) ? params : [];
        if (!items.length) return "";
        var label = items[0].axisValueLabel;
        var filtered = [];
        var total = 0;
        for (var i = 0; i < items.length; i++) {
            if (typeof items[i].value === "number" && items[i].value > 0) {
                filtered.push(items[i]);
                total += items[i].value;
            }
        }
        filtered.sort(function(a,b){ return b.value - a.value; });
        var rows = "";
        for (var i = 0; i < filtered.length; i++) {
            var it = filtered[i];
            rows += '<div style="display:flex;justify-content:space-between;gap:16px;align-items:center;line-height:1.7">' +
                '<span><i style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' +
                it.color + ';margin-right:6px"></i>' + it.seriesName + "</span><b>" + it.value + "</b></div>";
        }
        return '<div style="font-weight:600;margin-bottom:4px">' + label +
            '</div><div style="margin-bottom:4px;color:#94a3b8">总计: <b style="color:#e2e8f0">' +
            total + "</b></div>" + rows;
    };
    opt.legend = {
        type: "scroll", top: 0, left: 8, right: 8,
        textStyle: { color: "#94a3b8", fontSize: 11 },
        data: pods
    };
    opt.series = pods.map(function(podName, i) {
        return {
            name: podName, type: "line", data: podsData[i],
            showSymbol: false,
            lineStyle: { width: 1 },
            itemStyle: { color: COLORS[i % COLORS.length] },
            large: true, largeThreshold: 1000
        };
    });
    charts[id].setOption(opt, true);
}

/* ── 主渲染 ── */
function renderCharts() {
    var sInput = document.getElementById("start-time");
    var eInput = document.getElementById("end-time");
    var scale  = document.getElementById("scale").value;
    var agg    = document.getElementById("agg").value;

    var startTs = inputToTs(sInput.value);
    var endTs   = inputToTs(eInput.value);

    // 校验并钳制到数据范围
    if (startTs === null || startTs < minTs) startTs = minTs;
    if (endTs === null || endTs > maxTs + 1) endTs = maxTs + 1;
    if (startTs >= endTs) { startTs = minTs; endTs = maxTs + 1; }

    var bucketSize = { ms: 1, "10ms": 10, "100ms": 100, s: 1000, min: 60000, h: 3600000 }[scale];

    currentData = computeData(startTs, endTs, bucketSize, agg);

    renderAllChart("chart-total-all", "总请求数", currentData.labels, currentData.total.all, "#3b82f6");
    renderAllChart("chart-read-all",  "读请求数", currentData.labels, currentData.read.all,  "#10b981");
    renderAllChart("chart-write-all", "写请求数", currentData.labels, currentData.write.all, "#f59e0b");

    renderPodChart("chart-total-pod", "读+写", currentData.labels, currentData.total.pods);
    renderPodChart("chart-read-pod",  "读",    currentData.labels, currentData.read.pods);
    renderPodChart("chart-write-pod", "写",    currentData.labels, currentData.write.pods);
}

/* ── CSV 下载 ── */
function downloadCSV() {
    if (!currentData) return;
    var groups = [
        { name: "read_write", all: currentData.total.all, pods: currentData.total.pods },
        { name: "read",       all: currentData.read.all,  pods: currentData.read.pods },
        { name: "write",      all: currentData.write.all, pods: currentData.write.pods }
    ];
    var agg = document.getElementById("agg").value;
    var scale = document.getElementById("scale").value;

    for (var gi = 0; gi < groups.length; gi++) {
        var g = groups[gi];
        var lines = [];
        var header = ["开始时间", "结束时间", "总并发数"];
        for (var pi = 0; pi < pods.length; pi++) header.push(pods[pi]);
        lines.push(header.join(","));

        for (var i = 0; i < currentData.labels.length; i++) {
            var bStart = currentData.bucketStarts[i];
            var bEnd   = bStart + currentData.bucketSize;
            var row = [fmtFull(bStart), fmtFull(bEnd), g.all[i]];
            for (var j = 0; j < pods.length; j++) row.push(g.pods[j][i]);
            lines.push(row.join(","));
        }

        var csv = "\ufeff" + lines.join("\n");
        var blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = g.name + "_" + scale + "_" + agg + ".csv";
        a.click();
        URL.revokeObjectURL(url);
    }
}

/* ── 初始化 ── */
function init() {
    if (!records.length) {
        document.body.innerHTML = '<div class="no-data">未找到有效的日志数据。<br>请检查日志文件格式（ds_client_access_*.log）及文件中是否包含 DS_KV_CLIENT_GET / DS_KV_CLIENT_SET 操作。</div>';
        return;
    }

    initCharts();

    var sInput = document.getElementById("start-time");
    var eInput = document.getElementById("end-time");
    var minStr = tsToInput(minTs);
    var maxStr = tsToInput(maxTs);
    sInput.min = minStr; sInput.max = maxStr; sInput.value = minStr;
    eInput.min = minStr; eInput.max = maxStr; eInput.value = maxStr;

    // 摘要信息
    var durSec = (maxTs - minTs) / 1000;
    var durStr = durSec >= 3600 ? (durSec / 3600).toFixed(1) + " 小时"
               : durSec >= 60   ? (durSec / 60).toFixed(1) + " 分钟"
               : durSec.toFixed(1) + " 秒";
    document.getElementById("summary").innerHTML =
        "数据范围: <strong>" + fmtFull(minTs) + "</strong> ~ <strong>" + fmtFull(maxTs) +
        "</strong> | 持续时间: <strong>" + durStr + "</strong> | Pod 数: <strong>" + pods.length +
        "</strong> | 毫秒时间点: <strong>" + sortedTs.length.toLocaleString() + "</strong>";

    // 事件绑定
    sInput.addEventListener("change", renderCharts);
    eInput.addEventListener("change", renderCharts);
    document.getElementById("scale").addEventListener("change", renderCharts);
    document.getElementById("agg").addEventListener("change", renderCharts);
    document.getElementById("reset").addEventListener("click", function() {
        sInput.value = minStr;
        eInput.value = maxStr;
        renderCharts();
    });
    document.getElementById("download").addEventListener("click", downloadCSV);

    renderCharts();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}
})();
</script>
</body>
</html>
"""


def generate_html(data: dict) -> str:
    """生成自包含 HTML 文件（内嵌 JSON 数据 + ECharts 图表）"""
    # 转义 < 防止 pod 名中的特殊字符破坏 <script> 标签
    json_str = json.dumps(data, separators=(",", ":")).replace("<", "\\u003c")
    return HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json_str)


# ── 主入口 ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="统计 KVCache 接口日志中按毫秒的读写请求并发数，输出 HTML 文件"
    )
    parser.add_argument("directory", help="日志文件夹目录")
    parser.add_argument(
        "-o", "--output",
        default="para_cnt_report.html",
        help="输出 HTML 文件路径（默认: para_cnt_report.html）",
    )
    args = parser.parse_args()

    # 查找日志文件
    files = find_log_files(args.directory)
    if not files:
        print(f"错误: 在 {args.directory} 中未找到 ds_client_access_*.log 文件", file=sys.stderr)
        sys.exit(1)

    print(f"找到 {len(files)} 个日志文件:")
    for f in files:
        print(f"  {f}")

    # 解析并聚合
    print("\n解析日志中...")
    agg_df = parse_and_aggregate(files)

    if agg_df.is_empty():
        print("警告: 未解析到有效的 GET/SET 操作记录", file=sys.stderr)

    total_lines = agg_df.select(
        (pl.col("read") + pl.col("write")).sum().alias("total")
    ).item()
    print(f"\n聚合完成: {agg_df.height} 个 (毫秒, pod) 组合, 共 {total_lines} 条请求")

    # 构建输出数据
    data = build_output_data(agg_df)

    # 生成 HTML
    html = generate_html(data)
    output_path = Path(args.output)
    output_path.write_text(html, encoding="utf-8")

    print(f"\nHTML 报告已生成: {output_path.resolve()}")


if __name__ == "__main__":
    main()
