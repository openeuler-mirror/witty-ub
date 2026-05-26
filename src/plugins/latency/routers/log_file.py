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

from latency.schemas.response import UploadLogFilesResponse
from latency.services.log_file import LogFileService

router = APIRouter(prefix="/log_file", tags=["log_file"])


@router.post("/{kb_id}", response_model=UploadLogFilesResponse)
async def upload_log_files(
    kb_id: Annotated[str, Path(description="知识库ID")],
) -> UploadLogFilesResponse:
    upload_log_files_msg = await LogFileService.upload_log_files(kb_id)
    return UploadLogFilesResponse(message=upload_log_files_msg)
