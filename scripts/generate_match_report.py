#!/usr/bin/env python3
"""生成故障模式匹配验证的 HTML 报告"""

import json
import os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MATCH_RESULTS = os.path.join(SCRIPT_DIR, "match_results.json")
TRAIN_CASE_DIR = "/Users/zhaoyujin/Desktop/witty-ub/case_data/case"
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "match_report.html")


def load_train_cases():
    cases = {}
    for f in os.listdir(TRAIN_CASE_DIR):
        if not f.endswith(".json"):
            continue
        with open(os.path.join(TRAIN_CASE_DIR, f), "r", encoding="utf-8") as fh:
            d = json.load(fh)
        cases[d["root_cause_type"]] = d
    return cases


def fmt_val(v, max_len=60):
    if v is None:
        return "<span style='color:#999'>-</span>"
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, dict):
        items = sorted(v.items(), key=lambda x: -x[1] if isinstance(x[1], (int, float)) else 0)
        parts = []
        for k, val in items[:5]:
            if isinstance(val, float):
                parts.append(f"{k}:{val:.3f}")
            else:
                parts.append(f"{k}:{val}")
        s = ", ".join(parts)
        if len(items) > 5:
            s += f" +{len(items)-5}"
        if len(s) > max_len:
            s = s[:max_len] + "..."
        return s
    if isinstance(v, list):
        parts = [str(item) for item in v[:5]]
        s = ", ".join(parts)
        if len(v) > 5:
            s += f" +{len(v)-5}"
        return s
    return str(v)


def fmt_seg_ranking(segs):
    if not segs:
        return "<span style='color:#999'>-</span>"
    total = sum(s[1] for s in segs if s[1] > 0)
    if total <= 0:
        return "<span style='color:#999'>-</span>"
    parts = []
    for s in segs[:5]:
        pct = s[1] / total * 100
        parts.append(f"{s[0]}({pct:.0f}%)")
    return " &gt; ".join(parts)


def fmt_counter(counter, top_n=5):
    if not counter:
        return "<span style='color:#999'>-</span>"
    items = sorted(counter.items(), key=lambda x: -x[1])
    parts = [f"{k}:{v}" for k, v in items[:top_n]]
    s = ", ".join(parts)
    if len(items) > top_n:
        s += f" +{len(items)-top_n}"
    return s


def compare_vals(a, b):
    if a is None and b is None:
        return "match-empty"
    if a is None or b is None:
        return "mismatch"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return "match-exact"
        if min(abs(a), abs(b)) == 0:
            return "mismatch"
        ratio = max(abs(a), abs(b)) / min(abs(a), abs(b))
        if ratio < 1.5:
            return "match-close"
        return "mismatch"
    if isinstance(a, str) and isinstance(b, str):
        if a == b:
            return "match-exact"
        return "mismatch"
    if isinstance(a, dict) and isinstance(b, dict):
        if not a and not b:
            return "match-empty"
        if not a or not b:
            return "mismatch"
        overlap = len(set(a.keys()) & set(b.keys()))
        total = len(set(a.keys()) | set(b.keys()))
        if overlap / total > 0.5:
            return "match-close"
        return "mismatch"
    if isinstance(a, list) and isinstance(b, list):
        if not a and not b:
            return "match-empty"
        return "match-exact" if a == b else "mismatch"
    return "mismatch"


def build_feature_rows(test_f, gt_f, pred_f):
    rows = []

    def add_row(name, test_v, gt_v, pred_v, fmt_func=None):
        if fmt_func:
            test_s = fmt_func(test_v)
            gt_s = fmt_func(gt_v)
            pred_s = fmt_func(pred_v)
        else:
            test_s = fmt_val(test_v)
            gt_s = fmt_val(gt_v)
            pred_s = fmt_val(pred_v)
        gt_cls = compare_vals(test_v, gt_v)
        pred_cls = compare_vals(test_v, pred_v)
        rows.append((name, test_s, gt_s, gt_cls, pred_s, pred_cls))

    add_row("fault_category",
            test_f.get("fault_category"),
            gt_f.get("fault_category"),
            pred_f.get("fault_category"))

    test_lat = test_f.get("latency") or {}
    gt_lat = gt_f.get("latency") or {}
    pred_lat = pred_f.get("latency") or {}

    add_row("p99/p50 ratio", test_lat.get("p99_p50_ratio"),
            gt_lat.get("p99_p50_ratio"), pred_lat.get("p99_p50_ratio"))

    add_row("op_p99/p50", test_lat.get("op_p99_p50_ratio"),
            gt_lat.get("op_p99_p50_ratio"), pred_lat.get("op_p99_p50_ratio"))

    add_row("pod_concentration", test_lat.get("pod_concentration"),
            gt_lat.get("pod_concentration"), pred_lat.get("pod_concentration"))

    add_row("affected_pods", test_lat.get("affected_pods_count"),
            gt_lat.get("affected_pods_count"), pred_lat.get("affected_pods_count"))

    add_row("anomalous_ratio", test_lat.get("anomalous_ratio"),
            gt_lat.get("anomalous_ratio"), pred_lat.get("anomalous_ratio"))

    add_row("segment_ranking", test_lat.get("segment_ranking"),
            gt_lat.get("segment_ranking"), pred_lat.get("segment_ranking"),
            fmt_func=fmt_seg_ranking)

    add_row("affected_ops", test_lat.get("affected_operation_dist"),
            gt_lat.get("affected_operation_dist"), pred_lat.get("affected_operation_dist"),
            fmt_func=fmt_counter)

    add_row("trace_ctx_pods", test_lat.get("trace_context_pods_count"),
            gt_lat.get("trace_context_pods_count"), pred_lat.get("trace_context_pods_count"))

    add_row("trace_ctx_hosts", test_lat.get("trace_context_hosts_count"),
            gt_lat.get("trace_context_hosts_count"), pred_lat.get("trace_context_hosts_count"))

    test_conn = test_f.get("connectivity") or {}
    gt_conn = gt_f.get("connectivity") or {}
    pred_conn = pred_f.get("connectivity") or {}

    add_row("failure_mode", test_conn.get("failure_mode_dist"),
            gt_conn.get("failure_mode_dist"), pred_conn.get("failure_mode_dist"),
            fmt_func=fmt_counter)

    add_row("status_code", test_conn.get("status_code_dist"),
            gt_conn.get("status_code_dist"), pred_conn.get("status_code_dist"),
            fmt_func=fmt_counter)

    add_row("spatial_pod", (test_conn.get("spatial_pod") or {}).get("scope"),
            (gt_conn.get("spatial_pod") or {}).get("scope"),
            (pred_conn.get("spatial_pod") or {}).get("scope"))

    add_row("spatial_host", (test_conn.get("spatial_host") or {}).get("scope"),
            (gt_conn.get("spatial_host") or {}).get("scope"),
            (pred_conn.get("spatial_host") or {}).get("scope"))

    add_row("conn_ops", test_conn.get("affected_operation_dist"),
            gt_conn.get("affected_operation_dist"), pred_conn.get("affected_operation_dist"),
            fmt_func=fmt_counter)

    return rows


def generate_html(results_data, train_cases):
    results = results_data["results"]
    correct = [r for r in results if r["correct"]]
    incorrect = [r for r in results if not r["correct"]]

    by_cat = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        cat = r.get("test_fault_category", "unknown")
        by_cat[cat]["total"] += 1
        if r["correct"]:
            by_cat[cat]["correct"] += 1

    total = results_data["total_valid"]
    top1 = results_data["top1_accuracy"]
    top3 = results_data["top3_accuracy"]
    top5 = results_data["top5_accuracy"]

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>故障模式匹配验证报告</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:20px;background:#f5f5f5;color:#333}
h1{color:#1a1a2e;border-bottom:2px solid #16213e;padding-bottom:10px}
h2{color:#16213e;margin-top:30px}
.summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin:20px 0}
.summary-card{background:#fff;border-radius:8px;padding:15px;box-shadow:0 2px 4px rgba(0,0,0,.1);text-align:center}
.summary-card .value{font-size:28px;font-weight:bold}
.summary-card .label{font-size:13px;color:#666;margin-top:5px}
.good{color:#27ae60}.bad{color:#e74c3c}.medium{color:#f39c12}
.case-card{background:#fff;border-radius:8px;margin:15px 0;box-shadow:0 2px 4px rgba(0,0,0,.1);overflow:hidden}
.case-header{padding:12px 20px;display:flex;justify-content:space-between;align-items:center}
.case-header.correct{background:#e8f5e9;border-left:4px solid #27ae60}
.case-header.incorrect{background:#ffebee;border-left:4px solid #e74c3c}
.case-body{padding:15px 20px}
.case-name{font-weight:bold;font-size:14px}
.confidence{font-size:12px;color:#888}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}
th{background:#16213e;color:#fff;padding:8px 12px;text-align:left}
td{padding:6px 12px;border-bottom:1px solid #eee}
tr:hover td{background:#f0f4f8}
.match-exact{background:#e8f5e9}.match-close{background:#fff8e1}.match-empty{background:#f5f5f5;color:#999}.mismatch{background:#ffebee}
.top5-list{font-size:12px;color:#555;margin-top:8px}
.top5-item{display:inline-block;margin:2px 8px 2px 0;padding:2px 8px;border-radius:3px;background:#e8eaf6}
.top5-item.gt{background:#c8e6c9;font-weight:bold}.top5-item.pred{background:#ffcdd2}
.tag{display:inline-block;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:bold;margin-left:8px}
.tag-latency{background:#e3f2fd;color:#1565c0}.tag-mixed{background:#fff3e0;color:#e65100}.tag-connectivity{background:#fce4ec;color:#c62828}.tag-unknown{background:#f5f5f5;color:#666}
.filter-bar{margin:15px 0}
.filter-bar button{padding:6px 15px;margin-right:8px;border:1px solid #ccc;border-radius:4px;background:#fff;cursor:pointer}
.filter-bar button.active{background:#16213e;color:#fff;border-color:#16213e}
</style>
</head>
<body>
<h1>故障模式匹配验证报告</h1>
"""

    def cls_for_rate(rate, thresholds=(0.5, 0.3)):
        return "good" if rate > thresholds[0] else ("medium" if rate > thresholds[1] else "bad")

    html += f"""
<div class="summary-grid">
  <div class="summary-card"><div class="value">{total}</div><div class="label">有效测试案例</div></div>
  <div class="summary-card"><div class="value {cls_for_rate(top1)}">{top1*100:.1f}%</div><div class="label">Top-1 准确率 ({len(correct)}/{total})</div></div>
  <div class="summary-card"><div class="value {cls_for_rate(top3,(0.6,0.4))}">{top3*100:.1f}%</div><div class="label">Top-3 准确率</div></div>
  <div class="summary-card"><div class="value {cls_for_rate(top5,(0.7,0.5))}">{top5*100:.1f}%</div><div class="label">Top-5 准确率</div></div>
</div>

<h2>按故障类别统计</h2>
<table>
<tr><th>故障类别</th><th>正确</th><th>总数</th><th>Top-1 准确率</th></tr>
"""
    for cat in sorted(by_cat.keys()):
        info = by_cat[cat]
        rate = info["correct"] / info["total"] if info["total"] > 0 else 0
        html += f'<tr><td><span class="tag tag-{cat}">{cat}</span></td><td>{info["correct"]}</td><td>{info["total"]}</td><td class="{cls_for_rate(rate)}">{rate*100:.1f}%</td></tr>\n'

    html += """</table>

<h2>案例详情</h2>
<div class="filter-bar">
  <button class="active" onclick="filter('all')">全部</button>
  <button onclick="filter('correct')">正确</button>
  <button onclick="filter('incorrect')">错误</button>
  <button onclick="filter('latency')">latency</button>
  <button onclick="filter('mixed')">mixed</button>
  <button onclick="filter('connectivity')">connectivity</button>
</div>
"""

    all_cases = incorrect + correct

    for r in all_cases:
        gt = r["ground_truth"]
        pred = r["predicted"]
        conf = r["confidence"]
        correct_flag = r["correct"]
        test_f = r.get("test_features", {})
        cat = r.get("test_fault_category", "unknown")
        top5 = r.get("top5_candidates", [])

        gt_train = train_cases.get(gt, {})
        pred_train = train_cases.get(pred, {})
        gt_f = gt_train.get("features", {})
        pred_f = pred_train.get("features", {})

        header_cls = "correct" if correct_flag else "incorrect"
        status_text = "&#10003; 正确" if correct_flag else "&#10007; 错误"
        status_cls = "good" if correct_flag else "bad"

        html += f"""
<div class="case-card" data-status="{'correct' if correct_flag else 'incorrect'}" data-cat="{cat}">
  <div class="case-header {header_cls}">
    <div><span class="case-name">{gt}</span><span class="tag tag-{cat}">{cat}</span><span class="{status_cls}" style="margin-left:10px">{status_text}</span></div>
    <div><span class="confidence">置信度: {conf}</span></div>
  </div>
  <div class="case-body">
"""
        if not correct_flag:
            html += f'    <div style="margin-bottom:10px;color:#c62828"><b>误判为:</b> {pred} (置信度 {conf})</div>\n'

        if top5:
            html += '    <div class="top5-list"><b>Top-5:</b> '
            for cand_type, cand_sim in top5:
                cand_cls = "gt" if cand_type == gt else ("pred" if cand_type == pred and not correct_flag else "")
                html += f'<span class="top5-item {cand_cls}">{cand_type} ({cand_sim})</span>'
            html += '</div>\n'

        feature_rows = build_feature_rows(test_f, gt_f, pred_f)
        html += '    <table>\n      <tr><th>特征</th><th>测试案例</th><th>正确训练案例</th><th>匹配</th>'
        if not correct_flag:
            html += '<th>误判训练案例</th><th>匹配</th>'
        html += '</tr>\n'

        for row in feature_rows:
            name, test_s, gt_s, gt_cls, pred_s, pred_cls = row
            gt_mark = "&#10003;" if "exact" in gt_cls else ("~" if "close" in gt_cls else "&#10007;")
            pred_mark = "&#10003;" if "exact" in pred_cls else ("~" if "close" in pred_cls else "&#10007;")
            if correct_flag:
                html += f'      <tr><td>{name}</td><td>{test_s}</td><td>{gt_s}</td><td class="{gt_cls}">{gt_mark}</td></tr>\n'
            else:
                html += f'      <tr><td>{name}</td><td>{test_s}</td><td>{gt_s}</td><td class="{gt_cls}">{gt_mark}</td><td>{pred_s}</td><td class="{pred_cls}">{pred_mark}</td></tr>\n'

        html += '    </table>\n  </div>\n</div>\n'

    html += """
<script>
function filter(type){
  document.querySelectorAll('.filter-bar button').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.case-card').forEach(card=>{
    if(type==='all'){card.style.display='';return}
    if(type==='correct'||type==='incorrect'){card.style.display=card.dataset.status===type?'':'none'}
    else{card.style.display=card.dataset.cat===type?'':'none'}
  })
}
</script>
</body>
</html>
"""
    return html


def main():
    train_cases = load_train_cases()
    with open(MATCH_RESULTS, "r", encoding="utf-8") as f:
        results_data = json.load(f)

    html = generate_html(results_data, train_cases)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"报告已生成: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
