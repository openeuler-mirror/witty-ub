"""临时诊断脚本：查 log_knowledge 最新资产 + pod_role 填充情况。"""
import asyncio

import asyncpg


DSN = "postgresql://witty-ub:YqnUqVgU1u68IlNVV0HgifWp@127.0.0.1:15432/witty-ub"


async def main():
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(
            "SELECT id, name, log_id, created_at FROM log_knowledge ORDER BY created_at DESC LIMIT 5"
        )
        print("=== log_knowledge latest 5 ===")
        for r in rows:
            print(dict(r))

        print("\n=== pod_role count ===")
        r = await conn.fetchrow("SELECT COUNT(*) AS n FROM pod_role")
        print(dict(r))

        rows = await conn.fetch(
            "SELECT trace_id, client_pod, entry_worker_pods, meta_worker_pods, data_worker_pods "
            "FROM pod_role LIMIT 3"
        )
        print("\n=== pod_role sample ===")
        for r in rows:
            print(dict(r))

        # 333 log 的 trace 有多少有 pod_role
        if rows:
            r = await conn.fetchrow(
                "SELECT COUNT(DISTINCT pr.trace_id) AS n FROM pod_role pr "
                "JOIN log_parse_result lpr ON lpr.trace_id = pr.trace_id "
                "WHERE lpr.log_id = $1", "0709ccce-c047-4283-b1ef-59f8aae39def"
            )
            print("\n=== 333 log traces with pod_role ===", dict(r))
    finally:
        await conn.close()


asyncio.run(main())
