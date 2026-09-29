_#!/usr/bin/env python3
"""
上传 test_set 到后端并等待解析完成，然后运行评估。
用法: python scripts/upload_test_and_evaluate.py
"""
import os
import sys
import time
import json
import subprocess

API_BASE = "http://127.0.0.1:9772"
BASE_DATA_DIR = "/Users/zhaoyujin/Desktop/yxh_new_data_complete"
TEST_SET_DIR = os.path.join(BASE_DATA_DIR, "test_set")


def run(cmd, desc=""):
    print(f"  {desc}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    STDOUT: {result.stdout[:500]}")
        print(f"    STDERR: {result.stderr[:500]}")
        raise RuntimeError(f"Command failed: {desc}")
    return result.stdout.strip()


def main():
    print("=" * 60)
    print("上传 test_set 并运行评估")
    print("=" * 60)

    # Step 1: 上传 test_set
    print("\n📤 Step 1: 上传 test_set 到后端...")

    # 使用 run_dataset_match.py 的上传逻辑
    # 创建知识库
    kb_id = run(f"""curl -s -X POST "{API_BASE}/log_kb" \
      -H "Content-Type: application/json" \
      -d '{{"name": "test_set", "description": "测试集 - 评估用"}}'""", "创建知识库")

    try:
        kb_data = json.loads(kb_id)
        if kb_data.get("result") and kb_data["result"].get("kb_id"):
            kb_id = kb_data["result"]["kb_id"]
        else:
            # 可能已存在，尝试获取
            list_resp = run(f"""curl -s -X POST "{API_BASE}/log_kb/list" \
              -H "Content-Type: application/json" \
              -d '{{"name": "test_set", "page_cnt": 20, "page_num": 1}}'""", "查找知识库")
            list_data = json.loads(list_resp)
            items = list_data.get("result", {}).get("items", [])
            if items:
                kb_id = items[0]["id"]
            else:
                print(f"    响应: {kb_id}")
                raise RuntimeError("创建知识库失败")
    except Exception as e:
        print(f"    错误: {e}")
        # 尝试另一种方式
        list_resp = run(f"""curl -s -X POST "{API_BASE}/log_kb/list" \
          -H "Content-Type: application/json" \
          -d '{{"name": "test_set", "page_cnt": 20, "page_num": 1}}'""", "查找知识库")
        list_data = json.loads(list_resp)
        items = list_data.get("result", {}).get("items", [])
        if items:
            kb_id = items[0]["id"]
        else:
            raise

    print(f"    知识库 ID: {kb_id}")

    # 遍历 test_set 目录中的所有案例
    all_cases = []
    for source_dir in sorted(os.listdir(TEST_SET_DIR)):
        source_path = os.path.join(TEST_SET_DIR, source_dir)
        if not os.path.isdir(source_path):
            continue
        for case_dir in sorted(os.listdir(source_path)):
            case_path = os.path.join(source_path, case_dir)
            if not os.path.isdir(case_path):
                continue
            all_cases.append((case_dir, case_path))

    print(f"    发现 {len(all_cases)} 个测试案例")

    # 上传每个案例
    uploaded = 0
    for idx, (name, path) in enumerate(all_cases):
        print(f"    [{idx+1}/{len(all_cases)}] {name[:60]}...", end=" ", flush=True)
        try:
            resp = run(f"""curl -s -X POST "{API_BASE}/log_file/{kb_id}" \
              -H "Content-Type: application/json" \
              -d '{{"upload_log_file_configs": [{{"name": "{name}", "source_type": "local", "source": "{path}", "log_type": "KVCache"}}}}'""", f"上传 {name}")
            data = json.loads(resp)
            log_ids = data.get("result", {}).get("log_file_ids", [])
            if not log_ids:
                print("无 ID")
                continue

            # 触发解析
            log_id = log_ids[0]
            run(f"""curl -s -X PUT "{API_BASE}/log_file/run/{log_id}?run=true" \
              -H "Content-Type: application/json" """, "触发解析")
            uploaded += 1
            print("✅")
            time.sleep(0.3)
        except Exception as e:
            print(f"❌ {e}")

    print(f"    已上传 {uploaded}/{len(all_cases)} 个案例")

    # Step 2: 等待解析完成
    print("\n⏳ Step 2: 等待解析完成...")
    start_time = time.time()
    max_wait = 1800  # 30 分钟

    while time.time() - start_time < max_wait:
        # 查询任务状态
        task_resp = run(f"""curl -s -X POST "{API_BASE}/task/list" \
          -H "Content-Type: application/json" \
          -d '{{"kb_id": "{kb_id}", "page_cnt": 100, "page_num": 1}}'""", "查询任务")
        try:
            task_data = json.loads(task_resp)
            tasks = task_data.get("result", {}).get("tasks", [])
            if not tasks:
                print("    未找到任务，等待...")
            else:
                done = sum(1 for t in tasks if t.get("status") == "done")
                total = len(tasks)
                failed = sum(1 for t in tasks if t.get("status") == "failed")
                print(f"    进度: {done}/{total} 完成, {failed} 失败")
                if done + failed >= total:
                    print("    ✅ 所有解析任务完成！")
                    break
        except Exception as e:
            print(f"    查询异常: {e}")

        time.sleep(10)
    else:
        print("    ⚠️ 等待超时，但继续执行评估")

    # Step 3: 运行评估
    print("\n🔬 Step 3: 运行评估...")
    os.environ["TEST_KB_ID"] = kb_id
    script_dir = os.path.dirname(os.path.abspath(__file__))
    eval_script = os.path.join(script_dir, "run_evaluation_and_report.py")

    # 直接运行评估脚本
    eval_cmd = f"""cd /Users/zhaoyujin/Desktop/witty-ub && \
      BACKEND_URL="{API_BASE}" \
      TEST_SET_KB_NAME="test_set" \
      python3 {eval_script}"""
    print(f"    运行评估脚本...")
    subprocess.run(eval_cmd, shell=True, check=True)

    print("\n" + "=" * 60)
    print("全部完成！")
    print("报告位置: /Users/zhaoyujin/Desktop/witty-ub/evaluation_report.html")
    print("=" * 60)


if __name__ == "__main__":
    main()