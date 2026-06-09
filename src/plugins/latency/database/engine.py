import os
from multiprocessing import Lock as ProcessLock
import asyncio
import sqlite3
import logging
from typing import Any, Optional
from latency.config.config import Config

# 配置日志
logger = logging.getLogger(__name__)
# 表结构定义
table_ddl_list = {
    "log_knowledge_table": """
        CREATE TABLE IF NOT EXISTS log_knowledge_table (
            id TEXT PRIMARY KEY,
            image_bytes BLOB,
            name TEXT,
            description TEXT,
            task_cnt INTEGER,
            log_file_cnt INTEGER,
            anomaly_cnt INTEGER,
            existed_status BOOLEAN NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """,
    "failure_mode_knowledge_table": """
        CREATE TABLE IF NOT EXISTS failure_mode_knowledge_table (
            id TEXT PRIMARY KEY,
            name TEXT,
            symptom TEXT,
            root_cause TEXT,
            solution TEXT,
            failure_domain TEXT,
            children_failure_mode_ids TEXT
        )
    """,
    "log_file_table": """
        CREATE TABLE IF NOT EXISTS log_file_table (
            id TEXT PRIMARY KEY,
            kb_id TEXT,
            name TEXT,
            parse_status TEXT,
            file_path TEXT,
            file_size INTEGER,
            anomaly_cnt INTEGER,
            existed_status BOOLEAN NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """,
    "src_dst_aggregated_event_table": """
        CREATE TABLE IF NOT EXISTS src_dst_aggregated_event_table (
            id TEXT PRIMARY KEY,
            src_ip TEXT,
            dst_ip TEXT,
            log_id TEXT,
            log_parse_result_cnt INTEGER,
            anomaly_log_parse_result_cnt INTEGER,
            anomaly_cnt INTEGER,
            ave_total_latency REAL,
            min_total_latency REAL,
            max_total_latency REAL,
            p99_total_latency REAL,
            p95_total_latency REAL,
            ave_query_meta_latency REAL,
            min_query_meta_latency REAL,
            max_query_meta_latency REAL,
            p99_query_meta_latency REAL,
            p95_query_meta_latency REAL,
            ave_urma_total_latency REAL,
            min_urma_total_latency REAL,
            max_urma_total_latency REAL,
            p99_urma_total_latency REAL,
            p95_urma_total_latency REAL,
            ave_urma_link_latency REAL,
            min_urma_link_latency REAL,
            max_urma_link_latency REAL,
            p99_urma_link_latency REAL,
            p95_urma_link_latency REAL,
            ave_c2w_urma_latency REAL,
            min_c2w_urma_latency REAL,
            max_c2w_urma_latency REAL,
            p99_c2w_urma_latency REAL,
            p95_c2w_urma_latency REAL,
            ave_w2w_urma_latency REAL,
            min_w2w_urma_latency REAL,
            max_w2w_urma_latency REAL,
            p99_w2w_urma_latency REAL,
            p95_w2w_urma_latency REAL,
            existed_status BOOLEAN NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """,
    "anomalous_event_table": """
    CREATE TABLE IF NOT EXISTS anomalous_event_table (
        id TEXT PRIMARY KEY,
        log_id TEXT,
        aggregated_event_id TEXT,
        start_log_parse_offset INTEGER,
        end_log_parse_offset INTEGER,
        anomaly_reason TEXT,
        existed_status BOOLEAN NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """,
    # 异常事件链
    "anomalous_event_chain_table": """
    CREATE TABLE IF NOT EXISTS anomalous_event_chain_table (
        id TEXT PRIMARY KEY,
        log_id TEXT,
        anomalous_event_id TEXT,
        name TEXT,
        description TEXT,
        anomaly_code TEXT,
        offset INTEGER,
        existed_status BOOLEAN NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """,
    "log_parse_result_table": """
        CREATE TABLE IF NOT EXISTS log_parse_result_table(
            id TEXT PRIMARY KEY,
            log_id TEXT,
            aggregated_event_id TEXT NOT NULL DEFAULT '',
            anomalous_event_id TEXT NOT NULL DEFAULT '',
            trace_id TEXT,
            timestamp TEXT,
            src_ip TEXT,
            dst_ip TEXT,
            pod_ip TEXT,
            cluster_name TEXT,
            host TEXT,
            total_latency REAL,
            c2w_latency REAL,
            worker_query_meta_latency REAL,
            urma_total_latency REAL,
            urma_link_latency REAL,
            urma_inflight_count INTEGER,
            c2w_urma_latency REAL,
            w2w_urma_latency REAL,
            operation TEXT,
            data_size TEXT,
            offset INTEGER,
            is_anomalous BOOLEAN,
            content TEXT,
            anomaly_reason TEXT,
            anomaly_score REAL,
            remark TEXT,
            existed_status BOOLEAN NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """,
    "log_failure_event_table": """
        CREATE TABLE IF NOT EXISTS log_failure_event_table(
            id TEXT PRIMARY KEY,
            log_id TEXT,
            log_file TEXT,
            raw_text TEXT,
            host_name TEXT DEFAULT 'Unknown',
            timestamp TEXT,
            level TEXT,
            filename TEXT,
            pod_name TEXT,
            pid TEXT,
            tid TEXT,
            trace_id TEXT,
            cluster_name TEXT,
            message TEXT,
            status_code TEXT,
            failure_mode TEXT
        )
    """,
    "trace_failure_event_table": """
        CREATE TABLE IF NOT EXISTS trace_failure_event_table(
            id TEXT PRIMARY KEY,
            log_id TEXT,
            trace_id TEXT,
            pod_names TEXT,
            host_names TEXT,
            cluster_names TEXT,
            timestamp TEXT,
            status_code TEXT,
            failure_mode TEXT
        )
    """,
    "task_table": """
        CREATE TABLE IF NOT EXISTS task_table (
            id TEXT PRIMARY KEY,
            kb_id TEXT,
            op_id TEXT,
            retry_times INTEGER NOT NULL DEFAULT 0,
            task_name TEXT,
            task_type TEXT,
            status TEXT,
            existed_status BOOLEAN NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            duration_seconds REAL
        )
    """,
    "task_report_table": """
        CREATE TABLE IF NOT EXISTS task_report_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            progress REAL,
            message TEXT,
            existed_status BOOLEAN NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """,
}


class AsyncSQLiteSingleton:
    # 类级别的单例实例
    _instance: Optional["AsyncSQLiteSingleton"] = None
    # 进程级锁（跨进程保护）
    _process_lock = ProcessLock()
    # 类级锁（单例创建保护）
    _class_lock = asyncio.Lock()

    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            with cls._process_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 防止重复初始化
        if hasattr(self, "_initialized") and self._initialized:
            return

        # 数据库配置
        db_path = Config().get_config().db.db_path
        # 如果是相对路径，使其相对于 latency 目录
        if not os.path.isabs(db_path):
            latency_dir = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(latency_dir, db_path)
        self.DB_PATH = db_path
        # 确保数据库所在目录存在
        db_dir = os.path.dirname(self.DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        # 异步锁（协程级）
        self._async_lock = asyncio.Lock()
        # 数据库连接（复用连接，避免频繁创建/关闭）
        self._conn: Optional[sqlite3.Connection] = None
        # 初始化标记
        self._initialized = False

        # 初始化数据库连接
        self._init_connection()

    # -------------------------- 表结构迁移 --------------------------
    def _sync_migrate_database(self) -> bool:
        """同步执行数据库迁移（添加新字段等）"""
        if not self._conn:
            self._init_connection()

        # 表结构迁移语句列表
        migrate_sql_list = [
            # 为 log_parse_result_table 添加 cluster_name 和 host 字段
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN cluster_name TEXT"),
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN host TEXT"),
            # 为 task_table 添加 completed_at 和 duration_seconds 字段
            ("task_table", "ALTER TABLE task_table ADD COLUMN completed_at TEXT"),
            ("task_table", "ALTER TABLE task_table ADD COLUMN duration_seconds REAL"),
            # 为 timestamp 字段添加索引，加速时间范围查询
            ("log_parse_result_table", "CREATE INDEX IF NOT EXISTS idx_timestamp ON log_parse_result_table(timestamp)"),
        ]

        try:
            for table_name, sql in migrate_sql_list:
                try:
                    self._conn.execute(sql)
                    logger.info(f"成功为 {table_name} 执行迁移: {sql}")
                except sqlite3.OperationalError as e:
                    # 如果字段已存在，忽略错误
                    if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                        logger.info(f"字段/索引已存在，跳过迁移: {sql}")
                    else:
                        raise
            self._conn.commit()
            logger.info("数据库迁移完成")
            return True
        except sqlite3.Error as e:
            self._conn.rollback()
            logger.error(f"数据库迁移失败: {e}")
            return False

    def _init_connection(self):
        """初始化数据库连接（复用连接）"""
        try:
            # 增加超时时间到30秒，关闭自动提交
            self._conn = sqlite3.connect(
                self.DB_PATH,
                check_same_thread=False,
                timeout=30.0,  # 增加超时时间
                isolation_level=None,  # 关闭自动提交，手动控制事务
            )
            # 启用外键约束
            self._conn.execute("PRAGMA foreign_keys = ON")
            # 启用 WAL 模式（提高并发性能）
            self._conn.execute("PRAGMA journal_mode=WAL")
            # 设置同步模式为NORMAL（平衡性能和安全性）
            self._conn.execute("PRAGMA synchronous=NORMAL")

            logger.info("数据库连接初始化成功")
        except sqlite3.Error as e:
            logger.error(f"数据库连接初始化失败: {e}")
            raise

    # -------------------------- 同步操作函数（所有操作都在同一个连接执行） --------------------------
    def _sync_init_database(self) -> bool:
        """同步初始化数据库（复用连接）"""
        if not self._conn:
            self._init_connection()

        try:
            # 初始化所有表
            for table_name, ddl in table_ddl_list.items():
                self._conn.execute(ddl)
            self._conn.commit()
            logger.info("数据库初始化成功，表创建完成")
            
            # 执行数据库迁移
            self._sync_migrate_database()
            
            self._initialized = True
            return True
        except sqlite3.Error as e:
            self._conn.rollback()
            logger.error(f"数据库初始化失败: {e}")
            return False

    def _sync_execute_query(self, sql: str, params: dict | tuple = ()) -> list[dict]:
        """同步执行查询（复用连接）"""
        if not self._conn:
            self._init_connection()

        try:
            self._conn.row_factory = sqlite3.Row
            cursor = self._conn.cursor()
            cursor.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"执行查询成功，返回 {len(results)} 条记录")
            return results
        except sqlite3.Error as e:
            logger.error(f"执行查询失败: {e} (SQL: {sql}, params: {params})")
            return []

    def _sync_execute_modify(self, sql: str, params: Any = ()) -> bool:
        """
        同步执行增删改（支持单条/批量，复用连接）
        :param sql: SQL修改语句（位置参数用?，命名参数用:param_name）
        :param params: 单条：dict/元组；批量：list[元组]
        :return: 是否执行成功
        """
        if not self._conn:
            self._init_connection()

        try:
            cursor = self._conn.cursor()

            # 判断是否为批量操作
            if isinstance(params, list) and len(params) > 0:
                # 批量操作：使用 executemany
                cursor.executemany(sql, params)
                logger.debug(f"批量执行修改成功，影响行数: {cursor.rowcount}")
            else:
                # 单条操作：使用 execute
                cursor.execute(sql, params)
                logger.debug(f"单条执行修改成功，影响行数: {cursor.rowcount}")

            self._conn.commit()
            return True
        except sqlite3.Error as e:
            self._conn.rollback()
            logger.error(f"执行修改失败: {e} (SQL: {sql}, params: {params})")
            return False

    # -------------------------- 异步封装接口 --------------------------
    async def init_database(self) -> bool:
        """异步初始化数据库"""
        async with self._async_lock:
            return await asyncio.to_thread(self._sync_init_database)

    async def execute_query(self, sql: str, params: dict | tuple = ()) -> list[dict]:
        """
        异步执行查询语句
        :param sql: SQL查询语句（支持命名参数 :param_name 或位置参数 ?）
        :param params: 命名参数字典或位置参数元组
        :return: 查询结果列表（每行是字典）
        """
        async with self._async_lock:
            return await asyncio.to_thread(self._sync_execute_query, sql, params)

    async def execute_modify(self, sql: str, params: Any = ()) -> bool:
        """
        异步执行增删改语句
        :param sql: SQL修改语句（支持命名参数 :param_name 或位置参数 ?）
        :param params: 命名参数字典或位置参数元组
        :return: 是否执行成功
        """
        async with self._async_lock:
            return await asyncio.to_thread(self._sync_execute_modify, sql, params)

    async def close_connection(self):
        """关闭数据库连接"""
        async with self._async_lock:

            def _close():
                if self._conn:
                    self._conn.close()
                    self._conn = None
                    logger.info("数据库连接已关闭")

            await asyncio.to_thread(_close)

    def __del__(self):
        """析构函数：确保连接关闭"""
        if self._conn:
            self._conn.close()
            logger.info("析构函数中关闭数据库连接")
