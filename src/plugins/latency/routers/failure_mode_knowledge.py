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
    operation_id="get_status_code_knowledge",
    description=(
        "Explain a connectivity status code using the curated fault knowledge "
        "base. A not-found response means the code is unknown, not that the event "
        "is healthy."
    ),
)
async def get_status_code_knowledge(
    status_code: Annotated[str, Path()],
) -> GetStatusCodeKnowledgeResponse:
    msg = await FailureModeKnowledge.get_status_code_knowledge(status_code)
    if msg.status_code_info is None:
        raise HTTPException(status_code=404, detail=f"未找到故障码 {status_code}")
    return GetStatusCodeKnowledgeResponse(result=msg)


@router.get(
    "/{failure_mode_id}",
    response_model=GetFailureModeResponse,
    operation_id="get_failure_mode",
    description=(
        "Get a complete curated failure mode by ID, including symptom, root cause, "
        "solution, failure domain and child failure-mode relationships."
    ),
)
async def get_failure_mode_by_id(
    failure_mode_id: Annotated[str, Path()],
) -> GetFailureModeResponse:
    get_failure_mode_msg = (
        await FailureModeKnowledge.get_failure_mode_knowledege_by_id(failure_mode_id)
    )
    if get_failure_mode_msg.failure_mode is None:
        raise HTTPException(status_code=404, detail=f"未找到故障模式 {failure_mode_id}")
    return GetFailureModeResponse(result=get_failure_mode_msg)
