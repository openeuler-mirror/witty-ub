"""系统配置类"""
from pydantic import BaseModel, Field, model_validator
from uuid import uuid4
from latency.ENUM.general import OnlineStatus, LogLevel
from latency.ENUM.model import ModelProvider, ModelLabel


class ServiceConfig(BaseModel):
    is_debug: bool = Field(default=False, description="是否启用调试模式")
    uvicorn_ip: str = Field(default="0.0.0.0", description="FastAPI 服务的IP地址")
    uvicorn_port: int = Field(default=9772, description="FastAPI 服务的端口号")
    ssl_certfile: str | None = Field(None, description="SSL证书文件的路径")
    ssl_keyfile: str | None = Field(None, description="SSL密钥文件的路径")
    ssl_enable: bool = Field(default=False, description="是否启用SSL连接")
    log_level: LogLevel = Field(LogLevel.INFO, description="日志级别")


class DatabaseConfig(BaseModel):
    backend: str = Field(default="postgresql", description="数据库后端: sqlite 或 postgresql")
    db_path: str = Field(default="latency.db", description="SQLite数据库文件路径")
    pg_host: str = Field(default="127.0.0.1", description="PostgreSQL 主机地址")
    pg_port: int = Field(default=15432, description="PostgreSQL 端口")
    pg_database: str = Field(default="latency_test", description="PostgreSQL 数据库名")
    pg_user: str = Field(default="postgres", description="PostgreSQL 用户名")
    pg_password: str = Field(default="postgres", description="PostgreSQL 密码")
    pg_pool_size: int = Field(default=10, description="PostgreSQL 连接池大小")
    pg_max_overflow: int = Field(default=20, description="PostgreSQL 连接池最大溢出连接数")

    @model_validator(mode="after")
    def override_from_env(self):
        """支持通过环境变量覆盖单字段，便于容器部署时注入配置。

        环境变量名与字段名一致（全大写），例如：
            PG_HOST=postgres  ->  self.pg_host = "postgres"
            PG_PORT=5432      ->  self.pg_port = 5432
        """
        import os

        field_env_map = {
            "BACKEND": "backend",
            "DB_PATH": "db_path",
            "PG_HOST": "pg_host",
            "PG_PORT": "pg_port",
            "PG_DATABASE": "pg_database",
            "PG_USER": "pg_user",
            "PG_PASSWORD": "pg_password",
            "PG_POOL_SIZE": "pg_pool_size",
            "PG_MAX_OVERFLOW": "pg_max_overflow",
        }
        for env_name, field_name in field_env_map.items():
            val = os.getenv(env_name)
            if val is not None and val != "":
                field_type = self.__class__.model_fields[field_name].annotation
                try:
                    setattr(self, field_name, field_type(val))
                except (TypeError, ValueError):
                    pass
        return self

    def pg_dsn_url(self) -> str:
        """根据 host/port/database/user/password 构建 PostgreSQL DSN。"""
        from urllib.parse import quote_plus

        password = quote_plus(self.pg_password)
        return (
            f"postgresql+asyncpg://{self.pg_user}:{password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_database}"
        )


class TaskConfig(BaseModel):
    task_retry_times: int = Field(default=3, description="任务重试次数")
    cpu_limit: int = Field(default=64, description="任务使用CPU核数")


class ModelConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), description="模型ID")
    kb_id: str | None = Field(default=None, description="所属知识库ID")
    model_name: str = Field(default="", description="模型名称")
    online_status: OnlineStatus = Field(OnlineStatus.ONLINE, description="模型在线状态")
    model_labels: list[ModelLabel] = Field([], description="模型标签")
    model_provider: ModelProvider = Field(ModelProvider.OTHER, description="模型提供商")
    end_point: str = Field(default="", description="模型服务接口地址")
    api_key: str = Field(default="", description="模型服务API key")
    request_timeout: int = Field(default=60, description="请求超时时间")
    input_max_tokens: int = Field(default=2048, description="输入最大token数")
    output_max_tokens: int = Field(default=8192, description="输出最大token数")
    temperature: float = Field(default=0.7, description="温度系数")
    batch_size: int = Field(default=16, description="批处理大小")


class DSLogAnalyzerConfig(BaseModel):
    # 多窗口配置（每个指标都会使用所有窗口检测）
    sliding_window_sizes: list[int] = Field(default=[100, 200, 300, 500], description="滑动窗口大小列表")
    sliding_window_steps: list[int] = Field(default=[20, 30, 40, 50], description="滑动窗口步长列表，与窗口大小一一对应")
    zone_anomaly_density_threshold: float = Field(default=0.9999, description="区间异常密度阈值，超过此比例则整个区间标记为异常")

    # 各指标阈值配置
    total_p99_threshold_ms: float = Field(default=5.0, description="总时延P99阈值，单位毫秒")
    c2w_p99_threshold_ms: float = Field(default=1.0, description="C2W时延P99阈值，单位毫秒")
    w2w_p99_threshold_ms: float = Field(default=1.0, description="W2W时延P99阈值，单位毫秒")
    urma_link_p99_threshold_ms: float = Field(default=1.0, description="URMA建链时延P99阈值，单位毫秒")
    query_meta_p99_threshold_ms: float = Field(default=1.0, description="Worker QueryMeta时延P99阈值，单位毫秒")


class LogFilenamePatternConfig(BaseModel):
    ds_client_access_log_file: list[str] = Field(default_factory=list, description="SDK客户端接口日志文件匹配模式")
    ds_client_info_log_file: list[str] = Field(default_factory=list, description="SDK客户端信息日志文件匹配模式")
    ds_worker_access_log_file: list[str] = Field(default_factory=list, description="Worker接口日志文件匹配模式")
    ds_worker_info_log_file: list[str] = Field(default_factory=list, description="Worker信息日志文件匹配模式")
    resource_log_file: list[str] = Field(default_factory=list, description="资源日志文件匹配模式")


class DiagnosisRuntimeConfig(BaseModel):
    """可在服务运行期间热更新的诊断配置。"""

    log_filename_pattern: LogFilenamePatternConfig
    log_analyzer_params: DSLogAnalyzerConfig

    @model_validator(mode="after")
    def validate_runtime_config(self):
        empty_pattern_types = [
            key
            for key, patterns in self.log_filename_pattern.model_dump().items()
            if not patterns
        ]
        if empty_pattern_types:
            raise ValueError(
                f"日志文件名 Pattern 不能为空: {', '.join(empty_pattern_types)}"
            )

        params = self.log_analyzer_params
        if not params.sliding_window_sizes:
            raise ValueError("至少需要配置一组滑动窗口")
        if len(params.sliding_window_sizes) != len(params.sliding_window_steps):
            raise ValueError("滑动窗口大小与步长数量必须一致")
        if any(value <= 0 for value in params.sliding_window_sizes):
            raise ValueError("滑动窗口大小必须大于 0")
        if any(value <= 0 for value in params.sliding_window_steps):
            raise ValueError("滑动窗口步长必须大于 0")
        if not 0 <= params.zone_anomaly_density_threshold <= 1:
            raise ValueError("区间异常密度阈值必须在 0 到 1 之间")
        return self


class ConfigModel(BaseModel):
    service: ServiceConfig = Field(
        default_factory=ServiceConfig, description="服务配置"
    )
    db: DatabaseConfig = Field(default_factory=DatabaseConfig, description="数据库配置")
    task: TaskConfig = Field(default_factory=TaskConfig, description="任务配置")
    chat_model: ModelConfig | None = Field(default=None, description="聊天模型配置")
    embedding_model: ModelConfig | None = Field(
        default=None, description="向量化模型配置"
    )
    log_filename_pattern: LogFilenamePatternConfig = Field(
        default_factory=LogFilenamePatternConfig,
        description="日志文件名匹配模式",
    )
    log_analyzer_params: DSLogAnalyzerConfig = Field(
        default_factory=DSLogAnalyzerConfig,
        description="DS日志分析配置",
    )
