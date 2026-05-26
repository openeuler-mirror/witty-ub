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
    UploadLogFilesResponse,
    DeleteLogFilesResponse,
    UpdateLogFileResponse,
    ListLogFilesResponse,
    GetLogFileResponse,
)
from latency.services.log_file import LogFileService

router = APIRouter(prefix="/log_file", tags=["log_file"])


@router.post("/{kb_id}", response_model=UploadLogFilesResponse)
async def upload_log_files(
    kb_id: Annotated[str, Path()],
    req: Annotated[UpLoadLogFilesRequest, Body()],
) -> UploadLogFilesResponse:
    upload_log_files_msg = await LogFileService.upload_log_files(kb_id, req)
    return UploadLogFilesResponse(message=upload_log_files_msg)


@router.delete("/{log_file_id}", response_model=DeleteLogFilesResponse)
async def delete_log_file_by_log_file_id(
    log_file_id: Annotated[str, Path()],
) -> DeleteLogFilesResponse:
    delete_log_files_msg = await LogFileService.delete_log_file_by_log_file_id(
        log_file_id
    )
    return DeleteLogFilesResponse(message=delete_log_files_msg)


@router.put("/{log_file_id}", response_model=UpdateLogFileResponse)
async def update_log_file(
    log_file_id: Annotated[str, Path()],
    req: Annotated[UpdateLogFileRequest, Body()],
) -> UpdateLogFileResponse:
    update_log_file_msg = await LogFileService.update_log_file(log_file_id, req)
    return UpdateLogFileResponse(message=update_log_file_msg)


@router.put("/run/{log_file_id}", response_model=UpdateLogFileResponse)
async def run_or_stop_log_file_by_log_file_id(
    log_file_id: Annotated[str, Path()],
    run: Annotated[bool, Query(description="是否运行日志文件，默认为true")] = True,
) -> UpdateLogFileResponse:
    update_log_file_msg = await LogFileService.run_or_stop_log_parse_by_log_file_id(
        log_file_id, run
    )
    return UpdateLogFileResponse(message=update_log_file_msg)


@router.post("/list/{kb_id}", response_model=ListLogFilesResponse)
async def list_log_files(
    kb_id: Annotated[str, Path()],
    req: Annotated[ListLogFilesRequest, Body()],
) -> ListLogFilesResponse:
    list_log_files_msg = await LogFileService.list_log_files(kb_id, req)
    return ListLogFilesResponse(result=list_log_files_msg)


@router.get("/{log_file_id}", response_model=GetLogFileResponse)
async def get_log_file_by_log_file_id(
    log_file_id: Annotated[str, Path()],
) -> GetLogFileResponse:
    get_log_file_msg = await LogFileService.get_log_file_by_log_file_id(log_file_id)
    return GetLogFileResponse(result=get_log_file_msg)
