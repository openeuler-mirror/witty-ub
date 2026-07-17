import os
import time
import json

from latency.schemas.log import (
    C2WLogParseResultDataclass,
    LogParseResultDataclass,
    LogParseResultModel,
    SparseLogParseResultDataclass,
)
from latency.schemas.request import ListLogParseResultRequest, ListTracesByHostRequest, GetLatencyMetricsRequest
from latency.database.engine import AsyncSQLiteSingleton


LogParseResultStorage = (
    LogParseResultDataclass
    | C2WLogParseResultDataclass
    | SparseLogParseResultDataclass
)


def _log_parse_result_to_db_tuple(result: LogParseResultStorage) -> tuple:
    """按 INSERT 列顺序生成 SQLite 参数，跳过 Pydantic 中间对象。"""
    return (
        result.id,
        result.log_id,
        result.aggregated_event_id,
        result.anomalous_event_id,
        result.trace_id,
        result.timestamp,
        result.src_ip,
        result.dst_ip,
        json.dumps(result.pod_ips) if result.pod_ips else None,
        result.cluster_name,
        result.host,
        result.total_latency,
        result.c2w_latency,
        result.worker_query_meta_latency,
        result.urma_total_latency,
        result.urma_link_latency,
        result.urma_inflight_count,
        result.c2w_urma_latency,
        result.w2w_urma_latency,
        result.operation,
        result.data_size,
        result.offset,
        result.is_anomalous,
        result.content,
        result.anomaly_reason,
        result.anomaly_score,
        result.remark,
        result.existed_status,
        result.created_at,
        result.sdk_process,
        result.sdk_rpc,
        result.local_worker_cost,
        result.local_worker_lock,
        result.remote_worker_cost,
        result.remote_worker_rpc,
        result.master_process,
        result.master_rpc_total,
    )


def _can_use_sparse_insert(result: LogParseResultStorage) -> bool:
    """省略值为 NULL 的 Worker/诊断字段，保证落库结果与完整 INSERT 一致。"""
    return (
        result.c2w_latency is None
        and result.worker_query_meta_latency is None
        and result.urma_total_latency is None
        and result.urma_link_latency is None
        and result.urma_inflight_count is None
        and result.w2w_urma_latency is None
        and result.src_ip is None
        and result.dst_ip is None
        and result.host is None
        and result.offset is None
        and result.content is None
        and result.anomaly_score is None
        and result.sdk_process is None
        and result.sdk_rpc is None
        and result.local_worker_cost is None
        and result.local_worker_lock is None
        and result.remote_worker_cost is None
        and result.remote_worker_rpc is None
        and result.master_process is None
        and result.master_rpc_total is None
    )


def _can_use_c2w_insert(result: LogParseResultStorage) -> bool:
    """省略普通 SDK→Worker 匹配结果中恒为 NULL 的端点/诊断字段。"""
    return (
        result.c2w_latency is not None
        and result.worker_query_meta_latency is None
        and result.urma_total_latency is None
        and result.urma_link_latency is None
        and result.urma_inflight_count is None
        and result.c2w_urma_latency is None
        and result.w2w_urma_latency is None
        and result.src_ip is None
        and result.dst_ip is None
        and result.host is None
        and result.offset is None
        and result.content is None
        and result.anomaly_score is None
        and result.sdk_process is None
        and result.sdk_rpc is None
        and result.local_worker_cost is None
        and result.local_worker_lock is None
        and result.remote_worker_cost is None
        and result.remote_worker_rpc is None
        and result.master_process is None
        and result.master_rpc_total is None
    )


def _log_parse_result_to_c2w_db_tuple(
    result: LogParseResultStorage,
) -> tuple:
    """生成只有 SDK→Worker c2w_latency 的精简 SQLite 参数。"""
    return (
        result.id,
        result.log_id,
        result.aggregated_event_id,
        result.anomalous_event_id,
        result.trace_id,
        result.timestamp,
        json.dumps(result.pod_ips) if result.pod_ips else None,
        result.cluster_name,
        result.total_latency,
        result.c2w_latency,
        result.operation,
        result.data_size,
        result.is_anomalous,
        result.anomaly_reason,
        result.remark,
        result.existed_status,
        result.created_at,
    )


def _log_parse_result_to_sparse_db_tuple(
    result: LogParseResultStorage,
) -> tuple:
    """生成常见无 Worker 结果的精简 SQLite 参数。"""
    return (
        result.id,
        result.log_id,
        result.aggregated_event_id,
        result.anomalous_event_id,
        result.trace_id,
        result.timestamp,
        json.dumps(result.pod_ips) if result.pod_ips else None,
        result.cluster_name,
        result.total_latency,
        result.c2w_urma_latency,
        result.operation,
        result.data_size,
        result.is_anomalous,
        result.anomaly_reason,
        result.remark,
        result.existed_status,
        result.created_at,
    )


def _can_use_minimal_insert(result: LogParseResultStorage) -> bool:
    """判断稀疏结果的非必填字段是否也等于数据库默认值。"""
    return (
        not result.aggregated_event_id
        and not result.anomalous_event_id
        and result.c2w_urma_latency is None
        and result.anomaly_reason is None
    )


def _log_parse_result_to_minimal_db_tuple(
    result: LogParseResultStorage,
) -> tuple:
    return (
        result.id,
        result.log_id,
        result.trace_id,
        result.timestamp,
        json.dumps(result.pod_ips) if result.pod_ips else None,
        result.cluster_name,
        result.total_latency,
        result.operation,
        result.data_size,
        result.is_anomalous,
        result.remark,
        result.existed_status,
        result.created_at,
    )


class LogParseResultManager:
    """日志解析结果管理器"""

    last_store_metrics: dict[str, object] = {}
    profile_explicit_wal_checkpoint = False

    @staticmethod
    async def add_log_parse_result(result: LogParseResultModel) -> bool:
        """添加日志解析结果"""
        sql_str = """
            INSERT INTO log_parse_result_table (
                id, log_id, aggregated_event_id, anomalous_event_id, trace_id,
                timestamp, src_ip, dst_ip, pod_ips, cluster_name, host,
                total_latency, c2w_latency, worker_query_meta_latency,
                urma_total_latency, urma_link_latency, urma_inflight_count,
                c2w_urma_latency, w2w_urma_latency, operation, data_size,
                offset, is_anomalous, content, anomaly_reason, anomaly_score,
                remark, existed_status, created_at,
                sdk_process, sdk_rpc, local_worker_cost, local_worker_lock,
                remote_worker_cost, remote_worker_rpc, master_process, master_rpc_total
            ) VALUES (
                :id, :log_id, :aggregated_event_id, :anomalous_event_id, :trace_id,
                :timestamp, :src_ip, :dst_ip, :pod_ips, :cluster_name, :host,
                :total_latency, :c2w_latency, :worker_query_meta_latency,
                :urma_total_latency, :urma_link_latency, :urma_inflight_count,
                :c2w_urma_latency, :w2w_urma_latency, :operation, :data_size,
                :offset, :is_anomalous, :content, :anomaly_reason, :anomaly_score,
                :remark, :existed_status, :created_at,
                :sdk_process, :sdk_rpc, :local_worker_cost, :local_worker_lock,
                :remote_worker_cost, :remote_worker_rpc, :master_process, :master_rpc_total
            )
        """
        data = result.model_dump(exclude_none=False, by_alias=True)
        if data.get("pod_ips"):
            data["pod_ips"] = json.dumps(data["pod_ips"])
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, data)
        return success

    @staticmethod
    async def add_log_parse_results(
        results: list[LogParseResultStorage],
        batch_size: int = 50000,
    ) -> bool:
        """将 dataclass 分批写入 SQLite，不创建 Pydantic/字典副本。"""
        import asyncio
        import logging
        
        logger = logging.getLogger(__name__)

        LogParseResultManager.last_store_metrics = {}
        if not results:
            return True

        total_count = len(results)
        db = AsyncSQLiteSingleton()
        id_prefix = os.urandom(10).hex()
        profile_checkpoint = LogParseResultManager.profile_explicit_wal_checkpoint
        
        # 全局协程锁，保证同一时间只有一组操作操作sqlite连接
        async with db._async_lock:
            def sync_batch_insert():
                """同步函数：全部sqlite操作放到同一个子线程，线程安全"""
                db.ensure_initialized()
                conn = db._write_conn
                sync_started = time.perf_counter()
                original_wal_autocheckpoint = None
                metrics: dict[str, object] = {
                    "rows": total_count,
                    "batch_size": batch_size,
                    "batch_count": (total_count + batch_size - 1) // batch_size,
                    "minimal_rows": 0,
                    "c2w_rows": 0,
                    "sparse_rows": 0,
                    "full_rows": 0,
                    "setup_seconds": 0.0,
                    "parameter_build_seconds": 0.0,
                    "minimal_insert_seconds": 0.0,
                    "c2w_insert_seconds": 0.0,
                    "sparse_insert_seconds": 0.0,
                    "full_insert_seconds": 0.0,
                    "commit_seconds": 0.0,
                    "checkpoint_seconds": 0.0,
                    "explicit_checkpoint": profile_checkpoint,
                    "commit_includes_auto_checkpoint": not profile_checkpoint,
                }
                success = False
                try:
                    setup_started = time.perf_counter()
                    if profile_checkpoint:
                        original_wal_autocheckpoint = conn.execute(
                            "PRAGMA wal_autocheckpoint;"
                        ).fetchone()[0]
                        conn.execute("PRAGMA wal_autocheckpoint = 0;")

                    # 写入性能调优（事务内生效，不影响其他连接）
                    conn.execute("PRAGMA journal_mode = WAL;")
                    conn.execute("PRAGMA synchronous = NORMAL;")
                    conn.execute("PRAGMA cache_size = -65536;")  # 64MB缓存
                    conn.execute("PRAGMA temp_store = MEMORY;")
                    conn.execute("PRAGMA foreign_keys = OFF;")
                    
                    # 开启统一事务
                    conn.execute("BEGIN IMMEDIATE;")
                    metrics["setup_seconds"] = (
                        time.perf_counter() - setup_started
                    )
                    
                    sql_str = """
                        INSERT INTO log_parse_result_table (
                            id, log_id, aggregated_event_id, anomalous_event_id, trace_id,
                            timestamp, src_ip, dst_ip, pod_ips, cluster_name, host,
                            total_latency, c2w_latency, worker_query_meta_latency,
                            urma_total_latency, urma_link_latency, urma_inflight_count,
                            c2w_urma_latency, w2w_urma_latency, operation, data_size,
                            offset, is_anomalous, content, anomaly_reason, anomaly_score,
                            remark, existed_status, created_at,
                            sdk_process, sdk_rpc, local_worker_cost, local_worker_lock,
                            remote_worker_cost, remote_worker_rpc, master_process, master_rpc_total
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    """
                    sparse_sql_str = """
                        INSERT INTO log_parse_result_table (
                            id, log_id, aggregated_event_id, anomalous_event_id,
                            trace_id, timestamp, pod_ips, cluster_name,
                            total_latency, c2w_urma_latency, operation, data_size,
                            is_anomalous, anomaly_reason, remark, existed_status,
                            created_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    """
                    c2w_sql_str = """
                        INSERT INTO log_parse_result_table (
                            id, log_id, aggregated_event_id, anomalous_event_id,
                            trace_id, timestamp, pod_ips, cluster_name,
                            total_latency, c2w_latency, operation, data_size,
                            is_anomalous, anomaly_reason, remark, existed_status,
                            created_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    """
                    minimal_sql_str = """
                        INSERT INTO log_parse_result_table (
                            id, log_id, trace_id, timestamp, pod_ips,
                            cluster_name, total_latency, operation, data_size,
                            is_anomalous, remark, existed_status, created_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    """

                    # 每批只保留参数tuple；常见的无Worker结果不绑定恒为NULL的列。
                    for i in range(0, total_count, batch_size):
                        end = min(i + batch_size, total_count)
                        minimal_batch = []
                        c2w_batch = []
                        sparse_batch = []
                        full_batch = []
                        parameter_started = time.perf_counter()
                        for index in range(i, end):
                            result = results[index]
                            if not result.id:
                                # 80-bit随机前缀保证批次唯一，48-bit递增后缀
                                # 让SQLite主键索引按顺序写入，避免UUID随机写放大。
                                result.id = id_prefix + f"{index:012x}"
                            if type(result) is SparseLogParseResultDataclass:
                                # 解析主路径已经用紧凑类型证明所有 Worker 字段
                                # 均为 NULL，直接分类和构造参数，避免千万次通用
                                # 稀疏判定以及多层 Python 函数调用。
                                if (
                                    not result.aggregated_event_id
                                    and not result.anomalous_event_id
                                    and result.c2w_urma_latency is None
                                    and result.anomaly_reason is None
                                ):
                                    minimal_batch.append(
                                        (
                                            result.id,
                                            result.log_id,
                                            result.trace_id,
                                            result.timestamp,
                                            json.dumps(result.pod_ips) if result.pod_ips else None,
                                            result.cluster_name,
                                            result.total_latency,
                                            result.operation,
                                            result.data_size,
                                            result.is_anomalous,
                                            result.remark,
                                            result.existed_status,
                                            result.created_at,
                                        )
                                    )
                                else:
                                    sparse_batch.append(
                                        (
                                            result.id,
                                            result.log_id,
                                            result.aggregated_event_id,
                                            result.anomalous_event_id,
                                            result.trace_id,
                                            result.timestamp,
                                            json.dumps(result.pod_ips) if result.pod_ips else None,
                                            result.cluster_name,
                                            result.total_latency,
                                            result.c2w_urma_latency,
                                            result.operation,
                                            result.data_size,
                                            result.is_anomalous,
                                            result.anomaly_reason,
                                            result.remark,
                                            result.existed_status,
                                            result.created_at,
                                        )
                                    )
                            elif type(result) is C2WLogParseResultDataclass:
                                c2w_batch.append(
                                    (
                                        result.id,
                                        result.log_id,
                                        result.aggregated_event_id,
                                        result.anomalous_event_id,
                                        result.trace_id,
                                        result.timestamp,
                                        json.dumps(result.pod_ips) if result.pod_ips else None,
                                        result.cluster_name,
                                        result.total_latency,
                                        result.c2w_latency,
                                        result.operation,
                                        result.data_size,
                                        result.is_anomalous,
                                        result.anomaly_reason,
                                        result.remark,
                                        result.existed_status,
                                        result.created_at,
                                    )
                                )
                            elif _can_use_c2w_insert(result):
                                c2w_batch.append(
                                    _log_parse_result_to_c2w_db_tuple(result)
                                )
                            elif _can_use_sparse_insert(result):
                                if _can_use_minimal_insert(result):
                                    minimal_batch.append(
                                        _log_parse_result_to_minimal_db_tuple(result)
                                    )
                                else:
                                    sparse_batch.append(
                                        _log_parse_result_to_sparse_db_tuple(result)
                                    )
                            else:
                                full_batch.append(_log_parse_result_to_db_tuple(result))
                        metrics["parameter_build_seconds"] += (
                            time.perf_counter() - parameter_started
                        )
                        metrics["minimal_rows"] += len(minimal_batch)
                        metrics["c2w_rows"] += len(c2w_batch)
                        metrics["sparse_rows"] += len(sparse_batch)
                        metrics["full_rows"] += len(full_batch)

                        if minimal_batch:
                            insert_started = time.perf_counter()
                            conn.executemany(minimal_sql_str, minimal_batch)
                            metrics["minimal_insert_seconds"] += (
                                time.perf_counter() - insert_started
                            )
                        if c2w_batch:
                            insert_started = time.perf_counter()
                            conn.executemany(c2w_sql_str, c2w_batch)
                            metrics["c2w_insert_seconds"] += (
                                time.perf_counter() - insert_started
                            )
                        if sparse_batch:
                            insert_started = time.perf_counter()
                            conn.executemany(sparse_sql_str, sparse_batch)
                            metrics["sparse_insert_seconds"] += (
                                time.perf_counter() - insert_started
                            )
                        if full_batch:
                            insert_started = time.perf_counter()
                            conn.executemany(sql_str, full_batch)
                            metrics["full_insert_seconds"] += (
                                time.perf_counter() - insert_started
                            )
                    
                    # 一次性提交
                    commit_started = time.perf_counter()
                    conn.commit()
                    metrics["commit_seconds"] = (
                        time.perf_counter() - commit_started
                    )
                    success = True

                    if profile_checkpoint:
                        try:
                            checkpoint_started = time.perf_counter()
                            checkpoint_result = conn.execute(
                                "PRAGMA wal_checkpoint(PASSIVE);"
                            ).fetchone()
                            metrics["checkpoint_seconds"] = (
                                time.perf_counter() - checkpoint_started
                            )
                            if checkpoint_result:
                                metrics["checkpoint_busy"] = checkpoint_result[0]
                                metrics["checkpoint_log_frames"] = checkpoint_result[1]
                                metrics["checkpointed_frames"] = checkpoint_result[2]
                        except Exception as checkpoint_error:
                            metrics["checkpoint_error"] = str(checkpoint_error)
                            logger.warning(
                                "[Store] WAL checkpoint计时失败: %s",
                                checkpoint_error,
                            )
                except Exception as e:
                    conn.rollback()
                    metrics["error"] = str(e)
                    logger.error(f"[Store] 插入失败，事务回滚: {str(e)}")
                finally:
                    if original_wal_autocheckpoint is not None:
                        try:
                            conn.execute(
                                f"PRAGMA wal_autocheckpoint = "
                                f"{original_wal_autocheckpoint};"
                            )
                        except Exception as restore_error:
                            metrics["wal_autocheckpoint_restore_error"] = str(
                                restore_error
                            )
                    metrics["total_sync_seconds"] = (
                        time.perf_counter() - sync_started
                    )
                    db_path = getattr(db, "DB_PATH", "")
                    wal_path = f"{db_path}-wal" if db_path else ""
                    metrics["wal_size_bytes"] = (
                        os.path.getsize(wal_path)
                        if wal_path and os.path.exists(wal_path)
                        else 0
                    )
                    metrics["success"] = success
                    LogParseResultManager.last_store_metrics = metrics

                if success:
                    logger.info(
                        "[Store] 单事务插入成功，共 %s 条记录，明细=%s",
                        f"{total_count:,}",
                        metrics,
                    )
                return success
            
            # 所有sqlite操作全部在同一个线程执行，避免多线程争抢conn
            success = await asyncio.to_thread(sync_batch_insert)
            return success

    @staticmethod
    async def delete_log_parse_results_by_log_id(log_id: str) -> bool:
        """根据日志ID删除解析结果"""
        sql_str = """
            UPDATE log_parse_result_table
            SET existed_status = 0
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def update_log_parse_results_existed_status_by_log_id(
        log_id: str, existed_status: int
    ) -> bool:
        """根据日志ID更新解析结果的existed_status"""
        sql_str = """
            UPDATE log_parse_result_table
            SET existed_status = :existed_status
            WHERE log_id = :log_id
        """
        params = {"log_id": log_id, "existed_status": existed_status}
        success, _ = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return success

    @staticmethod
    async def list_anomalous_trace_ids_by_log_id(log_id: str) -> set[str]:
        """查询指定日志中所有异常解析结果的 trace_id。"""
        sql_str = """
            SELECT DISTINCT trace_id
            FROM log_parse_result_table
            WHERE log_id = :log_id
              AND existed_status = 1
              AND is_anomalous = 1
              AND trace_id IS NOT NULL
              AND trace_id != ''
        """
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, {"log_id": log_id})
        return {row["trace_id"].strip() for row in rows if row["trace_id"].strip()}

    @staticmethod
    async def list_log_parse_results(
        req: ListLogParseResultRequest,
    ) -> tuple[int, list[LogParseResultModel]]:
        """分页查询日志解析结果"""
        sql_str = """
            SELECT lpr.id, lpr.log_id, lpr.aggregated_event_id, lpr.anomalous_event_id, lpr.trace_id,
                lpr.timestamp, lpr.src_ip, lpr.dst_ip, lpr.pod_ips, lpr.cluster_name, lpr.host,
                lpr.total_latency, lpr.c2w_latency, lpr.worker_query_meta_latency,
                lpr.urma_total_latency, lpr.urma_link_latency, lpr.urma_inflight_count,
                lpr.c2w_urma_latency, lpr.w2w_urma_latency, lpr.operation, lpr.data_size,
                lpr.offset, lpr.is_anomalous, lpr.content, lpr.anomaly_reason, lpr.anomaly_score,
                lpr.remark, lpr.existed_status, lpr.created_at,
                lpr.sdk_process, lpr.sdk_rpc, lpr.local_worker_cost, lpr.local_worker_lock,
                lpr.remote_worker_cost, lpr.remote_worker_rpc, lpr.master_process, lpr.master_rpc_total
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE lpr.existed_status = 1
        """
        params = {}
        if req.kb_id:
            sql_str += " AND lf.kb_id = :kb_id"
            params["kb_id"] = req.kb_id
        if req.log_id:
            sql_str += " AND lpr.log_id = :log_id"
            params["log_id"] = req.log_id
        if req.aggregated_event_id:
            sql_str += " AND lpr.aggregated_event_id = :aggregated_event_id"
            params["aggregated_event_id"] = req.aggregated_event_id
        if req.trace_id:
            sql_str += " AND lpr.trace_id = :trace_id"
            params["trace_id"] = req.trace_id
        if req.trace_ids:
            placeholders = ', '.join([f':trace_id_{i}' for i in range(len(req.trace_ids))])
            sql_str += f" AND lpr.trace_id IN ({placeholders})"
            for i, trace_id in enumerate(req.trace_ids):
                params[f'trace_id_{i}'] = trace_id
        if req.src_ip is not None:
            if req.src_ip == "":
                sql_str += " AND (lpr.src_ip IS NULL OR lpr.src_ip = '')"
            else:
                sql_str += " AND lpr.src_ip LIKE :src_ip"
                params["src_ip"] = f"%{req.src_ip}%"
        if req.dst_ip is not None:
            if req.dst_ip == "":
                sql_str += " AND (lpr.dst_ip IS NULL OR lpr.dst_ip = '')"
            else:
                sql_str += " AND lpr.dst_ip LIKE :dst_ip"
                params["dst_ip"] = f"%{req.dst_ip}%"
        if req.pod_ip:
            sql_str += """
                AND lpr.id IN (
                    SELECT pod_map.log_parse_result_id
                    FROM log_parse_result_pod_ip_table AS pod_map
                    WHERE pod_map.pod_ip = :pod_ip
                )
            """
            params["pod_ip"] = req.pod_ip
        if req.host:
            sql_str += " AND lpr.host = :host"
            params["host"] = req.host
        if req.cluster_name:
            sql_str += " AND lpr.cluster_name = :cluster_name"
            params["cluster_name"] = req.cluster_name
        if req.is_anomalous is not None:
            sql_str += " AND lpr.is_anomalous = :is_anomalous"
            params["is_anomalous"] = req.is_anomalous
        if req.created_at_start:
            sql_str += " AND lpr.created_at >= :created_at_start"
            params["created_at_start"] = req.created_at_start
        if req.created_at_end:
            sql_str += " AND lpr.created_at <= :created_at_end"
            params["created_at_end"] = req.created_at_end
        if req.start_time:
            sql_str += " AND lpr.timestamp >= :start_time"
            params["start_time"] = req.start_time
        if req.end_time:
            sql_str += " AND lpr.timestamp <= :end_time"
            params["end_time"] = req.end_time

        count_sql = f"SELECT COUNT(*) as cnt FROM ({sql_str})"
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0

        sort_field_mapping = {
            "total_latency": "lpr.total_latency",
            "timestamp": "lpr.timestamp",
            "trace_id": "lpr.trace_id",
            "pod_ips": "lpr.pod_ips",
            "cluster_name": "lpr.cluster_name",
            "host": "lpr.host",
            "query_meta_latency": "lpr.worker_query_meta_latency",
            "urma_total_latency": "lpr.urma_total_latency",
            "urma_link_latency": "lpr.urma_link_latency",
            "worker_query_meta_latency": "lpr.worker_query_meta_latency",
            "c2w_urma_latency": "lpr.c2w_urma_latency",
            "w2w_urma_latency": "lpr.w2w_urma_latency",
            "created_at": "lpr.created_at",
        }
        
        if req.sort_fields and len(req.sort_fields) > 0:
            sort_clauses = []
            for sort_field in req.sort_fields:
                field_name = sort_field.field
                if field_name in sort_field_mapping:
                    order = "DESC" if sort_field.order == "desc" else "ASC"
                    sort_clauses.append(f"{sort_field_mapping[field_name]} {order}")
            # 如果有有效的排序字段，使用它们；否则使用默认排序
            if sort_clauses:
                sql_str += " ORDER BY " + ", ".join(sort_clauses)
            else:
                sql_str += " ORDER BY lpr.total_latency DESC"
        else:
            sql_str += " ORDER BY lpr.total_latency DESC"
        
        offset = (req.page_num - 1) * req.page_cnt
        sql_str += " LIMIT :limit OFFSET :offset"
        params["limit"] = req.page_cnt
        params["offset"] = offset

        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        results = []
        for row in rows:
            row_dict = dict(row)
            pod_ips_str = row_dict.get("pod_ips")
            if pod_ips_str:
                try:
                    row_dict["pod_ips"] = json.loads(pod_ips_str)
                except (json.JSONDecodeError, TypeError):
                    row_dict["pod_ips"] = None
            results.append(LogParseResultModel(**row_dict))
        return total, results

    @staticmethod
    async def get_log_parse_result_by_id(result_id: str) -> LogParseResultModel | None:
        """根据ID获取日志解析结果"""
        sql_str = """
            SELECT id, log_id, aggregated_event_id, anomalous_event_id, trace_id,
                timestamp, src_ip, dst_ip, pod_ips, cluster_name, host,
                total_latency, c2w_latency, worker_query_meta_latency,
                urma_total_latency, urma_link_latency, urma_inflight_count,
                c2w_urma_latency, w2w_urma_latency, operation, data_size,
                offset, is_anomalous, content, anomaly_reason, anomaly_score,
                remark, existed_status, created_at,
                sdk_process, sdk_rpc, local_worker_cost, local_worker_lock,
                remote_worker_cost, remote_worker_rpc, master_process, master_rpc_total
            FROM log_parse_result_table
            WHERE id = :result_id
        """
        params = {"result_id": result_id}
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        if rows:
            row = dict(rows[0])
            pod_ips_str = row.get("pod_ips")
            if pod_ips_str:
                try:
                    row["pod_ips"] = json.loads(pod_ips_str)
                except (json.JSONDecodeError, TypeError):
                    row["pod_ips"] = None
            return LogParseResultModel(**row)
        return None

    @staticmethod
    async def list_traces_by_host(
        req: ListTracesByHostRequest,
    ) -> tuple[int, list[dict]]:
        """根据主机获取trace列表"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"list_traces_by_host called with is_anomalous={req.is_anomalous}")
        
        sql_str = """
            SELECT 
                lpr.id,
                lpr.trace_id,
                lpr.pod_ips,
                lpr.cluster_name,
                lpr.host,
                lpr.timestamp as time,
                lpr.operation,
                lpr.total_latency,
                lpr.urma_total_latency,
                lpr.c2w_latency,
                lpr.worker_query_meta_latency,
                lpr.w2w_urma_latency,
                lpr.is_anomalous,
                lpr.anomaly_reason,
                lpr.c2w_latency as req_delay_ms,
                (lpr.total_latency - lpr.c2w_latency) as rsp_delay_ms,
                lpr.total_latency as sdk_ms,
                lpr.pod_ips as pod_id
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE lpr.existed_status = 1 AND lpr.pod_ips LIKE :host_pattern
        """
        params = {"host_pattern": f"%{req.host}%"}
        
        if req.kb_id:
            sql_str += " AND lf.kb_id = :kb_id"
            params["kb_id"] = req.kb_id
        if req.start_time:
            sql_str += " AND lpr.timestamp >= :start_time"
            params["start_time"] = req.start_time
        if req.end_time:
            sql_str += " AND lpr.timestamp <= :end_time"
            params["end_time"] = req.end_time
        if req.operation:
            sql_str += " AND lpr.operation LIKE :operation"
            params["operation"] = f"%{req.operation}%"
        if req.is_anomalous is not None:
            logger.info(f"Adding is_anomalous filter: {req.is_anomalous}")
            sql_str += " AND lpr.is_anomalous = :is_anomalous"
            params["is_anomalous"] = 1 if req.is_anomalous else 0
        
        logger.info(f"Final SQL params: {params}")
        
        count_sql = f"SELECT COUNT(*) as cnt FROM ({sql_str})"
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0
        
        valid_sort_fields = ["timestamp", "total_latency", "c2w_latency"]
        sort_by = req.sort_by if req.sort_by in valid_sort_fields else "timestamp"
        sort_order = "DESC" if req.sort_order.lower() == "desc" else "ASC"
        sql_str += f" ORDER BY {sort_by} {sort_order}"
        
        offset = (req.page_num - 1) * req.page_cnt
        sql_str += " LIMIT :limit OFFSET :offset"
        params["limit"] = req.page_cnt
        params["offset"] = offset
        
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        logger.info(f"Returned {len(rows)} rows")
        
        for row in rows:
            pod_ips_str = row.get("pod_ips")
            if pod_ips_str:
                try:
                    row["pod_ips"] = json.loads(pod_ips_str)
                except (json.JSONDecodeError, TypeError):
                    row["pod_ips"] = None
        
        return total, rows

    @staticmethod
    async def get_latency_metrics(
        req: GetLatencyMetricsRequest,
    ) -> tuple[int, list[dict]]:
        """获取延迟指标时间曲线数据（从预聚合表查询）"""
        where_clauses = ["existed_status = 1"]
        params = {}
        cte_sql = ""

        if req.kb_id:
            where_clauses.append("kb_id = :kb_id")
            params["kb_id"] = req.kb_id
        if req.cluster_name or req.host or req.pod_ip:
            original_filters = []
            if req.cluster_name:
                original_filters.append("lpr.cluster_name = :cluster_name")
                params["cluster_name"] = req.cluster_name
            if req.host:
                original_filters.append("lpr.host = :host")
                params["host"] = req.host
            if req.pod_ip:
                original_filters.append("""
                    lpr.id IN (
                        SELECT pod_map.log_parse_result_id
                        FROM log_parse_result_pod_ip_table AS pod_map
                        WHERE pod_map.pod_ip = :pod_ip
                    )
                """)
                params["pod_ip"] = req.pod_ip
            matched_window_scope = []
            if req.kb_id:
                matched_window_scope.append("twa.kb_id = :kb_id")
            if req.start_time:
                matched_window_scope.append("twa.time_bucket >= :start_time")
            if req.end_time:
                matched_window_scope.append("twa.time_bucket <= :end_time")
            matched_window_scope_sql = ""
            if matched_window_scope:
                matched_window_scope_sql = (
                    " AND " + " AND ".join(matched_window_scope)
                )
            cte_sql = """
                WITH matched_time_windows AS MATERIALIZED (
                    SELECT DISTINCT twa.id
                    FROM log_parse_result_table AS lpr
                    INNER JOIN time_window_aggregated_table AS twa
                        ON twa.log_id = lpr.log_id
                       AND twa.time_bucket = substr(lpr.timestamp, 1, 19)
                       AND COALESCE(twa.src_ip, '') = COALESCE(lpr.src_ip, '')
                       AND COALESCE(twa.dst_ip, '') = COALESCE(lpr.dst_ip, '')
                    WHERE lpr.existed_status = 1
                      AND twa.existed_status = 1
                      AND {}
                      {}
                )
            """.format(
                " AND ".join(original_filters),
                matched_window_scope_sql,
            )
            where_clauses.append("id IN (SELECT id FROM matched_time_windows)")
        if req.src_ip is not None:
            if req.src_ip == "":
                where_clauses.append("(src_ip IS NULL OR src_ip = '')")
            else:
                where_clauses.append("src_ip LIKE :src_ip")
                params["src_ip"] = f"%{req.src_ip}%"
        if req.dst_ip is not None:
            if req.dst_ip == "":
                where_clauses.append("(dst_ip IS NULL OR dst_ip = '')")
            else:
                where_clauses.append("dst_ip LIKE :dst_ip")
                params["dst_ip"] = f"%{req.dst_ip}%"
        if req.start_time:
            where_clauses.append("time_bucket >= :start_time")
            params["start_time"] = req.start_time
        if req.end_time:
            where_clauses.append("time_bucket <= :end_time")
            params["end_time"] = req.end_time

        where_sql = " AND ".join(where_clauses)

        count_sql = cte_sql + f"""
            SELECT COUNT(*) as cnt 
            FROM time_window_aggregated_table
            WHERE {where_sql}
        """
        count_rows = await AsyncSQLiteSingleton().execute_query(count_sql, params)
        total = count_rows[0]["cnt"] if count_rows else 0

        if total == 0:
            return 0, []

        sample_field_map = {
            "avg": "ave_",
            "min": "min_",
            "max": "max_",
            "p95": "p95_",
            "p99": "p99_",
            "p9999": "p9999_",
        }
        sample_prefix = sample_field_map.get(req.sample_mode, "p99_")

        sql_str = cte_sql + f"""
            SELECT 
                time_bucket as time,
                {sample_prefix}total_latency as total_latency,
                {sample_prefix}urma_total_latency as urma_total_latency,
                {sample_prefix}query_meta_latency as worker_query_meta_latency,
                {sample_prefix}sdk_process as sdk_process,
                {sample_prefix}sdk_rpc as sdk_rpc,
                {sample_prefix}local_worker_cost as local_worker_cost,
                {sample_prefix}local_worker_lock as local_worker_lock,
                {sample_prefix}remote_worker_cost as remote_worker_cost,
                {sample_prefix}remote_worker_rpc as remote_worker_rpc,
                {sample_prefix}master_process as master_process,
                {sample_prefix}master_rpc_total as master_rpc_total
            FROM time_window_aggregated_table
            WHERE {where_sql}
            ORDER BY time_bucket ASC
        """
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return total, rows

    @staticmethod
    async def get_cluster_list(kb_id: str | None = None) -> list[str]:
        """获取所有非空的集群名称列表"""
        sql_str = """
            SELECT DISTINCT lpr.cluster_name 
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE lpr.cluster_name IS NOT NULL AND lpr.cluster_name != ''
        """
        params = {}
        if kb_id:
            sql_str += " AND lf.kb_id = :kb_id"
            params["kb_id"] = kb_id
        sql_str += " ORDER BY lpr.cluster_name"
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [row["cluster_name"] for row in rows] if rows else []

    @staticmethod
    async def get_host_list(kb_id: str | None = None) -> list[str]:
        """获取所有非空的主机名称列表"""
        sql_str = """
            SELECT DISTINCT lpr.host 
            FROM log_parse_result_table lpr
            LEFT JOIN log_file_table lf ON lpr.log_id = lf.id
            WHERE lpr.host IS NOT NULL AND lpr.host != ''
        """
        params = {}
        if kb_id:
            sql_str += " AND lf.kb_id = :kb_id"
            params["kb_id"] = kb_id
        sql_str += " ORDER BY lpr.host"
        rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
        return [row["host"] for row in rows] if rows else []
