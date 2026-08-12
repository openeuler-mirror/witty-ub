# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
    Body,
    File,
    UploadFile,
    Request,
    HTTPException,
    status,
)
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from typing import Annotated, Optional
import urllib
import json
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
    RunOrStopLogParseResponse,
    ListLogFilesResponse,
    GetLogFileResponse,
)
from latency.services.log_file import LogFileService

router = APIRouter(prefix="/log_file", tags=["log_file"])


@router.post("/{kb_id}", response_model=UploadLogFilesResponse)
async def upload_log_files(
    kb_id: Annotated[str, Path()],
    request: Request,
) -> UploadLogFilesResponse:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        raw_configs = form.get("upload_log_file_configs")
        if not isinstance(raw_configs, str):
            raise HTTPException(status_code=400, detail="缺少上传文件配置")

        try:
            configs = json.loads(raw_configs)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="上传文件配置不是有效JSON") from exc

        uploaded_files = form.getlist("file")
        file_index = 0
        for config in configs:
            if config.get("source_type") != "upload":
                continue
            if file_index >= len(uploaded_files):
                raise HTTPException(status_code=400, detail="缺少上传文件")
            uploaded_file = uploaded_files[file_index]
            file_index += 1
            if not hasattr(uploaded_file, "read") or not hasattr(uploaded_file, "filename"):
                raise HTTPException(status_code=400, detail="上传文件格式不正确")
            config["name"] = config.get("name") or uploaded_file.filename
            config["source"] = uploaded_file

        payload = {"upload_log_file_configs": configs}
        raw_parse_config = form.get("parse_config")
        if isinstance(raw_parse_config, str) and raw_parse_config.strip():
            try:
                payload["parse_config"] = json.loads(raw_parse_config)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail="解析配置不是有效JSON") from exc
        try:
            req = UpLoadLogFilesRequest.model_validate(payload)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors())
    else:
        try:
            req = UpLoadLogFilesRequest.model_validate(await request.json())
        except ValidationError as exc:
            raise RequestValidationError(exc.errors())

    upload_log_files_msg = await LogFileService.upload_log_files(kb_id, req)
    return UploadLogFilesResponse(result=upload_log_files_msg)


@router.delete("/{log_file_id}", response_model=DeleteLogFilesResponse)
async def delete_log_file_by_log_file_id(
    log_file_id: Annotated[str, Path()],
) -> DeleteLogFilesResponse:
    delete_log_files_msg = await LogFileService.delete_log_file_by_log_file_id(
        log_file_id
    )
    return DeleteLogFilesResponse(result=delete_log_files_msg)


@router.put("/{log_file_id}", response_model=UpdateLogFileResponse)
async def update_log_file(
    log_file_id: Annotated[str, Path()],
    req: Annotated[UpdateLogFileRequest, Body()],
) -> UpdateLogFileResponse:
    update_log_file_msg = await LogFileService.update_log_file(log_file_id, req)
    return UpdateLogFileResponse(result=update_log_file_msg)


@router.put("/run/{log_file_id}", response_model=RunOrStopLogParseResponse)
async def run_or_stop_log_file_by_log_file_id(
    log_file_id: Annotated[str, Path()],
    run: Annotated[bool, Query(description="是否运行日志文件，默认为true")] = True,
) -> RunOrStopLogParseResponse:
    update_log_file_msg = await LogFileService.run_or_stop_log_parse_by_log_file_id(
        log_file_id, run
    )
    return RunOrStopLogParseResponse(result=update_log_file_msg)


@router.post(
    "/list/{kb_id}",
    response_model=ListLogFilesResponse,
    operation_id="list_log_files",
    description=(
        "List log files in a knowledge base. Use this to discover log IDs, parse "
        "status, task IDs and fault counts. A non-successful parse status means "
        "downstream results may be incomplete."
    ),
)
async def list_log_files(
    kb_id: Annotated[str, Path()],
    req: Annotated[ListLogFilesRequest, Body()],
) -> ListLogFilesResponse:
    list_log_files_msg = await LogFileService.list_log_files(kb_id, req)
    return ListLogFilesResponse(result=list_log_files_msg)


@router.get(
    "/{log_file_id}",
    response_model=GetLogFileResponse,
    operation_id="get_log_file",
    description=(
        "Get one log file by ID, including its knowledge base, source, parse "
        "status, task information and fault statistics."
    ),
)
async def get_log_file_by_log_file_id(
    log_file_id: Annotated[str, Path()],
) -> GetLogFileResponse:
    get_log_file_msg = await LogFileService.get_log_file_by_log_file_id(log_file_id)
    return GetLogFileResponse(result=get_log_file_msg)
