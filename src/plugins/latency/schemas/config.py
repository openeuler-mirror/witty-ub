from pydantic import BaseModel, Field
from uuid import uuid4
from latency.ENUM.ds_log import OpType, AccessLogCol, StatusCode
from latency.ENUM.general import OnlineStatus, LogLevel
from latency.ENUM.model import ModelProvider, ModelLabel


class ServiceConfig(BaseModel):
    is_debug: bool = Field(default=False, description="是否启用调试模式")
    uvicorn_ip: str = Field(default="0.0.0.0", description="FastAPI 服务的IP地址")
    uvicorn_port: int = Field(default=8000, description="FastAPI 服务的端口号")
    ssl_certfile: str | None = Field(None, description="SSL证书文件的路径")
    ssl_keyfile: str | None = Field(None, description="SSL密钥文件的路径")
    ssl_enable: bool = Field(default=False, description="是否启用SSL连接")
    log_level: LogLevel = Field(LogLevel.INFO, description="日志级别")


class DatabaseConfig(BaseModel):
    db_path: str = Field(default="latency.db", description="SQLite数据库文件路径")


class TaskConfig(BaseModel):
    task_retry_time: int = Field(default=3, description="任务重试次数")
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
    model_config = {"populate_by_name": True}

    total_p99_threshold_ms: float = Field(default=2.0, alias="TOTAL_P99_THRESHOLD_MS", description="总时延P99阈值，单位毫秒")
    c2w_p99_threshold_ms: float = Field(default=1.0, alias="C2W_P99_THRESHOLD_MS", description="C2W时延P99阈值，单位毫秒")
    w2w_p99_threshold_ms: float = Field(default=1.0, alias="W2W_P99_THRESHOLD_MS", description="W2W时延P99阈值，单位毫秒")
    urma_link_p99_threshold_ms: float = Field(default=1.0, alias="URMA_LINK_P99_THRESHOLD_MS", description="URMA建链时延P99阈值，单位毫秒")
    query_meta_p99_threshold_ms: float = Field(default=1.0, alias="QUERY_META_P99_THRESHOLD_MS", description="Worker QueryMeta时延P99阈值，单位毫秒")


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
    ds_log_analyzer: DSLogAnalyzerConfig = Field(
        default_factory=DSLogAnalyzerConfig,
        alias="DS_LOG_ANALYZER",
        description="DS日志分析配置",
    )
