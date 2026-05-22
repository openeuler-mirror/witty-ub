from pydantic import BaseModel, Field
from uuid import uuid4
from latency.ENUM.general import OnlineStatus
from latency.ENUM.model import ModelProvider, ModelLabel


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


class RunConfig(BaseModel):
    host: str = Field(
        default="0.0.0.0", description="服务运行的主机地址", alias="RUN_HOST"
    )
    port: int = Field(default=12144, description="服务运行的端口号", alias="RUN_PORT")


class ConfigModel(BaseModel):
    run_config: RunConfig = Field(default_factory=RunConfig, description="运行配置")
    task: TaskConfig = Field(default_factory=TaskConfig, description="任务配置")
    chat_model: ModelConfig | None = Field(default=None, description="聊天模型配置")
    embedding_model: ModelConfig | None = Field(
        default=None, description="向量化模型配置"
    )
