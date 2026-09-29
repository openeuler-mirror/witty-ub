# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""schemas 补充测试：config / request / failure_mode / log / brpc_diagnosis 的未覆盖分支。"""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from latency.schemas.brpc_diagnosis import (
    BrpcDiagBatch,
    BrpcDiagSchema,
    parse_brpc_query_timestamp,
)
from latency.schemas.config import (
    DatabaseConfig,
    DiagnosisRuntimeConfig,
    DSLogAnalyzerConfig,
    LogFilenamePatternConfig,
)
from latency.schemas.failure_mode import FailureModeModel
from latency.schemas.log import (
    C2WLogParseResultDataclass,
    generate_uuids_hex,
    LogParseResultBatch,
    LogParseResultDataclass,
    LogParseResultModel,
    SparseLogParseResultDataclass,
)
from latency.schemas.request import (
    CreateLogKnowledgeRequest,
    RunBrpcDiagnosisRequest,
)


class TestDatabaseConfigEnvOverride:
    def test_env_override_applies(self, monkeypatch):
        """环境变量按字段类型转换后覆盖默认值。"""
        monkeypatch.setenv("BACKEND", "sqlite")
        monkeypatch.setenv("PG_HOST", "pg.example.com")
        monkeypatch.setenv("PG_PORT", "6543")
        cfg = DatabaseConfig()
        assert cfg.backend == "sqlite"
        assert cfg.pg_host == "pg.example.com"
        assert cfg.pg_port == 6543

    def test_env_override_invalid_value_keeps_default(self, monkeypatch):
        """环境变量无法转换为字段类型时忽略该字段，保留默认值。"""
        monkeypatch.setenv("PG_POOL_SIZE", "not-a-number")
        monkeypatch.setenv("PG_PORT", "")
        cfg = DatabaseConfig()
        assert cfg.pg_pool_size == 10
        assert cfg.pg_port == 5432

    def test_pg_dsn_url_escapes_special_characters(self):
        """DSN 生成时密码需做 URL 编码，避免特殊字符破坏连接串。"""
        cfg = DatabaseConfig(
            pg_user="ub_user",
            pg_password="p@ss/w:rd",
            pg_host="db-host",
            pg_port=1,
            pg_database="demo",
        )
        assert cfg.pg_dsn_url() == (
            "postgresql+asyncpg://ub_user:p%40ss%2Fw%3Ard@db-host:1/demo"
        )


class TestDiagnosisRuntimeConfigValidation:
    def _full_patterns(self) -> LogFilenamePatternConfig:
        return LogFilenamePatternConfig(
            ds_client_access_log_file=["a_access.log"],
            ds_client_info_log_file=["a.INFO.log"],
            ds_worker_access_log_file=["w_access.log"],
            ds_worker_info_log_file=["w.INFO.log"],
            resource_log_file=["resource.log"],
            brpc_log_file_patterns=["brpc.log"],
        )

    def test_empty_pattern_rejected(self):
        """任一日志文件 Pattern 为空即拒绝，并在报错中列出字段名。"""
        with pytest.raises(ValidationError) as exc_info:
            DiagnosisRuntimeConfig(
                log_filename_pattern=LogFilenamePatternConfig(),
                log_analyzer_params=DSLogAnalyzerConfig(),
            )
        assert "日志文件名 Pattern 不能为空" in str(exc_info.value)
        assert "ds_client_access_log_file" in str(exc_info.value)

    def test_empty_sliding_window_rejected(self):
        """滑动窗口列表为空时拒绝。"""
        with pytest.raises(ValidationError) as exc_info:
            DiagnosisRuntimeConfig(
                log_filename_pattern=self._full_patterns(),
                log_analyzer_params=DSLogAnalyzerConfig(sliding_window_sizes=[]),
            )
        assert "至少需要配置一组滑动窗口" in str(exc_info.value)

    def test_window_size_step_mismatch_rejected(self):
        """滑动窗口大小与步长数量不一致时拒绝。"""
        with pytest.raises(ValidationError) as exc_info:
            DiagnosisRuntimeConfig(
                log_filename_pattern=self._full_patterns(),
                log_analyzer_params=DSLogAnalyzerConfig(
                    sliding_window_sizes=[100, 200],
                    sliding_window_steps=[20],
                ),
            )
        assert "滑动窗口大小与步长数量必须一致" in str(exc_info.value)


class TestRunBrpcDiagnosisRequest:
    def test_invalid_format_rejected(self):
        """非 YYYY-MM-DD HH:MM:SS 格式的字符串直接拒绝。"""
        with pytest.raises(ValidationError) as exc_info:
            RunBrpcDiagnosisRequest(start_time="2026/01/01 00:00:00")
        assert "start_time 必须使用 YYYY-MM-DD HH:MM:SS 格式" in str(exc_info.value)

    def test_non_padded_time_rejected(self):
        """可被 strptime 解析但不满足零填充格式的时间同样拒绝。"""
        with pytest.raises(ValidationError):
            RunBrpcDiagnosisRequest(start_time="2026-01-01 0:0:0")

    def test_valid_time_accepted(self):
        req = RunBrpcDiagnosisRequest(start_time="2026-01-01 12:30:45")
        assert req.start_time == "2026-01-01 12:30:45"


class TestCreateLogKnowledgeRequest:
    def test_blank_name_rejected(self):
        """name 去除首尾空白后为空时拒绝。"""
        with pytest.raises(ValidationError) as exc_info:
            CreateLogKnowledgeRequest(name="   ", description="知识描述")
        assert "知识名称不能为空" in str(exc_info.value)

    def test_name_stripped(self):
        """合法 name 去除首尾空白后保存。"""
        req = CreateLogKnowledgeRequest(name="  知识名称  ", description="知识描述")
        assert req.name == "知识名称"


class TestFailureModeModel:
    def _base(self, **overrides):
        base = dict(
            id="fm-1",
            name="故障模式",
            symptom="故障表现",
            root_cause="故障根因",
            solution="解决方案",
            failure_domain="故障域",
            children_failure_mode_ids="",
        )
        base.update(overrides)
        return base

    def test_error_code_bool_coerced_to_digits(self):
        """布尔 error_code 归一化为 "1"/"0" 字符串，避免真假值被当作文本。"""
        assert FailureModeModel(**self._base(error_code=True)).error_code == "1"
        assert FailureModeModel(**self._base(error_code=False)).error_code == "0"

    def test_error_code_serializer(self):
        """序列化时非空 error_code 原样输出，空值输出 None。"""
        model = FailureModeModel(**self._base(error_code="E4001"))
        assert model.model_dump()["error_code"] == "E4001"
        empty_model = FailureModeModel(**self._base(error_code=""))
        assert empty_model.error_code is None
        assert empty_model.model_dump()["error_code"] is None


class TestLogParseResultBatch:
    def test_preallocated_with_hint(self):
        """批次对象按 size 预分配 None 占位，并携带 all_sparse 提示。"""
        batch = LogParseResultBatch(3, all_sparse=True)
        assert len(batch) == 3
        assert list(batch) == [None, None, None]
        assert batch.all_sparse is True

    def test_empty_batch(self):
        batch = LogParseResultBatch(0, all_sparse=False)
        assert batch == []
        assert batch.all_sparse is False


class TestLogParseResultToPydantic:
    def test_full_dataclass_to_pydantic(self):
        """完整解析结果转换：基础字段与 YUANRONG 指标字段逐项映射。"""
        data = LogParseResultDataclass(
            total_latency=1.5,
            is_anomalous=True,
            id="id-1",
            total_latency_us=1500.0,
            request_mode="near",
            sdk_processing_us=100.0,
        )
        model = data.to_pydantic()
        assert isinstance(model, LogParseResultModel)
        assert model.id == "id-1"
        assert model.total_latency == 1.5
        assert model.is_anomalous is True
        assert model.total_latency_us == 1500.0
        assert model.request_mode == "near"
        assert model.sdk_processing_us == 100.0

    def test_c2w_dataclass_to_pydantic_missing_metric_fields(self):
        """当前实现：C2W 紧凑结果缺少 YUANRONG 指标字段，to_pydantic 抛 AttributeError。

        该方法目前无生产调用方；若未来启用需先为紧凑 dataclass 补齐
        YUANRONG_METRIC_FIELDS 对应的 ClassVar[None] 定义。
        """
        data = C2WLogParseResultDataclass(
            total_latency=2.0, is_anomalous=False, c2w_latency=0.5
        )
        with pytest.raises(AttributeError, match="total_latency_us"):
            data.to_pydantic()

    def test_sparse_dataclass_to_pydantic_missing_metric_fields(self):
        """当前实现：Sparse 紧凑结果同样缺少 YUANRONG 指标字段。"""
        data = SparseLogParseResultDataclass(total_latency=3.0, is_anomalous=False)
        with pytest.raises(AttributeError, match="total_latency_us"):
            data.to_pydantic()


class TestGenerateUuidsHex:
    def test_batch_generate(self):
        """批量生成 128-bit UUID hex：数量、长度与基本唯一性。"""
        ids = generate_uuids_hex(8)
        assert len(ids) == 8
        assert all(isinstance(value, str) and len(value) == 32 for value in ids)
        assert len(set(ids)) == 8

    def test_zero_count(self):
        assert generate_uuids_hex(0) == []


def _brpc_node(node_id: str, node_type: str) -> dict:
    return {
        "node_id": node_id,
        "node_type": node_type,
        "component": "ubsocket",
        "name": "节点",
        "filename": "file.cc",
        "function_name": "Func",
        "phenomenon": "现象",
        "cause": "原因",
        "solution": "方案",
        "error_code": None,
    }


def _brpc_schema_dict(**overrides) -> dict:
    data = {
        "format_version": 1,
        "schema_id": "a" * 64,
        "nodes": [
            _brpc_node("if-1", "interface"),
            _brpc_node("fm-1", "failure_mode"),
        ],
        "edges": [
            {
                "source_node_id": "if-1",
                "target_node_id": "fm-1",
                "edge_type": "intra_component",
            }
        ],
        "failure_interface_mappings": [
            {
                "failure_mode_id": "fm-1",
                "interface_ids": ["if-1"],
                "subgraph_edge_indexes": [0],
            }
        ],
    }
    data.update(overrides)
    return data


class TestParseBrpcQueryTimestamp:
    def test_non_string_rejected(self):
        """查询时间必须是字符串，其他类型拒绝。"""
        with pytest.raises(ValueError, match="字符串格式"):
            parse_brpc_query_timestamp(1234567890)

    def test_non_padded_time_rejected(self):
        """可解析但不满足零填充格式的时间拒绝。"""
        with pytest.raises(ValueError, match="格式"):
            parse_brpc_query_timestamp("2026-01-01 0:0:0")

    def test_before_epoch_rejected(self):
        """早于 Unix Epoch 的 UTC+8 时间拒绝。"""
        with pytest.raises(ValueError, match="时间不能早于 Unix Epoch"):
            parse_brpc_query_timestamp("1969-12-31 23:59:59")

    def test_epoch_boundary(self):
        """UTC+8 的 1970-01-01 08:00:00 恰好对应 epoch 0。"""
        assert parse_brpc_query_timestamp("1970-01-01 08:00:00") == 0


class TestBrpcDiagSchemaValidation:
    def test_valid_schema(self):
        schema = BrpcDiagSchema(**_brpc_schema_dict())
        assert schema.nodes[0].node_id == "if-1"
        assert schema.failure_interface_mappings[0].failure_mode_id == "fm-1"

    def test_edge_source_not_exist_rejected(self):
        """边的 source 节点不存在时拒绝。"""
        data = _brpc_schema_dict(
            edges=[
                {
                    "source_node_id": "ghost",
                    "target_node_id": "if-1",
                    "edge_type": "intra_component",
                }
            ]
        )
        with pytest.raises(
            ValidationError, match="edge source node does not exist: ghost"
        ):
            BrpcDiagSchema(**data)

    def test_duplicate_edge_rejected(self):
        """完全相同的边重复出现时拒绝。"""
        edge = {
            "source_node_id": "if-1",
            "target_node_id": "fm-1",
            "edge_type": "intra_component",
        }
        with pytest.raises(ValidationError, match="duplicate edge"):
            BrpcDiagSchema(**_brpc_schema_dict(edges=[edge, dict(edge)]))

    def test_mapping_references_non_failure_node_rejected(self):
        """映射的 failure_mode_id 指向非 failure_mode 节点时拒绝。"""
        data = _brpc_schema_dict(
            failure_interface_mappings=[
                {
                    "failure_mode_id": "if-1",
                    "interface_ids": ["if-1"],
                    "subgraph_edge_indexes": [0],
                }
            ]
        )
        with pytest.raises(
            ValidationError,
            match="mapping does not reference a failure_mode node: if-1",
        ):
            BrpcDiagSchema(**data)

    def test_mapping_references_non_interface_node_rejected(self):
        """映射的 interface_ids 包含非 interface 节点时拒绝。"""
        data = _brpc_schema_dict(
            failure_interface_mappings=[
                {
                    "failure_mode_id": "fm-1",
                    "interface_ids": ["fm-1"],
                    "subgraph_edge_indexes": [0],
                }
            ]
        )
        with pytest.raises(
            ValidationError,
            match="mapping does not reference an interface node: fm-1",
        ):
            BrpcDiagSchema(**data)

    def test_defensive_unknown_failure_mode_mapping(self):
        """防御性分支：校验过程中节点状态不一致时报告未知故障模式映射。

        正常数据流中映射引用的 failure_mode 节点必然已在 failure_node_ids
        集合内（167 行校验保证），extra_mappings 恒为空；这里用 node_type
        读取时序不一致的模拟对象触发该防御分支。
        """

        class _InconsistentNode:
            """首次读取 node_type 返回 interface，之后返回 failure_mode。"""

            def __init__(self, node_id):
                self.node_id = node_id
                self._reads = 0

            @property
            def node_type(self):
                self._reads += 1
                return "interface" if self._reads == 1 else "failure_mode"

        class _FakeSchema:
            def __init__(self, nodes, mappings):
                self.nodes = nodes
                self.edges = []
                self.failure_interface_mappings = mappings

        mapping = SimpleNamespace(
            failure_mode_id="fm-1", interface_ids=[], subgraph_edge_indexes=[]
        )
        fake = _FakeSchema([_InconsistentNode("fm-1")], [mapping])
        with pytest.raises(ValueError, match="mappings for unknown failure modes"):
            BrpcDiagSchema.validate_graph(fake)


class TestBrpcDiagBatchValidation:
    def _batch_dict(self, **overrides) -> dict:
        data = {
            "record_type": "batch",
            "format_version": 2,
            "task_id": "task-1",
            "batch_id": "batch-1",
            "schema_id": "a" * 64,
            "created_at_timestamp": 10,
            "start_timestamp": 100,
            "end_timestamp": 200,
            "hit_count": 0,
        }
        data.update(overrides)
        return data

    def test_valid_batch(self):
        batch = BrpcDiagBatch(**self._batch_dict())
        assert batch.task_id == "task-1"
        assert batch.end_timestamp == 200

    def test_end_before_start_rejected(self):
        """end_timestamp 早于 start_timestamp 时拒绝。"""
        with pytest.raises(
            ValidationError,
            match="end_timestamp must not be earlier than start_timestamp",
        ):
            BrpcDiagBatch(**self._batch_dict(end_timestamp=50))
