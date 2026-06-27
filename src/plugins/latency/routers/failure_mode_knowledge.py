# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
    Body,
    File,
    UploadFile,
    HTTPException,
    status,
)
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from typing import Annotated, Optional
import urllib
from httpx import AsyncClient
import os
from latency.schemas.log import LogFileModel
from latency.schemas.request import (
    UpLoadLogFilesRequest,
    UpdateLogFileRequest,
    ListLogFilesRequest,
)
from latency.schemas.response import (
    GetFailureModeMsg,
    GetFailureModeResponse,
    GetStatusCodeKnowledgeResponse,
)
from latency.services.failure_mode_knowledge import FailureModeKnowledge

router = APIRouter(prefix="/failure_mode", tags=["failure_mode"])

@router.get(
    "/status_code/{status_code}",
    response_model=GetStatusCodeKnowledgeResponse,
)
async def get_status_code_knowledge(
    status_code: Annotated[str, Path()],
) -> GetStatusCodeKnowledgeResponse:
    msg = await FailureModeKnowledge.get_status_code_knowledge(status_code)
    if msg.status_code_info is None:
        raise HTTPException(status_code=404, detail=f"未找到故障码 {status_code}")
    return GetStatusCodeKnowledgeResponse(result=msg)


@router.get("/{failure_mode_id}", response_model=GetFailureModeResponse)
async def get_failure_mode_by_id(
    failure_mode_id: Annotated[str, Path()],
) -> GetFailureModeResponse:
    get_failure_mode_msg = await FailureModeKnowledge.get_failure_mode_knowledege_by_id(failure_mode_id)
    return GetFailureModeResponse(result=get_failure_mode_msg)
