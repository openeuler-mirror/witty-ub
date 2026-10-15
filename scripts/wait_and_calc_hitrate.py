#!/usr/bin/env python3
"""监控 test_set 解析进度，全部完成后自动计算 Top-1/3/5 命中率。

用法:
    python3 scripts/wait_and_calc_hitrate.py

每 30 秒查询一次 test_set 的 62 个案例解析状态，全部 successful 后
调用 calculate_test_set_hitrate.py 的逻辑重新计算命中率并输出结果。
"""
import json
import os
import sys
import time
import urllib.request

# 强制 stdout 不缓冲，确保后台运行时能实时看到输出
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, "reconfigure") else None

sys.path.insert(0, os.path.dirname(__file__))
from calculate_test_set_hitrate import (
    API_BASE,
    UPLOAD_RESULTS_PATH,
    extract_root_cause_type,
    BROAD_CATEGORY,
    api_post,
)

POLL_INTERVAL = 30  # 秒
MAX_WAIT = 3600 * 4  # 最长等待 4 小时


def get_test_set_status(up):
    """返回 (successful_count, pending_count, running_count, total)."""
    from collections import Counter
    c = Counter()
    for name, info in up.items():
        tid = info.get("task_id")
        try:
            url = f"{API_BASE}/task/{tid}"
            with urllib.request.urlopen(url, timeout=10) as r:
                d = json.loads(r.read().decode("utf-8"))
            st = ((d.get("result") or {}).get("task") or {}).get("status")
        except Exception:
            st = "ERR"
        c[st] += 1
    return c


def main():
    print("=" * 70)
    print("test_set 解析进度监控 + 命中率自动计算")
    print("=" * 70)

    with open(UPLOAD_RESULTS_PATH, "r", encoding="utf-8") as f:
        up = json.load(f)
    total = len(up)
    print(f"待解析案例总数: {total}")

    start = time.time()
    last_print = 0
    while True:
        elapsed = time.time() - start
        c = get_test_set_status(up)
        successful = c.get("successful", 0)
        pending = c.get("pending", 0)
        running = c.get("running", 0)

        # 每 30 秒或状态变化时打印
        now = time.time()
        if now - last_print >= 30 or successful == total:
            print(
                f"[{int(elapsed)//60:>3d}m{int(elapsed)%60:02d}s] "
                f"successful={successful}/{total}  running={running}  pending={pending}  "
                f"others={ {k:v for k,v in c.items() if k not in ('successful','pending','running')} }"
            )
            last_print = now

        if successful == total:
            print("\n所有 test_set 案例解析完成！开始计算命中率...")
            break

        if elapsed > MAX_WAIT:
            print(f"\n等待超时（{MAX_WAIT//60} 分钟），当前仅 {successful}/{total} 完成，退出。")
            sys.exit(1)

        time.sleep(POLL_INTERVAL)

    # 健康检查
    try:
        url = f"{API_BASE}/health_check"
        with urllib.request.urlopen(url, timeout=10) as r:
            print(f"API 健康检查: {json.loads(r.read().decode('utf-8')).get('status','unknown')}")
    except Exception as e:
        print(f"[ERROR] API 不可达: {e}")
        sys.exit(1)

    # 逐个调用相似案例分析 API（与 calculate_test_set_hitrate.py 逻辑一致）
    results = []
    hit1 = hit3 = hit5 = errors = 0
    for idx, (log_name, info) in enumerate(sorted(up.items()), 1):
        log_file_id = info["log_file_id"]
        rct_en = extract_root_cause_type(log_name)
        gt_cat = BROAD_CATEGORY.get(rct_en, "其他")
        print(f"\n  [{idx}/{total}] {log_name}")
        print(f"    GT: {rct_en} → {gt_cat}")
        try:
            resp = api_post("/similarity_analysis", {"log_file_id": log_file_id, "top_k": 50})
            if resp.get("code") != 200:
                print(f"    [ERROR] API返回错误: {resp.get('message','')}")
                errors += 1
                results.append({"log_name": log_name, "rct_en": rct_en, "gt_cat": gt_cat, "error": resp.get("message","API错误")})
                continue
            top_matches = resp.get("result", {}).get("top_matches", [])
            seen_cats = []
            for m in top_matches:
                cat = m.get("case_category", "")
                if cat and cat not in seen_cats:
                    seen_cats.append(cat)
                if len(seen_cats) >= 5:
                    break
            top1_hit = gt_cat in seen_cats[:1]
            top3_hit = gt_cat in seen_cats[:3]
            top5_hit = gt_cat in seen_cats[:5]
            if top1_hit: hit1 += 1
            if top3_hit: hit3 += 1
            if top5_hit: hit5 += 1
            predicted_cats = " > ".join(seen_cats[:5])
            print(f"    预测Top5大类: {predicted_cats}")
            print(f"    命中: Top1={top1_hit} Top3={top3_hit} Top5={top5_hit}")
            best_type = top_matches[0]["root_cause_type"] if top_matches else ""
            best_cat = top_matches[0].get("case_category","") if top_matches else ""
            best_sim = top_matches[0]["similarity"] if top_matches else 0
            results.append({
                "log_name": log_name, "rct_en": rct_en, "gt_cat": gt_cat,
                "predicted_top1_cat": best_cat, "predicted_top5_cats": seen_cats[:5],
                "top1_hit": top1_hit, "top3_hit": top3_hit, "top5_hit": top5_hit,
                "best_type": best_type, "best_sim": best_sim,
                "top5_types": [m["root_cause_type"] for m in top_matches[:5]],
            })
        except Exception as e:
            print(f"    [ERROR] {e}")
            errors += 1
            results.append({"log_name": log_name, "rct_en": rct_en, "gt_cat": gt_cat, "error": str(e)})
        time.sleep(0.3)

    valid = total - errors
    print(f"\n{'='*70}")
    print("命中率汇总（基于已解析完成的特征）")
    print(f"{'='*70}")
    print(f"  总案例数: {total}")
    print(f"  有效案例: {valid}")
    print(f"  错误案例: {errors}")
    if valid > 0:
        print(f"  Top-1 命中率: {hit1}/{valid} = {hit1/valid*100:.1f}%")
        print(f"  Top-3 命中率: {hit3}/{valid} = {hit3/valid*100:.1f}%")
        print(f"  Top-5 命中率: {hit5}/{valid} = {hit5/valid*100:.1f}%")

    # 按大类分组
    print(f"\n按大类分组命中率:")
    cat_stats = {}
    for r in results:
        if "error" in r: continue
        gt = r["gt_cat"]
        if gt not in cat_stats:
            cat_stats[gt] = {"total":0,"hit1":0,"hit3":0,"hit5":0}
        cat_stats[gt]["total"] += 1
        if r["top1_hit"]: cat_stats[gt]["hit1"] += 1
        if r["top3_hit"]: cat_stats[gt]["hit3"] += 1
        if r["top5_hit"]: cat_stats[gt]["hit5"] += 1
    print(f"  {'大类':<25s} {'总数':>4s} {'Top1':>6s} {'Top3':>6s} {'Top5':>6s}")
    print(f"  {'-'*55}")
    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        print(f"  {cat:<25s} {s['total']:>4d} {s['hit1']}/{s['total']:>3d} {s['hit3']}/{s['total']:>3d} {s['hit5']}/{s['total']:>3d}")

    # 未命中
    missed = [r for r in results if "error" not in r and not r["top5_hit"]]
    if missed:
        print(f"\nTop-5 未命中案例 ({len(missed)} 个):")
        for r in missed:
            print(f"  {r['rct_en']} (GT: {r['gt_cat']}) → 预测: {' > '.join(r['predicted_top5_cats'])}")

    # 保存
    output_path = "/Users/zhaoyujin/Desktop/witty-ub/scripts/test_set_hitrate_results.json"
    output = {
        "total": total, "valid": valid, "errors": errors,
        "top1_hit": hit1, "top3_hit": hit3, "top5_hit": hit5,
        "top1_rate": hit1/valid if valid>0 else 0,
        "top3_rate": hit3/valid if valid>0 else 0,
        "top5_rate": hit5/valid if valid>0 else 0,
        "cat_stats": cat_stats, "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存: {output_path}")


if __name__ == "__main__":
    main()
