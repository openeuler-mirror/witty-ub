#!/usr/bin/env python3
"""分析案例库分布 + 10 个测试案例的命中情况，给出提升命中率的具体建议。

用法:
    PYTHONPATH=src/plugins src/plugins/latency/.venv/bin/python scripts/analyze_hitrate.py
"""

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.services.case_service import CASE_DIR
from latency.services.similarity import (
    FeatureVector,
    compute_similarity_detailed,
    load_case_library,
)

# 大类映射（与 run_new_case_match.py 一致）
TYPE_TO_BROAD = {
    "本地UB单端口down": "UB-端口故障",
    "本地UB全部端口不可用": "UB-端口故障",
    "本地UB全部端口down": "UB-端口故障",
    "本地UB全部端口lane down": "UB-端口故障",
    "本地UB全部端口链路丢失": "UB-端口故障",
    "本地UB双端口闪断": "UB-端口故障",
    "本地UB单socket双端口down": "UB-端口故障",
    "本地UB双socket单端口down": "UB-端口故障",
    "远端UB单端口down": "UB-端口故障",
    "远端UB双socket单端口down": "UB-端口故障",
    "远端UB单socket双端口down": "UB-端口故障",
    "远端UB全部端口down": "UB-端口故障",
    "Worker本地UB链路down": "UB-链路故障",
    "Worker远端UB单链路down": "UB-链路故障",
    "Worker远端UB信号错误": "UB-链路故障",
    "Worker远端UB NFE": "UB-链路故障",
    "Worker远端UB CE": "UB-链路故障",
    "Worker远端UB FE": "UB-链路故障",
    "Worker远端本地UB单端口down": "UB-链路故障",
    "Worker远端本地UB链路丢失": "UB-链路故障",
    "Worker远端本地UB链路闪断": "UB-链路故障",
    "Worker远端本地UB lane down": "UB-链路故障",
    "Worker远端远端UB单端口down": "UB-链路故障",
    "Worker缩容远端UB NFE": "UB-链路故障",
    "Worker缩容远端UB链路down": "UB-链路故障",
    "Client获取UB失败": "UB-链路故障",
    "Client获取UBSe失败": "UB-UBSe/UBM管理进程故障",
    "Client获取UBM失败": "UB-UBSe/UBM管理进程故障",
    "Client远端写入后UBSe故障": "UB-UBSe/UBM管理进程故障",
    "Client远端写入后UBM故障": "UB-UBSe/UBM管理进程故障",
    "Worker进程退出": "Worker-退出/崩溃",
    "Worker进程被kill": "Worker-退出/崩溃",
    "Worker单节点进程退出": "Worker-退出/崩溃",
    "Worker Pod重启": "Worker-重启",
    "Worker Pod重启(L2)": "Worker-重启",
    "Worker单节点重启": "Worker-重启",
    "Worker发现进程挂死": "Worker-缩容/挂死",
    "Worker缩容Client退出": "Worker-缩容/挂死",
    "Worker缩容TCP丢包": "Worker-缩容/挂死",
    "Worker缩容Client挂死": "Worker-缩容/挂死",
    "Worker缩容TCP down": "Worker-缩容/挂死",
    "Client缩容Worker挂死": "Worker-缩容/挂死",
    "Client进程退出": "Client-退出",
    "Client进程退出启动": "Client-退出",
    "Client获取退出启动": "Client-退出",
    "Client进程挂死": "Client-挂死/网络",
    "Client获取挂死": "Client-挂死/网络",
    "Client TCP down": "Client-挂死/网络",
    "Client缩容TCP down": "Client-挂死/网络",
    "远端写入TCP延迟": "网络/TCP故障",
    "Worker跨节点网卡丢包": "网络/TCP故障",
    "Worker写入网卡丢包": "网络/TCP故障",
    "Worker网卡丢包": "网络/TCP故障",
    # 新增小类
    "Client Pod重启": "Client-退出",
    "Client进程跨节点退出": "Client-退出",
    "Client进程挂死(r)": "Client-挂死/网络",
    "SDK安装TCP网络down": "网络/TCP故障",
    "Worker带宽限制": "网络/TCP故障",
    "Worker UB端口闪断故障": "UB-端口故障",
    "Worker获取退出启动": "Worker-退出/崩溃",
    "Worker远端UB链路down": "UB-链路故障",
    "Client进程退出(跨节点)": "Client-退出",
    "Worker进程退出(跨节点)": "Worker-退出/崩溃",
}


def analyze_library_distribution():
    """统计案例库每个大类的样本数量、特征完整性。"""
    print("=" * 70)
    print("[1] 案例库分布统计")
    print("=" * 70)

    case_files = [
        f for f in sorted(os.listdir(CASE_DIR))
        if f.endswith(".json") and not f.startswith("_")
    ]
    print(f"案例库共 {len(case_files)} 个案例")

    broad_counter = Counter()
    sub_counter = Counter()
    no_features = []
    no_log_file = []
    no_root_cause = []
    broad_sub_map = defaultdict(set)

    for fname in case_files:
        fpath = os.path.join(CASE_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            case = json.load(f)

        rct = case.get("root_cause_type", "")
        if not rct:
            no_root_cause.append(fname)
            continue
        broad = TYPE_TO_BROAD.get(rct, "未分类(无映射)")
        broad_counter[broad] += 1
        sub_counter[rct] += 1
        broad_sub_map[broad].add(rct)

        if not case.get("features"):
            no_features.append((fname, rct, broad))
        if not case.get("log_file_id"):
            no_log_file.append((fname, rct, broad))

    print(f"\n各大类案例数（按数量降序）:")
    for broad, n in broad_counter.most_common():
        subs = len(broad_sub_map[broad])
        print(f"  {broad:30s}  {n:4d} 个案例  ({subs} 个子类)")

    print(f"\n未提取 features 的案例: {len(no_features)} 个")
    for fname, rct, broad in no_features[:10]:
        print(f"  - {fname[:12]}  rct={rct}  broad={broad}")

    print(f"\n无 log_file_id 的案例: {len(no_log_file)} 个")

    print(f"\n无 root_cause_type 的案例: {len(no_root_cause)} 个")

    return broad_counter, sub_counter, broad_sub_map


def analyze_each_test_case_hit():
    """详细分析每个测试案例的命中情况和 Top1/Top2 大类的得分差。"""
    print("\n" + "=" * 70)
    print("[2] 10 个测试案例的逐个命中分析")
    print("=" * 70)

    with open("/Users/zhaoyujin/Desktop/witty-ub/scripts/new_case_hitrate_results.json",
              "r", encoding="utf-8") as f:
        results = json.load(f)

    # 按预期大类分组
    by_expected = defaultdict(list)
    for r in results["results"]:
        by_expected[r["expected_broad"]].append(r)

    print("\n按预期大类分组统计:")
    for broad, items in by_expected.items():
        n = len(items)
        h1 = sum(1 for r in items if r["hit1"])
        h3 = sum(1 for r in items if r["hit3"])
        h5 = sum(1 for r in items if r["hit5"])
        print(f"  {broad:30s}  样本={n}  Top1={h1}/{n}  Top3={h3}/{n}  Top5={h5}/{n}")

    print("\n每个测试案例的详细命中分析:")
    for i, r in enumerate(results["results"], 1):
        fname = r["test_case"]
        rct = r["root_cause_type"]
        expected = r["expected_broad"]
        top1 = r["top1"]
        scores = r["top5_scores"]

        print(f"\n--- [{i}/10] {fname[:12]} ---")
        print(f"  故障类型: {rct}")
        print(f"  预期大类: {expected}")
        print(f"  Top1: {top1}  {'✓命中' if r['hit1'] else '✗未命中'}")
        print(f"  Top3: {r['top3']}  {'✓命中' if r['hit3'] else '✗未命中'}")
        print(f"  Top5: {r['top5']}  {'✓命中' if r['hit5'] else '✗未命中'}")
        print(f"  Top5 大类得分:")
        for s in scores:
            mark = "  ← 预期" if s["broad_category"] == expected else ""
            print(f"    {s['broad_category']:25s}  score={s['score']:.4f}{mark}")

        # 分析 Top1 与预期大类的差距
        if not r["hit1"]:
            expected_score = next(
                (s["score"] for s in scores if s["broad_category"] == expected),
                None
            )
            top1_score = scores[0]["score"] if scores else 0
            if expected_score is not None:
                gap = top1_score - expected_score
                print(f"  ⚠ Top1 比 预期大类 高 {gap:.4f} (Top1={top1_score:.4f}, 预期={expected_score:.4f})")
            else:
                print(f"  ⚠ 预期大类 {expected} 未进入 Top5！Top1={top1_score:.4f}")


def analyze_feature_gap_for_missed_cases():
    """针对未命中的案例，分析其特征与案例库中正确大类案例的特征差异。"""
    print("\n" + "=" * 70)
    print("[3] 未命中案例的特征差异分析")
    print("=" * 70)

    # 加载案例库
    library_cases = load_case_library()
    print(f"案例库中含 features 的案例: {len(library_cases)}")

    # 按大类组织案例
    broad_cases = defaultdict(list)
    for case in library_cases:
        rct = case.get("root_cause_type", "")
        broad = TYPE_TO_BROAD.get(rct, "未分类")
        broad_cases[broad].append(case)

    # 加载测试案例
    new_case_dir = "/Users/zhaoyujin/Desktop/new_case"
    test_cases = []
    for fname in sorted(os.listdir(new_case_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(new_case_dir, fname), "r", encoding="utf-8") as f:
            tc = json.load(f)
        if tc.get("features"):
            tc["_fname"] = fname
            test_cases.append(tc)

    # 找出未命中的测试案例
    with open("/Users/zhaoyujin/Desktop/witty-ub/scripts/new_case_hitrate_results.json",
              "r", encoding="utf-8") as f:
        results = json.load(f)

    missed_fnames = {r["test_case"] for r in results["results"] if not r["hit5"]}
    print(f"未命中(Top5 不含预期大类)的测试案例: {len(missed_fnames)} 个")

    for tc in test_cases:
        if tc["_fname"] not in missed_fnames:
            continue

        rct = tc.get("root_cause_type", "")
        # 推断预期大类（与 run_new_case_match.py 一致）
        expected_broad = infer_expected_broad(rct)

        print(f"\n--- {tc['_fname'][:12]}  rct={rct}  预期={expected_broad} ---")

        query_fv = FeatureVector(tc["features"], tc.get("fault_category", "unknown"))

        # 显示测试案例的关键特征
        print(f"  测试案例特征:")
        print(f"    fault_category: {tc.get('fault_category', '?')}")
        if query_fv.latency:
            print(f"    pod_concentration: '{query_fv.pod_concentration}'")
            print(f"    p99_p50: {query_fv.p99_p50}")
            print(f"    operation_dist: {dict(list(query_fv.operation_dist.items())[:5])}")
            print(f"    seg_ranking_ordered(top5): {query_fv.seg_ranking_ordered[:5]}")
            print(f"    client_side_ratio: {query_fv.client_side_ratio:.3f}")
            print(f"    server_side_ratio: {query_fv.server_side_ratio:.3f}")
            print(f"    trace_context_pods: {query_fv.trace_context_pods}")
            print(f"    anomalous_ratio: {query_fv.anomalous_ratio:.3f}")
        if query_fv.connectivity:
            print(f"    failure_mode_dist: {dict(list(query_fv.failure_mode_dist.items())[:5])}")
            print(f"    status_code_dist: {dict(list(query_fv.status_code_dist.items())[:5])}")
            print(f"    pod_scope: '{query_fv.pod_scope}'")
            print(f"    host_scope: '{query_fv.host_scope}'")

        # 案例库中预期大类的所有案例
        if expected_broad in broad_cases:
            expected_cases = broad_cases[expected_broad]
            print(f"\n  案例库中 {expected_broad} 共 {len(expected_cases)} 个案例，平均特征:")

            # 计算预期大类案例的平均特征
            n = len(expected_cases)
            sum_p99 = sum(c.get("features", {}).get("latency", {}).get("p99_p50_ratio", 0) or 0
                          for c in expected_cases) / n
            sum_client = sum(FeatureVector(c["features"], c.get("fault_category", "")).client_side_ratio
                             for c in expected_cases) / n
            sum_server = sum(FeatureVector(c["features"], c.get("fault_category", "")).server_side_ratio
                             for c in expected_cases) / n
            sum_pods = sum(FeatureVector(c["features"], c.get("fault_category", "")).trace_context_pods
                          for c in expected_cases) / n
            sum_anom = sum(FeatureVector(c["features"], c.get("fault_category", "")).anomalous_ratio
                          for c in expected_cases) / n

            print(f"    平均 p99_p50: {sum_p99:.3f}")
            print(f"    平均 client_side_ratio: {sum_client:.3f}")
            print(f"    平均 server_side_ratio: {sum_server:.3f}")
            print(f"    平均 trace_context_pods: {sum_pods:.1f}")
            print(f"    平均 anomalous_ratio: {sum_anom:.3f}")

            # 找出与测试案例最相似的预期大类案例
            scored_expected = []
            for case in expected_cases:
                case_fv = FeatureVector(case["features"], case.get("fault_category", "unknown"))
                detail = compute_similarity_detailed(query_fv, case_fv)
                scored_expected.append({
                    "case_id": case.get("id", ""),
                    "log_file_name": case.get("log_file_name", ""),
                    "score": detail["final_score"],
                    "base_score": detail["base_score"],
                    "cat_gate": detail["cat_gate"],
                    "asym_gate": detail["asym_gate"],
                    "rct": case.get("root_cause_type", ""),
                })
            scored_expected.sort(key=lambda x: -x["score"])

            print(f"\n  与预期大类案例的最高 3 个相似度:")
            for s in scored_expected[:3]:
                print(f"    score={s['score']:.4f} base={s['base_score']:.4f} "
                      f"cat_gate={s['cat_gate']:.2f} asym_gate={s['asym_gate']:.2f} "
                      f"rct={s['rct']}")

            # 显示这个最相似案例的特征
            if scored_expected:
                best_case = next((c for c in expected_cases
                                  if c.get("id") == scored_expected[0]["case_id"]), None)
                if best_case:
                    best_fv = FeatureVector(best_case["features"],
                                           best_case.get("fault_category", "unknown"))
                    print(f"\n  最相似案例的特征:")
                    print(f"    fault_category: {best_case.get('fault_category', '?')}")
                    if best_fv.latency:
                        print(f"    pod_concentration: '{best_fv.pod_concentration}'")
                        print(f"    p99_p50: {best_fv.p99_p50}")
                        print(f"    seg_ranking_ordered(top5): {best_fv.seg_ranking_ordered[:5]}")
                        print(f"    client_side_ratio: {best_fv.client_side_ratio:.3f}")
                        print(f"    server_side_ratio: {best_fv.server_side_ratio:.3f}")
                        print(f"    trace_context_pods: {best_fv.trace_context_pods}")
                        print(f"    anomalous_ratio: {best_fv.anomalous_ratio:.3f}")
                    if best_fv.connectivity:
                        print(f"    failure_mode_dist: {dict(list(best_fv.failure_mode_dist.items())[:5])}")
                        print(f"    status_code_dist: {dict(list(best_fv.status_code_dist.items())[:5])}")
        else:
            print(f"  ⚠ 案例库中没有 {expected_broad} 大类的案例！")


def infer_expected_broad(rct: str) -> str:
    """与 run_new_case_match.py 保持一致。"""
    rct_lower = rct.lower() if rct else ""
    if "cpu" in rct_lower and "挂" in rct:
        return "Worker-缩容/挂死"
    if "sdk" in rct_lower and ("初始化" in rct or "配置" in rct):
        return "SDK初始化配置错误"
    if "ub端口" in rct_lower or "ub" in rct_lower and "端口" in rct:
        return "UB-端口故障"
    if "ub链路" in rct_lower or ("ub" in rct_lower and "链路" in rct):
        return "UB-链路故障"
    if "l1" in rct_lower and ("端口" in rct or "闪断" in rct or "shutdown" in rct_lower):
        return "网络/TCP故障"
    if "端侧" in rct and "l1" in rct_lower:
        return "网络/TCP故障"
    if "tcp" in rct_lower and "down" in rct_lower:
        return "网络/TCP故障"
    if "worker" in rct_lower and ("退出" in rct or "异常" in rct):
        return "Worker-退出/崩溃"
    if "交换机" in rct and "l1" in rct_lower:
        return "网络/TCP故障"
    return "未知"


def main():
    analyze_library_distribution()
    analyze_each_test_case_hit()
    analyze_feature_gap_for_missed_cases()

    print("\n" + "=" * 70)
    print("[4] 提升命中率的具体建议")
    print("=" * 70)
    print("""
基于上述分析，给出以下提升命中率的具体建议:

1. **案例库覆盖不全**:
   - SDK初始化配置错误: 案例库中无此类案例，应补充 5-10 个 SDK 初始化配置错误案例
   - 网络/TCP故障 Top5 都未命中: 案例库中虽然已有 4 个网络/TCP故障 子类，但特征提取
     不够明显。应增加 L1-L2 互联链路、shutdown 闪断等具体场景

2. **特征提取不完整**:
   - TCPdown (cb9b7dc5) 所有得分都极低 (~0.04)，特征向量几乎为 0，
     说明该案例的日志解析没有提取到有效特征。需检查特征提取脚本对该日志的处理

3. **相似度计算需要增强区分度**:
   - UB-链路故障 vs UB-端口故障: 多次混淆，需要增加区分 UB 链路 vs 端口的特征维度
   - Worker-重启 vs Worker-退出/崩溃: 也很容易混淆，需要增强进程状态相关特征
   - 网络/TCP故障 与 UB-端口故障 / Worker-缩容/挂死 经常混淆

4. **cat_gate 门控可能过于宽容**:
   - 当前 fault_category 一致时 cat_gate=1.0，不一致时=0.25
   - 但 fault_category 自动分类只有 'latency'/'connectivity'/'mixed'/'unknown' 四种
   - 建议增加 fault_category 自动分类的精细度，或者引入更精细的 secondary_category

5. **权重调整建议**:
   - 当前 failure_mode (6.0) 和 op_p99_p50 (4.0) 权重最高
   - 但很多故障 failure_mode 为空，导致权重浪费
   - 建议在 failure_mode 为空时，将权重重新分配给 connectivity 相关维度

6. **asym_gate 不对称惩罚可能过强**:
   - 当一方有 failure_mode/status_code 而另一方没有时，惩罚系数为 0.3/0.4
   - 这导致测试案例只要 features 完整而案例库中案例 features 不完整，就会被严重压低
   - 建议重新提取所有案例库案例的 features，确保完整性

7. **大类去重可能丢失关键信号**:
   - 每个大类只保留最高分，但有时最高分子类并不是真正的故障类型
   - 建议引入子类层面的加权投票，让大类得分综合考虑多个子类的命中情况
""")


if __name__ == "__main__":
    main()
