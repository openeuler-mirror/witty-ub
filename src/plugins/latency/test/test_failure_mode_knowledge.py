import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from latency.database.managers.failure_mode_knowledge import (
    FailureModeKnowledgePGManager,
)
from latency.routers.failure_mode_knowledge import get_failure_mode_by_id
from latency.schemas.response import GetFailureModeMsg
from latency.services.failure_mode_knowledge import FailureModeKnowledge


REPO_ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.asyncio
async def test_init_failure_mode_knowledge_reads_current_data_files(monkeypatch) -> None:
    captured_failure_modes = {}
    captured_status_codes = {}

    async def capture_failure_modes(items):
        captured_failure_modes.update({item.id: item for item in items})
        return [item.id for item in items]

    async def capture_status_codes(items):
        captured_status_codes.update({item.status_code: item for item in items})
        return [item.status_code for item in items]

    monkeypatch.setenv("WITTY_DIR", str(REPO_ROOT))
    monkeypatch.setattr(
        FailureModeKnowledgePGManager,
        "add_failure_mode_knowledge",
        capture_failure_modes,
    )
    monkeypatch.setattr(
        FailureModeKnowledgePGManager,
        "add_status_code_knowledge",
        capture_status_codes,
    )

    loaded = await FailureModeKnowledge.init_failure_mode_knowledge()

    with (REPO_ROOT / "data/kvcache/kvcache_failure_mode.json").open(
        encoding="utf-8"
    ) as file:
        kvcache_count = len(json.load(file))
    with (REPO_ROOT / "data/urma/urma_failure_mode.json").open(
        encoding="utf-8"
    ) as file:
        urma_count = len(json.load(file))
    with (REPO_ROOT / "data/kvcache/kvcache_error_code_info.json").open(
        encoding="utf-8"
    ) as file:
        status_code_count = len(json.load(file))
    with (REPO_ROOT / "data/failure_mode_tree.json").open(encoding="utf-8") as file:
        failure_mode_tree = json.load(file)

    assert len(loaded) == kvcache_count + urma_count + 1
    assert len(captured_status_codes) == status_code_count

    kvcache_mode = captured_failure_modes["kvcache_access_001"]
    assert kvcache_mode.name == "重复操作"
    assert kvcache_mode.failure_domain == "用户"
    assert kvcache_mode.error_code == "K_DUPLICATED(1)"
    assert kvcache_mode.children_failure_mode_ids == ",".join(
        failure_mode_tree["kvcache"][kvcache_mode.id]
    )

    kvcache_ok_with_message_mode = captured_failure_modes["kvcache_access_034"]
    assert kvcache_ok_with_message_mode.error_code == "K_OK(0)"
    assert captured_status_codes["0"].symptom.startswith("请求返回K_OK")

    urma_mode = captured_failure_modes["urma_001"]
    assert urma_mode.name == "执行初始化URMA资源时失败"
    assert urma_mode.error_code is None
    assert "urma_328" in urma_mode.children_failure_mode_ids.split(",")

    urma_int_mode = captured_failure_modes["urma_131"]
    assert urma_int_mode.error_code == "-1"

    assert captured_failure_modes["kvcache_failure_unknown"].name == "未知故障"
    assert captured_failure_modes["kvcache_failure_unknown"].error_code is None
    assert captured_status_codes["1"].symptom.startswith("请求返回K_DUPLICATED")


@pytest.mark.asyncio
async def test_get_failure_mode_returns_404_when_detail_is_missing(monkeypatch) -> None:
    async def get_missing_failure_mode(_failure_mode_id: str) -> GetFailureModeMsg:
        return GetFailureModeMsg(failure_mode=None)

    monkeypatch.setattr(
        FailureModeKnowledge,
        "get_failure_mode_knowledege_by_id",
        get_missing_failure_mode,
    )

    with pytest.raises(HTTPException) as error:
        await get_failure_mode_by_id("missing-mode")

    assert error.value.status_code == 404
    assert error.value.detail == "未找到故障模式 missing-mode"
