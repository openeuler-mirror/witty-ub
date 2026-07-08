import os
from multiprocessing import Lock as ProcessLock
import asyncio
import sqlite3
import logging
import threading
from typing import Any, Optional, List
from latency.config.config import Config
from latency.ENUM.general import InitStatus

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
    "diagnosis_config_table": """
        CREATE TABLE IF NOT EXISTS diagnosis_config_table (
            kb_id TEXT PRIMARY KEY,
            config_json TEXT NOT NULL,
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
    "status_code_knowledge_table": """
        CREATE TABLE IF NOT EXISTS status_code_knowledge_table (
            status_code TEXT PRIMARY KEY,
            symptom TEXT NOT NULL,
            root_cause TEXT NOT NULL
        )
    """,
    "diagnosis_case_table": """
        CREATE TABLE IF NOT EXISTS diagnosis_case_table (
            id TEXT PRIMARY KEY,
            kb_id TEXT,
            fault_type TEXT NOT NULL,
            title TEXT,
            symptom_summary TEXT NOT NULL,
            root_cause TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0,
            failure_mode_ids TEXT NOT NULL DEFAULT '[]',
            status_codes TEXT NOT NULL DEFAULT '[]',
            fingerprint_json TEXT NOT NULL DEFAULT '{}',
            evidence_refs_json TEXT NOT NULL DEFAULT '[]',
            counter_evidence_json TEXT NOT NULL DEFAULT '[]',
            source_log_ids TEXT NOT NULL DEFAULT '[]',
            hit_count INTEGER NOT NULL DEFAULT 0,
            existed_status BOOLEAN NOT NULL DEFAULT 1,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """,
    "diagnosis_case_signal_table": """
        CREATE TABLE IF NOT EXISTS diagnosis_case_signal_table (
            case_id TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            signal_value TEXT NOT NULL,
            weight REAL NOT NULL DEFAULT 1,
            PRIMARY KEY (case_id, signal_type, signal_value)
        )
    """,
    "diagnosis_case_signal_table_idx_signal": """
        CREATE INDEX IF NOT EXISTS idx_diagnosis_case_signal
        ON diagnosis_case_signal_table(signal_type, signal_value)
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
            trace_failure_event_cnt INTEGER,
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
    "time_window_aggregated_table": """
        CREATE TABLE IF NOT EXISTS time_window_aggregated_table (
            id TEXT PRIMARY KEY,
            kb_id TEXT,
            log_id TEXT,
            time_bucket TEXT,
            src_ip TEXT,
            dst_ip TEXT,
            log_parse_result_cnt INTEGER,
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
    "time_window_aggregated_table_idx_kb_time": """
        CREATE INDEX IF NOT EXISTS idx_tw_kb_time
        ON time_window_aggregated_table(kb_id, time_bucket)
    """,
    "time_window_aggregated_table_idx_kb_src_dst": """
        CREATE INDEX IF NOT EXISTS idx_tw_kb_src_dst
        ON time_window_aggregated_table(kb_id, src_ip, dst_ip)
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
            created_at TEXT NOT NULL,
            sdk_process REAL,
            sdk_rpc REAL,
            local_worker_cost REAL,
            local_worker_lock REAL,
            remote_worker_cost REAL,
            remote_worker_rpc REAL,
            master_process REAL,
            master_rpc_total REAL
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
    "log_failure_event_table_idx_log_order": """
        CREATE INDEX IF NOT EXISTS idx_log_failure_log_order
        ON log_failure_event_table(log_id, log_file, timestamp, pid, tid)
    """,
    "log_failure_event_table_idx_log_trace": """
        CREATE INDEX IF NOT EXISTS idx_log_failure_log_trace
        ON log_failure_event_table(log_id, trace_id)
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
    "trace_failure_event_table_idx_log_id": """
        CREATE INDEX IF NOT EXISTS idx_trace_log_id ON trace_failure_event_table(log_id)
    """,
    "trace_failure_event_table_idx_timestamp": """
        CREATE INDEX IF NOT EXISTS idx_trace_timestamp ON trace_failure_event_table(timestamp)
    """,
    "trace_failure_event_table_idx_status_code": """
        CREATE INDEX IF NOT EXISTS idx_trace_status_code ON trace_failure_event_table(status_code)
    """,
    "trace_failure_event_table_idx_log_timestamp": """
        CREATE INDEX IF NOT EXISTS idx_trace_log_timestamp ON trace_failure_event_table(log_id, timestamp)
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
    # 线程级锁（保护初始化过程）
    _init_lock = threading.Lock()
    # 读连接池最大连接数
    _max_read_conns = 5

    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            with cls._process_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 防止重复初始化
        if hasattr(self, "_initialized") and self._initialized != InitStatus.UNINITIALIZED:
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
        # 异步锁（协程级）- 保护写操作
        self._async_lock = asyncio.Lock()
        # 写连接（用于增删改操作，需要加锁）
        self._write_conn: Optional[sqlite3.Connection] = None
        # 读连接池（用于查询操作，WAL模式下可并发）
        self._read_conns: List[sqlite3.Connection] = []
        # 读连接池锁（保护连接池操作）
        self._read_pool_lock = threading.Lock()
        # 当前读连接索引（轮询使用）
        self._read_conn_index = 0
        # 初始化状态标记（UNINITIALIZED/SUCCESS/FAILED）
        self._initialized: InitStatus = InitStatus.UNINITIALIZED

        # 初始化数据库写连接
        self._init_write_connection()

    # -------------------------- 表结构迁移 --------------------------
    def _sync_migrate_database(self) -> bool:
        """同步执行数据库迁移（添加新字段等）"""
        if not self._write_conn:
            self._init_write_connection()

        migrate_sql_list = [
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN cluster_name TEXT"),
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN host TEXT"),
            ("task_table", "ALTER TABLE task_table ADD COLUMN completed_at TEXT"),
            ("task_table", "ALTER TABLE task_table ADD COLUMN duration_seconds REAL"),
            ("log_parse_result_table", "CREATE INDEX IF NOT EXISTS idx_timestamp ON log_parse_result_table(timestamp)"),
            (
                "log_failure_event_table",
                "CREATE INDEX IF NOT EXISTS idx_log_failure_log_order ON log_failure_event_table(log_id, log_file, timestamp, pid, tid)",
            ),
            (
                "log_failure_event_table",
                "CREATE INDEX IF NOT EXISTS idx_log_failure_log_trace ON log_failure_event_table(log_id, trace_id)",
            ),
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN sdk_process REAL"),
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN sdk_rpc REAL"),
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN local_worker_cost REAL"),
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN local_worker_lock REAL"),
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN remote_worker_cost REAL"),
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN remote_worker_rpc REAL"),
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN master_process REAL"),
            ("log_parse_result_table", "ALTER TABLE log_parse_result_table ADD COLUMN master_rpc_total REAL"),
            (
                "diagnosis_case_table",
                """
                CREATE TABLE IF NOT EXISTS diagnosis_case_table (
                    id TEXT PRIMARY KEY,
                    kb_id TEXT,
                    fault_type TEXT NOT NULL,
                    title TEXT,
                    symptom_summary TEXT NOT NULL,
                    root_cause TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    failure_mode_ids TEXT NOT NULL DEFAULT '[]',
                    status_codes TEXT NOT NULL DEFAULT '[]',
                    fingerprint_json TEXT NOT NULL DEFAULT '{}',
                    evidence_refs_json TEXT NOT NULL DEFAULT '[]',
                    counter_evidence_json TEXT NOT NULL DEFAULT '[]',
                    source_log_ids TEXT NOT NULL DEFAULT '[]',
                    hit_count INTEGER NOT NULL DEFAULT 0,
                    existed_status BOOLEAN NOT NULL DEFAULT 1,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """,
            ),
            (
                "diagnosis_case_signal_table",
                """
                CREATE TABLE IF NOT EXISTS diagnosis_case_signal_table (
                    case_id TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    signal_value TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1,
                    PRIMARY KEY (case_id, signal_type, signal_value)
                )
                """,
            ),
            (
                "diagnosis_case_signal_table",
                "CREATE INDEX IF NOT EXISTS idx_diagnosis_case_signal ON diagnosis_case_signal_table(signal_type, signal_value)",
            ),
        ]

        try:
            for table_name, sql in migrate_sql_list:
                try:
                    self._write_conn.execute(sql)
                    logger.info(f"成功为 {table_name} 执行迁移: {sql}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                        logger.info(f"字段/索引已存在，跳过迁移: {sql}")
                    else:
                        raise
            self._write_conn.commit()
            logger.info("数据库迁移完成")
            return True
        except sqlite3.Error as e:
            self._write_conn.rollback()
            logger.error(f"数据库迁移失败: {e}")
            return False

    def _init_write_connection(self):
        """初始化写连接（用于增删改操作）"""
        try:
            self._write_conn = sqlite3.connect(
                self.DB_PATH,
                check_same_thread=False,
                timeout=30.0,
                isolation_level=None,
            )
            self._write_conn.execute("PRAGMA foreign_keys = ON")
            self._write_conn.execute("PRAGMA journal_mode=WAL")
            self._write_conn.execute("PRAGMA synchronous=NORMAL")

            logger.info("数据库写连接初始化成功")
        except sqlite3.Error as e:
            logger.error(f"数据库写连接初始化失败: {e}")
            raise

    def _create_read_connection(self) -> sqlite3.Connection:
        """创建只读连接（用于查询操作）"""
        try:
            conn = sqlite3.connect(
                self.DB_PATH,
                check_same_thread=False,
                timeout=5.0,
                isolation_level=None,
            )
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA query_only=ON")
            conn.execute("PRAGMA busy_timeout=3000")

            logger.info("数据库只读连接创建成功")
            return conn
        except sqlite3.Error as e:
            logger.error(f"数据库只读连接创建失败: {e}")
            raise

    def _get_read_connection(self) -> sqlite3.Connection:
        """从连接池获取只读连接（线程安全）"""
        with self._read_pool_lock:
            if not self._read_conns:
                for _ in range(self._max_read_conns):
                    self._read_conns.append(self._create_read_connection())

            self._read_conn_index = (self._read_conn_index + 1) % len(self._read_conns)
            return self._read_conns[self._read_conn_index]

    # -------------------------- 同步操作函数 --------------------------
    def _sync_init_database(self) -> bool:
        """同步初始化数据库"""
        if not self._write_conn:
            self._init_write_connection()

        try:
            self._write_conn.execute("PRAGMA journal_mode=WAL")
            self._write_conn.execute("PRAGMA busy_timeout=5000")
            self._write_conn.execute("PRAGMA synchronous=NORMAL")
            
            for table_name, ddl in table_ddl_list.items():
                self._write_conn.execute(ddl)
            self._write_conn.commit()
            logger.info("数据库初始化成功，表创建完成")
            
            migrate_result = self._sync_migrate_database()
            if not migrate_result:
                logger.error("数据库迁移失败")
                self._write_conn.rollback()
                self._initialized = InitStatus.FAILED
                return False
            
            self._initialized = InitStatus.SUCCESS
            return True
        except sqlite3.Error as e:
            self._write_conn.rollback()
            self._initialized = InitStatus.FAILED
            logger.error(f"数据库初始化失败: {e}")
            return False

    def _sync_execute_query_on_conn(self, conn: sqlite3.Connection, sql: str, params: dict | tuple = ()) -> list[dict]:
        """在指定连接上同步执行查询"""
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"执行查询成功，返回 {len(results)} 条记录")
            return results
        except sqlite3.Error as e:
            logger.error(f"执行查询失败: {e} (SQL: {sql}, params: {params})")
            return []

    def _sync_execute_modify(self, sql: str, params: Any = ()) -> tuple[bool, int]:
        """
        同步执行增删改（支持单条/批量）
        :param sql: SQL修改语句（位置参数用?，命名参数用:param_name）
        :param params: 单条：dict/元组；批量：list[元组]
        :return: (是否执行成功, 影响行数)
        """
        if not self._write_conn:
            self._init_write_connection()
        
        self.ensure_initialized()

        try:
            cursor = self._write_conn.cursor()
            started_transaction = not self._write_conn.in_transaction
            if started_transaction:
                self._write_conn.execute("BEGIN")

            if isinstance(params, list) and len(params) > 0:
                cursor.executemany(sql, params)
                rowcount = cursor.rowcount
                logger.debug(f"批量执行修改成功，影响行数: {rowcount}")
            else:
                cursor.execute(sql, params)
                rowcount = cursor.rowcount
                logger.debug(f"单条执行修改成功，影响行数: {rowcount}")

            if started_transaction:
                self._write_conn.commit()
            return True, rowcount
        except sqlite3.Error as e:
            if self._write_conn.in_transaction:
                self._write_conn.rollback()
            logger.error(f"执行修改失败: {e} (SQL: {sql}, params: {params})")
            return False, 0

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
        if self._is_read_only(sql):
            return await asyncio.to_thread(self._sync_execute_read_query, sql, params)
        else:
            async with self._async_lock:
                return await asyncio.to_thread(self._sync_execute_write_query, sql, params)
    
    def _sync_execute_read_query(self, sql: str, params: dict | tuple = ()) -> list[dict]:
        """同步执行只读查询（使用读连接池）"""
        self.ensure_initialized()
        
        conn = self._get_read_connection()
        return self._sync_execute_query_on_conn(conn, sql, params)
    
    def _sync_execute_write_query(self, sql: str, params: dict | tuple = ()) -> list[dict]:
        """同步执行写查询（使用写连接）"""
        if not self._write_conn:
            self._init_write_connection()
        
        self.ensure_initialized()
        
        return self._sync_execute_query_on_conn(self._write_conn, sql, params)
    
    def _is_read_only(self, sql: str) -> bool:
        """判断 SQL 是否为只读操作"""
        stripped = sql.strip().upper()
        if stripped.startswith('SELECT'):
            return True
        if stripped.startswith('PRAGMA'):
            pragma_parts = stripped.split()
            if len(pragma_parts) >= 2:
                pragma_name = pragma_parts[1].strip(';')
                read_only_pragmas = {
                    'DATABASE_LIST', 'TABLE_INFO', 'INDEX_LIST', 'INDEX_INFO',
                    'FOREIGN_KEY_LIST', 'COLLATION_LIST', 'SCHEMA_VERSION',
                    'USER_VERSION', 'INTEGRITY_CHECK', 'QUICK_CHECK', 'PAGE_COUNT',
                    'PAGE_SIZE', 'ENCODING', 'TEMP_STORE', 'AUTO_VACUUM', 'CACHE_SIZE',
                }
                return pragma_name in read_only_pragmas
            return False
        return False

    async def execute_modify(self, sql: str, params: Any = ()) -> tuple[bool, int]:
        """
        异步执行增删改语句
        :param sql: SQL修改语句（支持命名参数 :param_name 或位置参数 ?）
        :param params: 命名参数字典或位置参数元组
        :return: (是否执行成功, 影响行数)
        """
        async with self._async_lock:
            return await asyncio.to_thread(self._sync_execute_modify, sql, params)

    async def close_connection(self):
        """关闭所有数据库连接"""
        async with self._async_lock:

            def _close():
                if self._write_conn:
                    self._write_conn.close()
                    self._write_conn = None
                    logger.info("数据库写连接已关闭")
                
                for conn in self._read_conns:
                    conn.close()
                self._read_conns = []
                logger.info("数据库读连接池已关闭")

            await asyncio.to_thread(_close)

    def ensure_initialized(self):
        """确保数据库连接和表结构已初始化（线程安全）"""
        if not self._write_conn:
            self._init_write_connection()
        
        if self._initialized == InitStatus.SUCCESS:
            return
        
        if self._initialized == InitStatus.FAILED:
            raise RuntimeError("数据库初始化已失败，无法执行数据库操作")
        
        with self._init_lock:
            if self._initialized == InitStatus.SUCCESS:
                return
            if self._initialized == InitStatus.FAILED:
                raise RuntimeError("数据库初始化已失败，无法执行数据库操作")
            
            success = self._sync_init_database()
            if not success:
                raise RuntimeError(f"数据库初始化失败，路径: {self.DB_PATH}")

    def __del__(self):
        """析构函数：确保所有连接关闭"""
        if self._write_conn:
            self._write_conn.close()
            logger.info("析构函数中关闭数据库写连接")
        
        for conn in self._read_conns:
            conn.close()
        logger.info("析构函数中关闭数据库读连接池")
