#!/usr/bin/env python3
"""
测试集评估报告生成器

功能：
1. 读取 dataset_summary.json 获取训练集/测试集概况
2. 从后端 API 获取 test_set 知识库的所有日志文件
3. 对每个 test_set 日志调用 /similarity_analysis 获取 Top-3 相似故障类型
4. 将预测结果与真实标签对比，计算准确率
5. 生成包含未命中案例分析的 HTML 报告
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# ─── 配置 ───
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:9772")
DATASET_SUMMARY = os.environ.get(
    "DATASET_SUMMARY",
    "/Users/zhaoyujin/Desktop/yxh_new_data_complete/dataset_summary.json",
)
OUTPUT_HTML = os.environ.get(
    "OUTPUT_HTML",
    "/Users/zhaoyujin/Desktop/witty-ub/evaluation_report.html",
)
TEST_SET_KB_NAME = os.environ.get("TEST_SET_KB_NAME", "test_set")

# ─── HTTP 工具 ───

def api_get(path: str) -> dict:
    url = f"{BACKEND_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def api_post(path: str, data: dict) -> dict:
    url = f"{BACKEND_URL}{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def api_list_kb(name_filter: str) -> list:
    """List knowledge bases by name filter."""
    resp = api_post("/log_kb/list", {
        "name": name_filter,
        "page_cnt": 200,
        "page_num": 1,
    })
    return resp.get("result", {}).get("kbs", [])


def api_list_log_files(kb_id: str) -> list:
    """List log files for a knowledge base."""
    resp = api_post(f"/log_file/list/{kb_id}", {
        "page_cnt": 500,
        "page_num": 1,
    })
    items = resp.get("result", {}).get("log_files", [])
    return items


def api_similarity_analysis(log_file_id: str, top_k: int = 3) -> dict:
    """Get similarity analysis for a log file."""
    return api_post("/similarity_analysis", {
        "log_file_id": log_file_id,
        "top_k": top_k,
    })


# ─── 数据加载 ───

def load_dataset_summary() -> dict:
    with open(DATASET_SUMMARY, "r") as f:
        return json.load(f)


def build_truth_map(summary: dict) -> dict:
    """构建 case_name -> fault_type 的映射"""
    truth = {}
    for ft in summary["fault_types"]:
        ft_name = ft["fault_type"]
        # 映射到合并后的类型
        merged = summary.get("merge_map", {}).get(ft_name, ft_name)
        for case in ft.get("test_set_cases", []):
            case_name = case["name"]
            truth[case_name] = {
                "true_type": ft_name,
                "merged_type": merged,
                "source": case.get("source", ""),
            }
    return truth


def build_dataset_overview(summary: dict) -> dict:
    """构建数据集概况统计"""
    ds_total = summary["total_data_set"]
    ts_total = summary["total_test_set"]
    merge_map = summary.get("merge_map", {})

    # 训练集故障类型分布
    train_counter = Counter()
    test_counter = Counter()
    train_type_details = defaultdict(list)
    test_type_details = defaultdict(list)

    for ft in summary["fault_types"]:
        ft_name = ft["fault_type"]
        for case in ft.get("data_set_cases", []):
            train_counter[ft_name] += 1
            train_type_details[ft_name].append(case["name"])
        for case in ft.get("test_set_cases", []):
            test_counter[ft_name] += 1
            test_type_details[ft_name].append(case["name"])

    # 统计：有训练样本的故障类型数
    train_types_with_samples = sum(1 for c in train_counter.values() if c > 0)
    test_types_with_samples = sum(1 for c in test_counter.values() if c > 0)
    no_train_but_has_test = [
        ft for ft in test_counter if train_counter.get(ft, 0) == 0
    ]

    return {
        "train_total": ds_total,
        "test_total": ts_total,
        "train_fault_types": train_types_with_samples,
        "test_fault_types": test_types_with_samples,
        "no_train_has_test": no_train_but_has_test,
        "train_distribution": dict(train_counter.most_common()),
        "test_distribution": dict(test_counter.most_common()),
        "train_details": dict(train_type_details),
        "test_details": dict(test_type_details),
        "merge_map": merge_map,
    }


# ─── HTML 报告生成 ───

def generate_html_report(
    overview: dict,
    results: list,
    mismatches: list,
    top1_accuracy: float,
    top3_accuracy: float,
    per_type_stats: dict,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    train_dist = overview["train_distribution"]
    test_dist = overview["test_distribution"]

    # 训练集分布表格行
    train_rows = ""
    for ft, count in sorted(train_dist.items(), key=lambda x: -x[1]):
        train_rows += f"<tr><td><code>{ft}</code></td><td>{count}</td></tr>"

    # 测试集分布表格行
    test_rows = ""
    for ft, count in sorted(test_dist.items(), key=lambda x: -x[1]):
        train_count = train_dist.get(ft, 0)
        badge = ""
        if train_count == 0:
            badge = ' <span class="badge-no-train">无训练样本</span>'
        test_rows += f"<tr><td><code>{ft}</code>{badge}</td><td>{count}</td><td>{train_count}</td></tr>"

    # 按故障类型准确率表格
    perf_rows = ""
    for ft, stats in sorted(per_type_stats.items(), key=lambda x: -x[1].get("count", 0)):
        count = stats.get("count", 0)
        top1_correct = stats.get("top1_correct", 0)
        top3_correct = stats.get("top3_correct", 0)
        top1_rate = (top1_correct / count * 100) if count > 0 else 0
        top3_rate = (top3_correct / count * 100) if count > 0 else 0
        color = "#27ae60" if top1_rate >= 70 else ("#f39c12" if top1_rate >= 40 else "#e74c3c")
        perf_rows += f"""<tr>
            <td><code>{ft}</code></td>
            <td>{count}</td>
            <td style="color:{color};font-weight:bold">{top1_correct}/{count} ({top1_rate:.1f}%)</td>
            <td>{top3_correct}/{count} ({top3_rate:.1f}%)</td>
        </tr>"""

    # 未命中案例表格
    mismatch_rows = ""
    for m in mismatches[:50]:  # 最多显示50条
        top3 = ", ".join([f"{p['fault_type']} ({p['similarity']:.1%})" for p in m.get("top3", [])])
        top3_short = ", ".join([p["fault_type"] for p in m.get("top3", [])])
        mismatch_rows += f"""<tr>
            <td><code>{m['case_name']}</code></td>
            <td><code>{m['true_type']}</code></td>
            <td class="mismatch">❌</td>
            <td>{m.get('top1_pred', 'N/A')}</td>
            <td>{top3_short}</td>
            <td>{m.get('top1_similarity', 0):.1%}</td>
        </tr>"""

    # 无训练样本但有测试样本的故障类型
    no_train_list = "".join(
        f"<li><code>{ft}</code>（{test_dist.get(ft, 0)} 个测试案例）</li>"
        for ft in overview["no_train_has_test"]
    ) or "<li>无</li>"

    # 总体指标颜色
    top1_color = "#27ae60" if top1_accuracy >= 70 else ("#f39c12" if top1_accuracy >= 40 else "#e74c3c")
    top3_color = "#27ae60" if top3_accuracy >= 70 else ("#f39c12" if top3_accuracy >= 40 else "#e74c3c")

    # 正确案例数
    total = len(results)
    top1_correct_total = sum(1 for r in results if r.get("top1_correct", False))
    top3_correct_total = sum(1 for r in results if r.get("top3_correct", False))
    no_result = sum(1 for r in results if r.get("error", ""))

    # 按类别分组
    latency_cases = [r for r in results if r.get("category") == "latency"]
    connectivity_cases = [r for r in results if r.get("category") == "connectivity"]
    latency_top1 = sum(1 for r in latency_cases if r.get("top1_correct", False))
    conn_top1 = sum(1 for r in connectivity_cases if r.get("top1_correct", False))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>灵衢 KVCache 故障诊断评估报告</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: #f5f7fa;
    color: #333;
    line-height: 1.6;
    padding: 20px;
}}
.container {{
    max-width: 1400px;
    margin: 0 auto;
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    overflow: hidden;
}}
.header {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 32px 40px;
}}
.header h1 {{
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 8px;
}}
.header .subtitle {{
    font-size: 14px;
    opacity: 0.9;
}}
.content {{
    padding: 32px 40px;
}}
.section {{
    margin-bottom: 40px;
}}
.section h2 {{
    font-size: 20px;
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 3px solid #667eea;
    display: inline-block;
}}
.section h3 {{
    font-size: 16px;
    font-weight: 600;
    color: #34495e;
    margin: 20px 0 12px 0;
}}
.metrics-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 32px;
}}
.metric-card {{
    background: linear-gradient(135deg, #f8f9ff 0%, #eef1ff 100%);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    border: 1px solid #e4e8f0;
}}
.metric-card .value {{
    font-size: 36px;
    font-weight: 800;
    margin-bottom: 4px;
}}
.metric-card .label {{
    font-size: 13px;
    color: #7f8c8d;
    font-weight: 500;
}}
.metric-card.highlight {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
}}
.metric-card.highlight .label {{ color: rgba(255,255,255,0.9); }}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin-bottom: 16px;
}}
th {{
    background: #f8f9fa;
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    color: #2c3e50;
    border-bottom: 2px solid #dee2e6;
    white-space: nowrap;
}}
td {{
    padding: 8px 12px;
    border-bottom: 1px solid #eee;
    white-space: nowrap;
}}
tr:hover td {{ background: #f8f9ff; }}
code {{
    background: #f0f2f5;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'SF Mono', Monaco, Consolas, monospace;
    font-size: 12px;
}}
.badge-no-train {{
    background: #fff3cd;
    color: #856404;
    padding: 1px 6px;
    border-radius: 8px;
    font-size: 10px;
    margin-left: 4px;
}}
.mismatch {{
    color: #e74c3c;
    font-weight: bold;
}}
.match {{
    color: #27ae60;
    font-weight: bold;
}}
.two-col {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
}}
@media (max-width: 900px) {{
    .two-col {{ grid-template-columns: 1fr; }}
    .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
.legend {{
    font-size: 12px;
    color: #7f8c8d;
    margin-bottom: 12px;
}}
.legend span {{
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 3px;
    margin-right: 4px;
    vertical-align: middle;
}}
.legend .green {{ background: #27ae60; }}
.legend .orange {{ background: #f39c12; }}
.legend .red {{ background: #e74c3c; }}
.note {{
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 13px;
    color: #856404;
    margin: 16px 0;
}}
.footer {{
    text-align: center;
    padding: 20px;
    color: #95a5a6;
    font-size: 12px;
    border-top: 1px solid #ecf0f1;
}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🔍 灵衢 KVCache 故障诊断评估报告</h1>
        <div class="subtitle">生成时间：{now} · 评估引擎：相似度匹配 (Top-K Similarity) · 后端：{BACKEND_URL}</div>
    </div>
    <div class="content">

        <!-- ===== 总体指标 ===== -->
        <div class="section">
            <h2>📊 评估结果总览</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="value" style="color:#667eea">{total}</div>
                    <div class="label">测试案例总数</div>
                </div>
                <div class="metric-card highlight">
                    <div class="value">{top1_accuracy:.1f}%</div>
                    <div class="label">Top-1 准确率</div>
                </div>
                <div class="metric-card highlight">
                    <div class="value">{top3_accuracy:.1f}%</div>
                    <div class="label">Top-3 召回率</div>
                </div>
                <div class="metric-card">
                    <div class="value" style="color:#e74c3c">{len(mismatches)}</div>
                    <div class="label">未命中案例数</div>
                </div>
            </div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="value" style="color:#3498db">{latency_top1}/{len(latency_cases)}</div>
                    <div class="label">时延故障 Top-1</div>
                </div>
                <div class="metric-card">
                    <div class="value" style="color:#e74c3c">{conn_top1}/{len(connectivity_cases)}</div>
                    <div class="label">通断故障 Top-1</div>
                </div>
                <div class="metric-card">
                    <div class="value" style="color:#27ae60">{no_result}</div>
                    <div class="label">无结果案例</div>
                </div>
                <div class="metric-card">
                    <div class="value" style="color:#9b59b6">{overview['train_fault_types']}</div>
                    <div class="label">覆盖训练故障类型数</div>
                </div>
            </div>
        </div>

        <!-- ===== 数据集概况 ===== -->
        <div class="section">
            <h2>📚 数据集概况</h2>
            <div class="two-col">
                <div>
                    <h3>训练集 (data_set)</h3>
                    <p style="font-size:13px;color:#7f8c8d;margin-bottom:8px">
                        共 <b>{overview['train_total']}</b> 个案例，覆盖 <b>{overview['train_fault_types']}</b> 种故障类型
                    </p>
                    <table>
                        <thead><tr><th>故障类型</th><th>数量</th></tr></thead>
                        <tbody>{train_rows}</tbody>
                    </table>
                </div>
                <div>
                    <h3>测试集 (test_set)</h3>
                    <p style="font-size:13px;color:#7f8c8d;margin-bottom:8px">
                        共 <b>{overview['test_total']}</b> 个案例，覆盖 <b>{overview['test_fault_types']}</b> 种故障类型
                    </p>
                    <div class="note">
                        <b>⚠️ 零训练样本故障类型</b>（测试集中有但训练集中没有）：
                        <ul style="margin:8px 0 0 16px">{no_train_list}</ul>
                    </div>
                    <table>
                        <thead><tr><th>故障类型</th><th>测试数</th><th>训练数</th></tr></thead>
                        <tbody>{test_rows}</tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ===== 按故障类型准确率 ===== -->
        <div class="section">
            <h2>🎯 按故障类型准确率</h2>
            <div class="legend">
                <span class="green"></span> ≥70% 
                <span class="orange"></span> 40-69% 
                <span class="red"></span> <40%
            </div>
            <table>
                <thead><tr><th>故障类型</th><th>测试数</th><th>Top-1</th><th>Top-3</th></tr></thead>
                <tbody>{perf_rows}</tbody>
            </table>
        </div>

        <!-- ===== 未命中案例分析 ===== -->
        <div class="section">
            <h2>🔍 未命中案例分析 (共 {len(mismatches)} 个)</h2>
            <p style="font-size:13px;color:#7f8c8d;margin-bottom:12px">
                以下案例的 Top-1 预测与真实标签不匹配。Top-3 列展示预测到的故障类型列表。
            </p>
            <table>
                <thead><tr><th>案例名称</th><th>真实类型</th><th>匹配</th><th>Top-1 预测</th><th>Top-3 预测</th><th>Top-1 相似度</th></tr></thead>
                <tbody>{mismatch_rows if mismatch_rows else '<tr><td colspan="6" style="text-align:center;color:#27ae60">🎉 所有案例均命中！</td></tr>'}</tbody>
            </table>
        </div>

    </div>
    <div class="footer">
        灵衢 UB 超节点故障智能诊断平台 · 评估报告自动生成
    </div>
</div>
</body>
</html>"""
    return html


# ─── 主流程 ───

def main():
    print("=" * 60)
    print("灵衢 KVCache 故障诊断评估")
    print("=" * 60)

    # 1. 加载数据集概况
    print("\n📚 加载数据集概况...")
    summary = load_dataset_summary()
    overview = build_dataset_overview(summary)
    truth_map = build_truth_map(summary)
    print(f"  训练集: {overview['train_total']} 案例, {overview['train_fault_types']} 种故障类型")
    print(f"  测试集: {overview['test_total']} 案例, {overview['test_fault_types']} 种故障类型")
    print(f"  零训练样本故障类型: {overview['no_train_has_test']}")

    # 2. 获取 test_set 知识库
    print("\n🔍 查找 test_set 知识库...")
    kbs = api_list_kb(TEST_SET_KB_NAME)
    test_kb = None
    for kb in kbs:
        if kb.get("name") == TEST_SET_KB_NAME:
            test_kb = kb
            break
    if not test_kb and kbs:
        # 查找包含 test_set 的
        for kb in kbs:
            if TEST_SET_KB_NAME in kb.get("name", ""):
                test_kb = kb
                break
        if not test_kb:
            test_kb = kbs[0]
            print(f"  未找到精确匹配，使用首个知识库: {test_kb.get('name')}")
    if not test_kb:
        print("  ❌ 未找到 test_set 知识库！")
        sys.exit(1)
    kb_id = test_kb["id"]
    print(f"  知识库: {test_kb.get('name')} (id={kb_id})")

    # 3. 获取日志文件列表
    print("\n📋 获取日志文件列表...")
    log_files = api_list_log_files(kb_id)
    print(f"  共 {len(log_files)} 个日志文件")

    # 4. 对每个日志运行相似度分析
    print("\n🔬 运行相似度分析...")
    results = []
    for i, lf in enumerate(log_files):
        log_id = lf.get("id", "")
        log_name = lf.get("name", "")
        # log_name 格式: "yxh_new_0530/lingqu_kvcache_xxx"
        # case_name 应该是 "lingqu_kvcache_xxx"（不带 source 前缀）
        case_name = log_name
        if "/" in case_name:
            case_name = case_name.split("/", 1)[1]
        print(f"  [{i+1}/{len(log_files)}] {case_name[:60]}...", end=" ")

        result = {
            "log_file_id": log_id,
            "log_name": log_name,
            "case_name": case_name,
            "top1_pred": "",
            "top1_similarity": 0,
            "top1_correct": False,
            "top3_correct": False,
            "top3": [],
            "error": "",
            "true_type": "",
            "merged_type": "",
            "category": "",
        }

        # 查找真实标签（使用不带 source 前缀的 case_name）
        truth = truth_map.get(case_name, {})
        result["true_type"] = truth.get("true_type", "")
        result["merged_type"] = truth.get("merged_type", "")

        try:
            resp = api_similarity_analysis(log_id, top_k=3)
            top_matches = resp.get("result", {}).get("top_matches", [])
            result["top3"] = [
                {
                    "fault_type": m.get("root_cause_type", ""),
                    "similarity": m.get("similarity", 0),
                    "category": m.get("fault_category", ""),
                }
                for m in top_matches
            ]
            result["library_size"] = resp.get("result", {}).get("library_size", 0)

            if result["top3"]:
                result["top1_pred"] = result["top3"][0]["fault_type"]
                result["top1_similarity"] = result["top3"][0]["similarity"]

            # 计算是否正确
            true_type = result["merged_type"] or result["true_type"]
            if true_type:
                result["top1_correct"] = result["top1_pred"] == true_type
                result["top3_correct"] = any(
                    m["fault_type"] == true_type for m in result["top3"]
                )
                # 从 top3 第一个结果获取 category
                if result["top3"]:
                    result["category"] = result["top3"][0].get("category", "")

            if result["top1_correct"]:
                print("✅")
            elif result["top3_correct"]:
                print("🟡 (Top-3 命中)")
            else:
                print("❌")
        except Exception as e:
            result["error"] = str(e)
            print(f"⚠️ 错误: {e}")

        results.append(result)
        # 避免请求过于频繁
        time.sleep(0.1)

    # 5. 计算统计指标
    print("\n📊 计算评估指标...")
    total = len(results)
    top1_correct_total = sum(1 for r in results if r.get("top1_correct", False))
    top3_correct_total = sum(1 for r in results if r.get("top3_correct", False))
    top1_accuracy = (top1_correct_total / total * 100) if total > 0 else 0
    top3_accuracy = (top3_correct_total / total * 100) if total > 0 else 0

    # 按故障类型统计
    per_type_stats = defaultdict(lambda: {"count": 0, "top1_correct": 0, "top3_correct": 0})
    for r in results:
        ft = r["true_type"] or "unknown"
        per_type_stats[ft]["count"] += 1
        if r.get("top1_correct", False):
            per_type_stats[ft]["top1_correct"] += 1
        if r.get("top3_correct", False):
            per_type_stats[ft]["top3_correct"] += 1

    # 收集未命中案例
    mismatches = [r for r in results if not r.get("top1_correct", False)]

    print(f"  Top-1 准确率: {top1_accuracy:.1f}% ({top1_correct_total}/{total})")
    print(f"  Top-3 召回率: {top3_accuracy:.1f}% ({top3_correct_total}/{total})")
    print(f"  未命中案例: {len(mismatches)}")

    # 6. 生成 HTML 报告
    print("\n📝 生成 HTML 报告...")
    html = generate_html_report(
        overview=overview,
        results=results,
        mismatches=mismatches,
        top1_accuracy=top1_accuracy,
        top3_accuracy=top3_accuracy,
        per_type_stats=dict(per_type_stats),
    )

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ 报告已生成: {OUTPUT_HTML}")

    # 保存原始结果为 JSON
    json_output = OUTPUT_HTML.replace(".html", ".json")
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "overview": overview,
            "results": results,
            "top1_accuracy": top1_accuracy,
            "top3_accuracy": top3_accuracy,
            "mismatches": mismatches,
            "per_type_stats": dict(per_type_stats),
        }, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 原始数据: {json_output}")

    print("\n" + "=" * 60)
    print("评估完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()