"""契约测试：用**前端真实报文**打接口，防止再出现"UI 必然 422 而测试全绿"。

背景（2026-09-14 实测故障）：前端发的是
  {"upload_log_file_configs":[{"name":"…","source_type":"local","source":"/path","log_type":"kv-cache"}]}
后端枚举只认 "KVCache" → 422；而当时的测试恰好断言 "kv-cache 必须被拒"，两处都绿。
"""
import pytest

from latency.ENUM.general import DiagnosisConfigLogType
from latency.schemas.request import UpLoadLogFilesRequest
from latency.services.log_file import _display_name


FRONTEND_PAYLOAD = {
    "upload_log_file_configs": [
        {
            "name": "jingpai-log-sample1-new",
            "source_type": "local",
            "source": "/var/witty-ub/jingpai-log-sample1-new",
            "log_type": "kv-cache",          # ← 前端就是这个写法
        }
    ]
}


def test_frontend_payload_with_hyphenated_log_type_is_accepted():
    """前端报文的 log_type 是 kv-cache，必须被接受并归一化成 KVCache。"""
    req = UpLoadLogFilesRequest.model_validate(FRONTEND_PAYLOAD)
    assert req.upload_log_file_configs[0].log_type is DiagnosisConfigLogType.KVCACHE


def test_frontend_payload_without_name_is_accepted():
    """前端旧构建会丢掉 name 字段（JSON.stringify 吃掉 undefined）—— 不能被它卡成 422。"""
    payload = {"upload_log_file_configs": [{**FRONTEND_PAYLOAD["upload_log_file_configs"][0]}]}
    payload["upload_log_file_configs"][0].pop("name")
    req = UpLoadLogFilesRequest.model_validate(payload)
    assert req.upload_log_file_configs[0].name is None
    # 展示名由来源路径末段兜底（服务层行为）
    assert _display_name(req.upload_log_file_configs[0]) == "jingpai-log-sample1-new"


def test_display_name_prefers_explicit_name():
    req = UpLoadLogFilesRequest.model_validate(FRONTEND_PAYLOAD)
    assert _display_name(req.upload_log_file_configs[0]) == "jingpai-log-sample1-new"


@pytest.mark.parametrize("bad", ["brpc", "Other", ""])
def test_truly_invalid_log_type_still_rejected(bad):
    payload = {"upload_log_file_configs": [
        {**FRONTEND_PAYLOAD["upload_log_file_configs"][0], "log_type": bad}]}
    with pytest.raises(Exception):
        UpLoadLogFilesRequest.model_validate(payload)
