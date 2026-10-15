#!/usr/bin/env python3
"""基于 match_results_v2.json 生成增强版故障匹配验证报告 V2

功能：
1. 总体统计（Top-1/3/5 准确率）
2. 按故障类别分类统计
3. 系统化未命中归类分析
4. 高置信度误分析
5. 错误热点类型
6. 案例详情
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MATCH_RESULTS = os.path.join(SCRIPT_DIR, "match_results_v2.json")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "match_report_v2.html")

# ===== 样式模板 =====
STYLE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; padding: 20px; }
.container { max-width: 1400px; margin: 0 auto; background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); overflow: hidden; }
.header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px 40px; }
.header h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
.header .subtitle { font-size: 14px; opacity: 0.9; }
.content { padding: 32px 40px; }
.section { margin-bottom: 40px; }
.section h2 { font-size: 20px; font-weight: 700; color: #2c3e50; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 3px solid #667eea; display: inline-block; }
.section h3 { font-size: 16px; font-weight: 600; color: #34495e; margin: 20px 0 12px 0; }
.metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.metric-card { background: linear-gradient(135deg, #f8f9ff 0%, #eef1ff 100%); border-radius: 12px; padding: 20px; text-align: center; border: 1px solid #e4e8f0; }
.metric-card .value { font-size: 36px; font-weight: 800; margin-bottom: 4px; }
.metric-card .label { font-size: 13px; color: #7f8c8d; font-weight: 500; }
.metric-card.highlight { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; }
.metric-card.highlight .label { color: rgba(255,255,255,0.9); }
table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 16px; }
th { background: #f8f9fa; padding: 10px 12px; text-align: left; font-weight: 600; color: #2c3e50; border-bottom: 2px solid #dee2e6; white-space: nowrap; }
td { padding: 8px 12px; border-bottom: 1px solid #eee; white-space: nowrap; }
tr:hover td { background: #f8f9ff; }
.tag { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; }
.tag-latency { background: #e3f2fd; color: #1565c0; }
.tag-mixed { background: #fff3e0; color: #e65100; }
.tag-connectivity { background: #fce4ec; color: #c62828; }
.tag-c0 { background: #ffcdd2; color: #c62828; }
.tag-c1 { background: #ffe0b2; color: #e65100; }
.tag-c2 { background: #fff9c4; color: #f57f17; }
.tag-conf-high { background: #ef5350; color: white; }
.tag-conf-mid { background: #ffb300; color: white; }
.tag-conf-low { background: #66bb6a; color: white; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.three-col { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
@media (max-width: 900px) { .two-col, .three-col { grid-template-columns: 1fr; } .metrics-grid { grid-template-columns: repeat(2, 1fr); } }
.stat-bar { height: 24px; border-radius: 12px; background: #ecf0f1; overflow: hidden; position: relative; }
.stat-bar-fill { height: 100%; border-radius: 12px; }
.stat-bar-text { position: absolute; top: 50%; left: 8px; transform: translateY(-50%); font-size: 11px; font-weight: bold; color: #2c3e50; white-space: nowrap; }
.insight { background: #e8f5e9; border-left: 4px solid #27ae60; padding: 12px 16px; border-radius: 8px; font-size: 13px; color: #2e7d32; margin: 16px 0; }
.case-card { background: #fff; border-radius: 8px; margin: 15px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden; border: 1px solid #e4e8f0; }
.case-header { padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.case-header.incorrect { background: linear-gradient(90deg, #ffebee 0%, #fff 100%); border-left: 4px solid #e74c3c; }
.case-body { padding: 15px 20px; }
.case-name { font-weight: bold; font-size: 14px; color: #2c3e50; }
.confidence { font-size: 12px; color: #888; }
.top5-list { font-size: 12px; color: #555; margin-top: 8px; }
.top5-item { display: inline-block; margin: 2px 8px 2px 0; padding: 2px 8px; border-radius: 3px; background: #e8eaf6; }
.top5-item.gt { background: #c8e6c9; font-weight: bold; }
.top5-item.pred { background: #ffcdd2; }
.filter-bar { margin: 15px 0; display: flex; flex-wrap: wrap; gap: 6px; }
.filter-bar button { padding: 6px 15px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; font-size: 12px; }
.filter-bar button.active { background: #667eea; color: #fff; border-color: #667eea; }
.filter-bar button:hover { background: #f0f4f8; }
.filter-bar button.active:hover { background: #5a6fd6; }
.footer { text-align: center; padding: 20px; color: #95a5a6; font-size: 12px; border-top: 1px solid #ecf0f1; }
"""


def classify_miss_type(result):
    gt = result["ground_truth"]
    pred = result["predicted"]
    top5 = [c[0] for c in result.get("top5_candidates", [])]
    conf = result["confidence"]

    gt_in_top5 = gt in top5
    gt_top3 = gt in [c[0] for c in result.get("top5_candidates", [])[:3]]

    if not gt_in_top5:
        main_cat = "C0"
        main_label = "GT完全不在Top5候选集中"
    elif not gt_top3:
        main_cat = "C1"
        main_label = "GT在Top5但不在Top3"
    else:
        main_cat = "C2"
        main_label = "GT在Top3但不是Top1"

    # 子分类
    if ("client" in gt and "worker" in pred) or ("worker" in gt and "client" in pred):
        sub_cat = "Client/Worker角色混淆"
    elif ("local" in gt and "remote" in pred) or ("remote" in gt and "local" in pred):
        sub_cat = "Local/Remote位置混淆"
    elif "etcd" in gt and "etcd" in pred and gt != pred:
        sub_cat = "etcd相关子类型混淆"
    elif "ub" in gt.lower() and "ub" in pred.lower() and gt != pred:
        sub_cat = "UB类型内部混淆"
    elif gt.split("_")[0] == pred.split("_")[0]:
        sub_cat = "同家族内部混淆"
    else:
        sub_cat = "跨家族混淆"

    if conf >= 0.9:
        conf_level = "高置信度(>0.9)"
    elif conf >= 0.7:
        conf_level = "中置信度(0.7-0.9)"
    else:
        conf_level = "低置信度(<0.7)"

    second_is_gt = result.get("second_type") == gt

    return {
        "main_cat": main_cat, "main_label": main_label,
        "sub_cat": sub_cat, "conf_level": conf_level,
        "second_is_gt": second_is_gt,
    }


def fmt_val(v, max_len=80):
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


def esc(s):
    """Escape curly braces for CSS"""
    return s.replace("{", "{{").replace("}", "}}")


def generate_html(results_data):
    results = results_data["results"]
    correct = [r for r in results if r["correct"]]
    incorrect = [r for r in results if not r["correct"]]

    for r in incorrect:
        r["_classification"] = classify_miss_type(r)

    total = results_data["total_valid"]
    top1 = results_data["top1_accuracy"]
    top3 = results_data["top3_accuracy"]
    top5 = results_data["top5_accuracy"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ===== 统计 =====
    by_cat = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        cat = r.get("test_fault_category", "unknown")
        by_cat[cat]["total"] += 1
        if r["correct"]:
            by_cat[cat]["correct"] += 1

    by_main_cat = defaultdict(list)
    by_sub_cat = defaultdict(list)
    for r in incorrect:
        mc = r["_classification"]["main_cat"]
        sc = r["_classification"]["sub_cat"]
        by_main_cat[mc].append(r)
        by_sub_cat[sc].append(r)

    error_pairs = Counter()
    for r in incorrect:
        error_pairs[(r["ground_truth"], r["predicted"])] += 1

    gt_error_freq = Counter(r["ground_truth"] for r in incorrect)
    pred_error_freq = Counter(r["predicted"] for r in incorrect)
    conf_dist = Counter(r["_classification"]["conf_level"] for r in incorrect)

    top3_recall = sum(1 for r in incorrect if r.get("top3_correct"))
    top5_recall = sum(1 for r in incorrect if r.get("top5_correct"))
    second_is_gt = sum(1 for r in incorrect if r["_classification"]["second_is_gt"])

    latency_incorrect = [r for r in incorrect if r.get("test_fault_category") == "latency"]
    mixed_incorrect = [r for r in incorrect if r.get("test_fault_category") == "mixed"]
    conn_incorrect = [r for r in incorrect if r.get("test_fault_category") == "connectivity"]

    # ===== 开始构建 HTML =====
    h = []
    a = h.append  # shortcut

    a('<!DOCTYPE html>')
    a('<html lang="zh-CN">')
    a('<head>')
    a('<meta charset="UTF-8">')
    a('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    a('<title>故障模式匹配验证报告 V2</title>')
    a(f'<style>{STYLE_CSS}</style>')
    a('</head>')
    a('<body>')
    a('<div class="container">')

    # Header
    a(f'<div class="header">')
    a(f'<h1>🔍 灵衢 KVCache 故障诊断评估报告 V2</h1>')
    a(f'<div class="subtitle">生成时间：{now} · 案例总数：{total} · 正确：{len(correct)} · 未命中：{len(incorrect)}</div>')
    a('</div>')
    a('<div class="content">')

    # ===== Section 1: 总体指标 =====
    a('<div class="section">')
    a('<h2>📊 评估结果总览</h2>')
    a('<div class="metrics-grid">')
    a(f'<div class="metric-card"><div class="value" style="color:#667eea">{total}</div><div class="label">有效测试案例</div></div>')
    a(f'<div class="metric-card highlight"><div class="value">{top1*100:.1f}%</div><div class="label">Top-1 准确率</div></div>')
    a(f'<div class="metric-card"><div class="value" style="color:#27ae60">{top3*100:.1f}%</div><div class="label">Top-3 召回率</div></div>')
    a(f'<div class="metric-card"><div class="value" style="color:#f39c12">{top5*100:.1f}%</div><div class="label">Top-5 召回率</div></div>')
    a('</div>')

    # 按类别统计
    for cat in sorted(by_cat.keys()):
        info = by_cat[cat]
        rate = info["correct"] / info["total"] * 100 if info["total"] > 0 else 0
        cat_label = {"latency": "时延故障", "mixed": "混合故障", "connectivity": "通断故障"}.get(cat, cat)
        color = "#27ae60" if rate >= 70 else ("#f39c12" if rate >= 40 else "#e74c3c")
        a(f'''
        <div style="margin-bottom: 16px">
            <div style="display: flex; align-items: center; margin-bottom: 6px">
                <span class="tag tag-{cat}">{cat_label}</span>
                <span style="margin-left: 10px; font-size: 13px; color: #7f8c8d">{info["correct"]}/{info["total"]} 正确 ({rate:.1f}%)</span>
            </div>
            <div class="stat-bar"><div class="stat-bar-fill" style="width: {rate:.1f}%; background: {color}"></div></div>
        </div>''')
    a('</div>')

    # ===== Section 2: 系统化未命中归类 =====
    a(f'<div class="section">')
    a(f'<h2>🔍 系统化未命中归类分析（共 {len(incorrect)} 个未命中案例）</h2>')

    # 2.1 主分类
    a('<h3>📌 主分类：错误发生层级</h3>')
    a('<div class="three-col">')

    main_cat_info = [
        ("C0", "GT完全不在Top5候选集中", "候选集缺失/召回率不足", "#ef5350"),
        ("C1", "GT在Top5但不在Top3", "排序靠后", "#ffa726"),
        ("C2", "GT在Top3但不是Top1", "最终排序问题", "#ffee58"),
    ]
    for cat_code, label, desc, color in main_cat_info:
        cases = by_main_cat.get(cat_code, [])
        count = len(cases)
        pct = count / len(incorrect) * 100 if len(incorrect) > 0 else 0
        a(f'''
        <div class="metric-card" style="border-color: {color}">
            <div class="value" style="color: {color}">{count}</div>
            <div class="label" style="font-weight: 600; color: {color}">{cat_code}: {label}</div>
            <div style="font-size: 11px; color: #999; margin-top: 4px">{desc}</div>
            <div style="font-size: 11px; color: #666; margin-top: 4px">占比 {pct:.0f}%</div>
        </div>''')
    a('</div>')

    # 2.2 子分类
    a('<h3>🔀 子分类：混淆模式分析</h3>')
    a('<table><thead><tr><th>混淆模式</th><th>数量</th><th>占比</th><th>典型案例</th></tr></thead><tbody>')

    sub_cat_desc = {
        "Client/Worker角色混淆": "client端故障被误判为worker端，或反之",
        "Local/Remote位置混淆": "本地(local)故障被误判为远端(remote)，或反之",
        "etcd相关子类型混淆": "不同etcd相关故障子类型之间的混淆",
        "UB类型内部混淆": "UBM/UBSE等不同UB子类型之间的混淆",
        "同家族内部混淆": "前缀相同但故障子类型不同",
        "跨家族混淆": "完全不同故障家族之间的误判",
        "其他": "未能归类的其他混淆模式",
    }

    for sub_cat, cases in sorted(by_sub_cat.items(), key=lambda x: -len(x[1])):
        count = len(cases)
        pct = count / len(incorrect) * 100 if len(incorrect) > 0 else 0
        examples = list(set(f"{c['ground_truth']}→{c['predicted']}" for c in cases[:3]))
        examples_str = "; ".join(examples)
        if len(examples_str) > 80:
            examples_str = examples_str[:77] + "..."
        desc = sub_cat_desc.get(sub_cat, "")
        a(f'''
        <tr>
            <td><b>{sub_cat}</b><br><span style="color:#999; font-size:11px">{desc}</span></td>
            <td>{count}</td>
            <td><div class="stat-bar" style="min-width: 80px"><div class="stat-bar-fill" style="width: {pct:.0f}%; background: #667eea"></div><span class="stat-bar-text">{pct:.0f}%</span></div></td>
            <td style="font-family: monospace; font-size: 11px">{examples_str}</td>
        </tr>''')
    a('</tbody></table>')

    # 2.3 置信度
    a('<h3>⚠️ 置信度分布</h3>')
    a('<div class="three-col">')
    for label, key, color in [
        ("高置信度(>0.9)", "高置信度(>0.9)", "#ef5350"),
        ("中置信度(0.7-0.9)", "中置信度(0.7-0.9)", "#ffb300"),
        ("低置信度(<0.7)", "低置信度(<0.7)", "#66bb6a"),
    ]:
        count = conf_dist.get(key, 0)
        pct = count / len(incorrect) * 100 if len(incorrect) > 0 else 0
        a(f'''
        <div class="metric-card" style="border-color: {color}">
            <div class="value" style="color: {color}">{count}</div>
            <div class="label">{label}</div>
            <div style="font-size: 11px; color: #666; margin-top: 4px">占比 {pct:.0f}%</div>
        </div>''')
    a('</div>')

    # 2.4 Top-K 召回
    a(f'''
    <h3>🎯 Top-K 召回分析</h3>
    <div class="two-col">
        <div>
            <p style="font-size: 13px; margin-bottom: 8px"><b>未命中案例中，GT在候选集中的位置：</b></p>
            <table>
                <tr><th>位置</th><th>数量</th><th>占未命中比例</th></tr>
                <tr><td>Top-2 候选（第2名）</td><td>{second_is_gt}</td><td>{second_is_gt/max(len(incorrect),1)*100:.0f}%</td></tr>
                <tr><td>Top-3 候选内</td><td>{top3_recall}</td><td>{top3_recall/max(len(incorrect),1)*100:.0f}%</td></tr>
                <tr><td>Top-5 候选内</td><td>{top5_recall}</td><td>{top5_recall/max(len(incorrect),1)*100:.0f}%</td></tr>
                <tr><td>不在Top-5</td><td>{len(incorrect)-top5_recall}</td><td>{(len(incorrect)-top5_recall)/max(len(incorrect),1)*100:.0f}%</td></tr>
            </table>
        </div>
        <div>
            <div class="insight">
                <b>💡 改进建议</b><br>
                {second_is_gt}个案例的GT是第二候选，仅需微调排序逻辑即可修正。<br>
                {top5_recall}个案例的GT出现在Top5中，存在被召回的可能。<br>
                {len(incorrect)-top5_recall}个案例的GT完全不在候选集中，需要改进候选生成逻辑。
            </div>
        </div>
    </div>''')
    a('</div>')

    # ===== Section 3: 错误热点 =====
    a('<div class="section">')
    a('<h2>🔥 错误热点分析</h2>')

    a('<h3>最常见的错误模式（GT → 预测）</h3>')
    a('<table><thead><tr><th>真实类型 (GT)</th><th>被误判为</th><th>次数</th><th>占比</th></tr></thead><tbody>')
    for (gt, pred), count in error_pairs.most_common(15):
        pct = count / len(incorrect) * 100
        a(f'<tr><td><code>{gt}</code></td><td style="color:#e74c3c"><code>{pred}</code></td><td>{count}</td><td>{pct:.0f}%</td></tr>')
    a('</tbody></table>')

    a('<h3>最容易被误判的GT类型</h3>')
    a('<table><thead><tr><th>GT类型</th><th>误判次数</th><th>可能被误判为</th></tr></thead><tbody>')
    for gt, count in gt_error_freq.most_common(10):
        possible_preds = set()
        for r in incorrect:
            if r["ground_truth"] == gt:
                possible_preds.add(r["predicted"])
        preds_str = ", ".join(list(possible_preds)[:3])
        a(f'<tr><td><code>{gt}</code></td><td>{count}</td><td style="font-family: monospace; font-size: 11px; color: #e74c3c">{preds_str}</td></tr>')
    a('</tbody></table>')

    a('<h3>最常被错误预测的目标类型</h3>')
    a('<table><thead><tr><th>预测类型</th><th>被错误预测次数</th><th>预测置信度均值</th></tr></thead><tbody>')
    for pred, count in pred_error_freq.most_common(10):
        confs = [r["confidence"] for r in incorrect if r["predicted"] == pred]
        avg_conf = sum(confs) / len(confs) if confs else 0
        a(f'<tr><td><code>{pred}</code></td><td>{count}</td><td>{avg_conf:.3f}</td></tr>')
    a('</tbody></table>')
    a('</div>')

    # ===== Section 4: 分故障类型分析 =====
    a('<div class="section">')
    a('<h2>📈 分故障类型详细分析</h2>')
    for cat in sorted(by_cat.keys()):
        info = by_cat[cat]
        rate = info["correct"] / info["total"] * 100
        cat_label = {"latency": "时延故障", "mixed": "混合故障", "connectivity": "通断故障"}.get(cat, cat)
        incorrect_in_cat = [r for r in incorrect if r.get("test_fault_category") == cat]
        sub_dist = Counter(r["_classification"]["sub_cat"] for r in incorrect_in_cat)

        a(f'''
        <div style="margin-bottom: 30px; padding: 20px; background: #fafbfc; border-radius: 8px; border: 1px solid #e4e8f0">
            <h3><span class="tag tag-{cat}">{cat_label}</span> 准确率: {rate:.1f}% ({info["correct"]}/{info["total"]})</h3>''')

        if incorrect_in_cat:
            a('<p style="font-size: 13px; color: #7f8c8d; margin: 8px 0 12px"><b>未命中子分类分布：</b>')
            for sub_cat, sub_count in sub_dist.most_common():
                sub_pct = sub_count / len(incorrect_in_cat) * 100
                a(f'<span style="margin-right: 16px; font-size: 12px">{sub_cat}: <b>{sub_count}</b> ({sub_pct:.0f}%)</span>')
            a('</p>')

        a('</div>')
    a('</div>')

    # ===== Section 5: 案例详情 =====
    a('<div class="section">')
    a('<h2>📋 未命中案例详情</h2>')
    a(f'''
    <div class="filter-bar">
        <button class="active" onclick="filterCases('all')">全部 ({len(incorrect)})</button>
        <button onclick="filterCases('C0')">C0: GT不在Top5 ({len(by_main_cat.get("C0", []))})</button>
        <button onclick="filterCases('C1')">C1: GT在Top5非Top3 ({len(by_main_cat.get("C1", []))})</button>
        <button onclick="filterCases('C2')">C2: GT在Top3非Top1 ({len(by_main_cat.get("C2", []))})</button>
        <button onclick="filterCases('latency')">时延类 ({len(latency_incorrect)})</button>
        <button onclick="filterCases('mixed')">混合类 ({len(mixed_incorrect)})</button>
        <button onclick="filterCases('connectivity')">通断类 ({len(conn_incorrect)})</button>
    </div>''')

    for r in incorrect:
        gt = r["ground_truth"]
        pred = r["predicted"]
        conf = r["confidence"]
        cat = r.get("test_fault_category", "unknown")
        cls = r["_classification"]
        top5 = r.get("top5_candidates", [])
        test_f = r.get("test_features", {})
        test_lat = test_f.get("latency") or {}
        test_conn = test_f.get("connectivity") or {}

        conf_class = "tag-conf-high" if "高" in cls["conf_level"] else ("tag-conf-mid" if "中" in cls["conf_level"] else "tag-conf-low")
        data_attrs = f'data-main-cat="{cls["main_cat"]}" data-cat="{cat}"'

        a(f'''
        <div class="case-card" {data_attrs}>
            <div class="case-header incorrect">
                <div>
                    <span class="case-name">{gt}</span>
                    <span class="tag tag-{cat}">{cat}</span>
                    <span class="tag tag-{cls['main_cat'].lower()[:2]}">{cls['main_cat']}</span>
                    <span class="tag" style="background:#e8eaf6;color:#3949ab">{cls['sub_cat']}</span>
                    <span class="tag {conf_class}">{cls['conf_level']}</span>
                </div>
                <div><span class="confidence">置信度: {conf:.4f}</span></div>
            </div>
            <div class="case-body">
                <div style="margin-bottom: 10px; color: #c62828"><b>❌ 误判为:</b> {pred} (置信度 {conf:.4f})</div>''')

        if top5:
            a('    <div class="top5-list"><b>Top-5 候选:</b> ')
            for cand_type, cand_sim in top5:
                cand_cls = "gt" if cand_type == gt else ("pred" if cand_type == pred else "")
                a(f'<span class="top5-item {cand_cls}">{cand_type} ({cand_sim:.4f})</span>')
            a('</div>')

        a('    <table>')
        a('        <tr><th>特征</th><th>测试值</th><th>分析</th></tr>')

        a(f'        <tr><td>fault_category</td><td>{test_f.get("fault_category", "-")}</td><td>-</td></tr>')

        if test_lat:
            p99_p50 = test_lat.get("p99_p50_ratio", "-")
            p99_str = f"{p99_p50:.3f}" if isinstance(p99_p50, (int, float)) else str(p99_p50)
            a(f'        <tr><td>p99/p50 ratio</td><td>{p99_str}</td><td>{"异常" if isinstance(p99_p50, (int, float)) and p99_p50 > 10 else "正常"}</td></tr>')
            a(f'        <tr><td>pod_concentration</td><td>{fmt_val(test_lat.get("pod_concentration"))}</td><td>-</td></tr>')
            a(f'        <tr><td>segment_ranking</td><td>{fmt_seg_ranking(test_lat.get("segment_ranking", []))}</td><td>-</td></tr>')
            a(f'        <tr><td>anomalous_ratio</td><td>{fmt_val(test_lat.get("anomalous_ratio"))}</td><td>-</td></tr>')
            a(f'        <tr><td>trace_ctx_pods</td><td>{fmt_val(test_lat.get("trace_context_pods_count"))}</td><td>-</td></tr>')
            a(f'        <tr><td>trace_ctx_hosts</td><td>{fmt_val(test_lat.get("trace_context_hosts_count"))}</td><td>-</td></tr>')

        if test_conn:
            a(f'        <tr><td>failure_mode</td><td>{fmt_counter(test_conn.get("failure_mode_dist"))}</td><td>-</td></tr>')
            a(f'        <tr><td>status_code</td><td>{fmt_counter(test_conn.get("status_code_dist"))}</td><td>-</td></tr>')

        a('    </table>')
        a('</div>')
        a('</div>')

    # ===== Footer =====
    a('</div>')
    a('<div class="footer">灵衢 UB 超节点故障智能诊断平台 · 评估报告自动生成 V2 · 系统化未命中归类</div>')
    a('</div>')
    a('''
<script>
function filterCases(type) {
    document.querySelectorAll('.filter-bar button').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('.case-card').forEach(card => {
        if (type === 'all') { card.style.display = ''; return; }
        if (type === 'C0' || type === 'C1' || type === 'C2') {
            card.style.display = card.dataset.mainCat === type ? '' : 'none';
        } else {
            card.style.display = card.dataset.cat === type ? '' : 'none';
        }
    });
}
</script>''')
    a('</body>')
    a('</html>')

    return "\n".join(h)


def main():
    with open(MATCH_RESULTS, "r", encoding="utf-8") as f:
        data = json.load(f)

    html = generate_html(data)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    total = data["total_valid"]
    correct_count = sum(1 for r in data["results"] if r["correct"])
    print(f"✅ 报告已生成: {OUTPUT_HTML}")
    print(f"   总案例: {total}")
    print(f"   Top-1: {data['top1_accuracy']*100:.1f}%")
    print(f"   Top-3: {data['top3_accuracy']*100:.1f}%")
    print(f"   Top-5: {data['top5_accuracy']*100:.1f}%")
    print(f"   未命中: {total - correct_count}")


if __name__ == "__main__":
    main()
