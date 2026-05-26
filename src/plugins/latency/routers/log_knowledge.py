# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from re import L

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
from latency.schemas.request import (
    CreateLogKnowledgeRequest,
    UpdateLogKnowledgeRequest,
    ListLogKnowledgeRequest,
)
from latency.schemas.response import (
    CreateLogKnowledgeResponse,
    DeleteLogKnowledgeResponse,
    UpdateLogKnowledgeResponse,
    ListLogKnowledgeResponse,
    GetLogKnowledgeResponse,
)
from latency.services.log_knowledge import LogKnowledgeService

router = APIRouter(prefix="/log_kb", tags=["Knowledge Base"])


@router.post("", response_model=CreateLogKnowledgeResponse)
async def create_log_kb(
    req: Annotated[CreateLogKnowledgeRequest, Body()],
) -> CreateLogKnowledgeResponse:
    create_log_kb_msg = await LogKnowledgeService.create_log_kb(req)
    return CreateLogKnowledgeResponse(result=create_log_kb_msg)


@router.delete("/{kb_id}", response_model=DeleteLogKnowledgeResponse)
async def delete_log_kb_by_kb_id(
    kb_id: Annotated[str, Path()],
) -> DeleteLogKnowledgeResponse:
    delete_log_kb_msg = await LogKnowledgeService.delete_log_kb_by_kb_id(kb_id)
    return DeleteLogKnowledgeResponse(result=delete_log_kb_msg)


@router.put("/{kb_id}", response_model=UpdateLogKnowledgeResponse)
async def update_log_kb(
    kb_id: Annotated[str, Path()],
    req: Annotated[UpdateLogKnowledgeRequest, Body()],
) -> UpdateLogKnowledgeResponse:
    update_log_kb_msg = await LogKnowledgeService.update_log_kb(kb_id, req)
    return UpdateLogKnowledgeResponse(result=update_log_kb_msg)


@router.get("/{kb_id}", response_model=GetLogKnowledgeResponse)
async def get_log_kb_by_kb_id(
    kb_id: Annotated[str, Path()],
) -> GetLogKnowledgeResponse:
    get_log_kb_msg = await LogKnowledgeService.get_log_kb_by_kb_id(kb_id)
    return GetLogKnowledgeResponse(result=get_log_kb_msg)


@router.post("/list", response_model=ListLogKnowledgeResponse)
async def list_log_kbs(
    req: Annotated[ListLogKnowledgeRequest, Body()],
) -> ListLogKnowledgeResponse:

    list_log_kb_msg = await LogKnowledgeService.list_log_kbs(req)
    return ListLogKnowledgeResponse(result=list_log_kb_msg)
