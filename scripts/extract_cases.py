#!/usr/bin/env python3
"""从 yxh_new_simplified 知识库批量创建案例

用法:
    cd /Users/zhaoyujin/Desktop/witty-ub
    WITTY_DIR=/Users/zhaoyujin/Desktop/witty-ub/case_data PYTHONPATH=src/plugins:$PYTHONPATH src/plugins/latency/.venv/bin/python3 scripts/extract_cases.py

前提:
    - PostgreSQL 运行中，数据库 witty-ub 已有 yxh_new_simplified 的解析数据
    - 后端环境变量已设置 (PG_HOST 等)

功能:
    - 查找知识库下所有解析成功的 log_file
    - 对每个 log_file 调用 CaseServiceManager.create_case()
      （自动提取根因类型、特征、写 JSON）
    - 跳过已存在的案例
"""

import os
import sys
import asyncio
import traceback
from collections import Counter

# 项目模块
from latency.services.case_service import CaseServiceManager
from latency.database.engine import PGManager

# psycopg2 用于查询成功任务（项目 ORM 无此查询接口）
import psycopg2

# ============================================================
# 配置
# ============================================================

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DATABASE = os.getenv("PG_DATABASE", "witty-ub")
PG_USER = os.getenv("PG_USER", "witty-ub")

PG_PASSWD_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "deploy",
    "pg.passwd",
)

KB_ID = "bea5fe98-9724-4d67-b5d1-4a9c0d7db5f7"
KB_NAME = "yxh_new_simplified"


def read_pg_password() -> str:
    try:
        with open(PG_PASSWD_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"[ERROR] 密码文件不存在: {PG_PASSWD_FILE}")
        sys.exit(1)


def find_successful_log_files(cur) -> list[tuple[str, str]]:
    """查找知识库中解析成功的 log_file，返回 [(log_id, log_name), ...]"""
    cur.execute(
        """
        SELECT DISTINCT lf.id, lf.name
        FROM log_file lf
        JOIN task t ON t.op_id = lf.id AND t.task_type = 'kv_cache_log_parse_worker'
        WHERE lf.kb_id = %s AND t.status = 'successful'
        ORDER BY lf.name
        """,
        (KB_ID,),
    )
    return cur.fetchall()


async def main():
    print("=" * 70)
    print(f"从 {KB_NAME} 知识库批量创建案例")
    print("=" * 70)

    # 1. 连接数据库，查找成功任务
    pg_password = read_pg_password()
    dsn = f"host={PG_HOST} port={PG_PORT} dbname={PG_DATABASE} user={PG_USER} password={pg_password}"
    print(f"连接数据库: {PG_HOST}:{PG_PORT}/{PG_DATABASE}")

    try:
        conn = psycopg2.connect(dsn)
    except Exception as e:
        print(f"[ERROR] 数据库连接失败: {e}")
        sys.exit(1)

    conn.autocommit = True
    cur = conn.cursor()

    log_files = find_successful_log_files(cur)
    print(f"找到 {len(log_files)} 个解析成功的 log_file")

    conn.close()

    if not log_files:
        print("[WARN] 没有找到解析成功的 log_file，退出")
        return

    # 1b. 初始化 PGManager（FeatureExtractionManager 需要）
    from urllib.parse import quote_plus
    async_dsn = (
        f"postgresql+asyncpg://{PG_USER}:{quote_plus(pg_password)}"
        f"@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
    )
    PGManager.initialize(async_dsn)
    print("PGManager 已初始化")

    # 2. 遍历，调用 CaseServiceManager.create_case()
    skipped = 0
    created = 0
    failed = 0
    results = []

    for idx, (log_id, log_name) in enumerate(log_files, 1):
        print(f"\n[{idx}/{len(log_files)}] {log_name}")

        # 跳过已有案例（有特征的才跳过，无特征的会被覆盖）
        existing_id = CaseServiceManager.find_existing_case_by_log_name(log_name)
        if existing_id:
            # 检查是否已有特征
            import json as _json
            _jp = os.path.join(os.getenv("WITTY_DIR", "/var/witty-ub"), "case", f"{existing_id}.json")
            try:
                with open(_jp, "r", encoding="utf-8") as _f:
                    _existing = _json.load(_f)
                if _existing.get("features") is not None:
                    print(f"  [SKIP] 已存在有特征案例: {existing_id}")
                    skipped += 1
                    continue
                else:
                    print(f"  [OVERWRITE] 覆盖无特征案例: {existing_id}")
                    os.remove(_jp)
            except Exception:
                pass

        # 从文件名提取根因类型
        root_cause_type = CaseServiceManager.extract_root_cause_type(log_name)
        print(f"  根因类型: {root_cause_type}")

        try:
            case_record = await CaseServiceManager.create_case(
                kb_id=KB_ID,
                root_cause_type=root_cause_type,
                description=f"自动导入: {root_cause_type}",
                task_names=[log_name],
                log_file_id=log_id,
                log_file_name=log_name,
            )

            fault_cat = case_record.get("fault_category", "unknown")
            print(f"  [OK] 故障类别: {fault_cat}, 案例ID: {case_record['id']}")
            created += 1
            results.append({
                "root_cause_type": root_cause_type,
                "fault_category": fault_cat,
            })

        except Exception as e:
            failed += 1
            print(f"  [ERROR] 创建失败: {e}")
            traceback.print_exc()

    # 3. 汇总
    print("\n" + "=" * 70)
    print("汇总")
    print("=" * 70)
    print(f"  总 log_file 数: {len(log_files)}")
    print(f"  跳过（已有案例）: {skipped}")
    print(f"  新建案例: {created}")
    print(f"  失败: {failed}")

    if results:
        cat_counter = Counter(r["fault_category"] for r in results)
        print(f"\n故障类别分布:")
        for cat, cnt in cat_counter.most_common():
            print(f"  {cat}: {cnt}")

    print(f"\n案例目录: {os.getenv('WITTY_DIR', '/var/witty-ub')}/case")
    print("完成！")

    # 清理
    await PGManager.close()


if __name__ == "__main__":
    asyncio.run(main())
