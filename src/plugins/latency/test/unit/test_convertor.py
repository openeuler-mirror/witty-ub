# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""latency.common.convertor 单元测试。"""
from latency.common.convertor import Convertor
from latency.schemas.request import CreateLogKnowledgeRequest


class TestCreateLogKbReqToLogKbModel:
    async def test_basic_conversion(self):
        req = CreateLogKnowledgeRequest(name="kb-name", description="kb-desc")
        model = await Convertor.create_log_kb_req_to_log_kb_model(req)
        assert model.name == "kb-name"
        assert model.description == "kb-desc"

    async def test_none_image_bytes_becomes_empty(self):
        req = CreateLogKnowledgeRequest(name="n", description="d", image_bytes=None)
        model = await Convertor.create_log_kb_req_to_log_kb_model(req)
        assert model.image_bytes == b""

    async def test_image_bytes_preserved(self):
        req = CreateLogKnowledgeRequest(name="n", description="d", image_bytes=b"\x01\x02")
        model = await Convertor.create_log_kb_req_to_log_kb_model(req)
        assert model.image_bytes == b"\x01\x02"

    async def test_model_defaults(self):
        req = CreateLogKnowledgeRequest(name="n", description="d")
        model = await Convertor.create_log_kb_req_to_log_kb_model(req)
        assert model.task_cnt == 0
        assert model.log_file_cnt == 0
        assert model.anomaly_cnt == 0
        assert model.existed_status is True
        assert model.id  # uuid 默认生成
