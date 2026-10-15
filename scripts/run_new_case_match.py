#!/usr/bin/env python3
"""提取案例库 features + 对 new_case 测试集进行相似案例匹配，计算大类命中率 Top1/3/5。

流程:
1. 遍历案例库 112 个案例，用 log_file_id 调用 API 提取 features
2. 将 features 写回案例 JSON
3. 遍历 new_case 10 个测试案例，用相似度服务匹配案例库
4. 按大类统计 Top1/3/5 命中率

用法:
    PYTHONPATH=src/plugins src/plugins/latency/.venv/bin/python scripts/run_new_case_match.py
"""

import asyncio
import json
import os
import sys

# 确保 import 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "plugins"))

from latency.config.config import Config
from latency.database.engine import PGManager
from latency.services.feature_extraction import FeatureExtractionManager
from latency.services.similarity import (
    FeatureVector,
    compute_similarity_detailed,
    merge_fault_type,
    load_case_library,
)
from latency.services.case_service import CASE_DIR


async def init_pg():
    """初始化 PGManager 数据库连接。"""
    config = Config().get_config()
    PGManager.initialize(
        config.db.pg_dsn_url(),
        pool_size=config.db.pg_pool_size,
        max_overflow=config.db.pg_max_overflow,
    )
    await PGManager.init_timezone()
    print("PGManager 初始化完成")

NEW_CASE_DIR = "/Users/zhaoyujin/Desktop/new_case"
API = "http://127.0.0.1:9772"

# 大类映射（与 rebuild_case_library_v2.py 一致，中文小类 → 大类）
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
}


async def extract_and_update_case_features():
    """Step 1-2: 为案例库所有案例提取 features 并写回 JSON。"""
    print("=" * 70)
    print("[Step 1-2] 提取案例库 features")
    print("=" * 70)

    case_files = [
        f for f in sorted(os.listdir(CASE_DIR))
        if f.endswith(".json") and not f.startswith("_")
    ]
    print(f"案例库共 {len(case_files)} 个案例")

    ok = 0
    skip = 0
    fail = 0
    for i, fname in enumerate(case_files, 1):
        fpath = os.path.join(CASE_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            case = json.load(f)

        # 已有 features 则跳过
        if case.get("features"):
            ok += 1
            continue

        log_file_id = case.get("log_file_id", "")
        if not log_file_id:
            print(f"  [{i}/{len(case_files)}] {fname[:12]} 无 log_file_id，跳过")
            skip += 1
            continue

        try:
            features = await FeatureExtractionManager.extract_features(log_file_id)
            case["features"] = features
            case["fault_category"] = features.get("fault_category", "unknown")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(case, f, ensure_ascii=False, indent=2)
            fc = features.get("fault_category", "?")
            print(f"  [{i}/{len(case_files)}] {fname[:12]} OK  fault_category={fc}")
            ok += 1
        except Exception as e:
            print(f"  [{i}/{len(case_files)}] {fname[:12]} FAIL  {e}")
            fail += 1

    print(f"\n提取完成: OK={ok}  skip={skip}  fail={fail}")
    return ok


def match_test_cases():
    """Step 3-4: 对 new_case 测试集进行匹配，计算大类命中率。"""
    print("\n" + "=" * 70)
    print("[Step 3-4] 对 new_case 测试集进行相似案例匹配")
    print("=" * 70)

    # 加载案例库（含 features）
    library_cases = load_case_library()
    print(f"案例库中含 features 的案例: {len(library_cases)}")

    if not library_cases:
        print("错误: 案例库中无含 features 的案例，无法匹配")
        return

    # 构建案例库 FeatureVector 列表
    library_fvs = []
    for case in library_cases:
        fv = FeatureVector(
            case["features"],
            case.get("fault_category", "unknown"),
        )
        library_fvs.append({
            "fv": fv,
            "root_cause_type": case.get("root_cause_type", ""),
            "case_category": case.get("case_category", ""),
            "broad_category": TYPE_TO_BROAD.get(case.get("root_cause_type", ""), "未分类"),
            "case_id": case.get("id", ""),
            "log_file_name": case.get("log_file_name", ""),
        })

    # 遍历测试案例
    test_files = sorted([
        f for f in os.listdir(NEW_CASE_DIR)
        if f.endswith(".json")
    ])
    print(f"测试案例数: {len(test_files)}")

    results = []
    top1_hit = 0
    top3_hit = 0
    top5_hit = 0
    total = 0

    for i, fname in enumerate(test_files, 1):
        fpath = os.path.join(NEW_CASE_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            test_case = json.load(f)

        if not test_case.get("features"):
            print(f"  [{i}/{len(test_files)}] {fname[:12]} 无 features，跳过")
            continue

        # 测试案例的预期大类（根据 root_cause_type 人工标注）
        test_rct = test_case.get("root_cause_type", "")
        test_broad = test_case.get("case_category", "")  # 如果有
        # 从 root_cause_type 推断预期大类
        expected_broad = infer_expected_broad(test_rct)

        query_fv = FeatureVector(
            test_case["features"],
            test_case.get("fault_category", "unknown"),
        )

        # 计算与所有案例的相似度
        scored = []
        for lib in library_fvs:
            detail = compute_similarity_detailed(query_fv, lib["fv"])
            scored.append({
                **lib,
                "final_score": detail["final_score"],
                "reason": detail["reason"],
            })

        scored.sort(key=lambda x: -x["final_score"])

        # 按大类聚合：同一大类取最高分
        broad_scores = {}
        for s in scored:
            bc = s["broad_category"]
            if bc not in broad_scores:
                broad_scores[bc] = s
        broad_ranked = sorted(broad_scores.values(), key=lambda x: -x["final_score"])

        top1 = broad_ranked[0]["broad_category"] if len(broad_ranked) >= 1 else ""
        top3 = [r["broad_category"] for r in broad_ranked[:3]]
        top5 = [r["broad_category"] for r in broad_ranked[:5]]

        hit1 = expected_broad == top1 if expected_broad and top1 else False
        hit3 = expected_broad in top3 if expected_broad else False
        hit5 = expected_broad in top5 if expected_broad else False

        if hit1:
            top1_hit += 1
        if hit3:
            top3_hit += 1
        if hit5:
            top5_hit += 1
        total += 1

        mark1 = "✓" if hit1 else "✗"
        mark3 = "✓" if hit3 else "✗"
        mark5 = "✓" if hit5 else "✗"

        print(f"  [{i}/{len(test_files)}] {test_rct}")
        print(f"       预期大类: {expected_broad}")
        print(f"       Top1: {top1} {mark1}  | Top3: {top3} {mark3}  | Top5: {top5} {mark5}")
        print(f"       Top5 大类得分: {[(r['broad_category'], round(r['final_score'],4)) for r in broad_ranked[:5]]}")

        results.append({
            "test_case": fname,
            "root_cause_type": test_rct,
            "expected_broad": expected_broad,
            "top1": top1,
            "top3": top3,
            "top5": top5,
            "hit1": hit1,
            "hit3": hit3,
            "hit5": hit5,
            "top5_scores": [
                {"broad_category": r["broad_category"], "score": round(r["final_score"], 4)}
                for r in broad_ranked[:5]
            ],
        })

    print(f"\n{'=' * 70}")
    print(f"命中率统计 (共 {total} 个测试案例)")
    print(f"{'=' * 70}")
    print(f"  Top-1: {top1_hit}/{total} = {top1_hit/total*100:.1f}%" if total else "  Top-1: N/A")
    print(f"  Top-3: {top3_hit}/{total} = {top3_hit/total*100:.1f}%" if total else "  Top-3: N/A")
    print(f"  Top-5: {top5_hit}/{total} = {top5_hit/total*100:.1f}%" if total else "  Top-5: N/A")

    # 保存详细结果
    output_path = "/Users/zhaoyujin/Desktop/witty-ub/scripts/new_case_hitrate_results.json"
    summary = {
        "total": total,
        "top1_hit": top1_hit,
        "top3_hit": top3_hit,
        "top5_hit": top5_hit,
        "top1_rate": round(top1_hit / total * 100, 1) if total else 0,
        "top3_rate": round(top3_hit / total * 100, 1) if total else 0,
        "top5_rate": round(top5_hit / total * 100, 1) if total else 0,
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {output_path}")


def infer_expected_broad(rct: str) -> str:
    """根据测试案例的 root_cause_type 推断预期大类。"""
    rct_lower = rct.lower() if rct else ""
    # 关键词匹配
    if "cpu" in rct_lower and "挂" in rct:
        return "Worker-缩容/挂死"  # CPU挂死归入 Worker-缩容/挂死
    if "sdk" in rct_lower and ("初始化" in rct or "配置" in rct):
        return "SDK初始化配置错误"  # 不在案例库大类中
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


async def main():
    # Step 0: 初始化 PGManager
    await init_pg()

    # Step 1-2: 提取案例库 features
    await extract_and_update_case_features()

    # Step 3-4: 匹配测试案例
    match_test_cases()


if __name__ == "__main__":
    asyncio.run(main())
