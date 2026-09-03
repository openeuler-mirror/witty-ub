# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

from fastapi import APIRouter, Path, Body
from typing import Annotated
from latency.schemas.request import CreateTaskRequest, ListTasksRequest
from latency.schemas.response import (
    CreateTaskResponse,
    StopTaskResponse,
    DeleteTaskResponse,
    ListTasksResponse,
    GetTaskResponse,
)
from latency.services.task import TaskService
from latency.services.resource_id import ResourceIdService

router = APIRouter(prefix="/task", tags=["task"])


@router.post("/create", response_model=CreateTaskResponse)
async def create_task(
    req: Annotated[CreateTaskRequest, Body()],
) -> CreateTaskResponse:
    await ResourceIdService.validate_request(req)
    msg = await TaskService.create_task(req)
    return CreateTaskResponse(result=msg)


@router.put("/stop/{task_id}", response_model=StopTaskResponse)
async def stop_task(
    task_id: Annotated[str, Path()],
) -> StopTaskResponse:
    msg = await TaskService.stop_task(task_id)
    return StopTaskResponse(result=msg)


@router.delete("/{task_id}", response_model=DeleteTaskResponse)
async def delete_task(
    task_id: Annotated[str, Path()],
) -> DeleteTaskResponse:
    msg = await TaskService.delete_task(task_id)
    return DeleteTaskResponse(result=msg)


@router.post(
    "/list",
    response_model=ListTasksResponse,
    operation_id="list_parse_tasks",
    description=(
        "List parsing tasks by knowledge base, status, type or creation time. Use "
        "this to inspect parsing progress when a log file has no direct task ID."
    ),
)
async def list_tasks(
    req: Annotated[ListTasksRequest, Body()],
) -> ListTasksResponse:
    await ResourceIdService.validate_request(req)
    msg = await TaskService.list_tasks(req)
    return ListTasksResponse(result=msg)


@router.get(
    "/{task_id}",
    response_model=GetTaskResponse,
    operation_id="get_parse_task",
    description=(
        "Get one parsing task and its progress, reports and completion status. "
        "Call this before treating empty analysis results as evidence that no "
        "fault exists."
    ),
)
async def get_task_by_id(
    task_id: Annotated[str, Path()],
) -> GetTaskResponse:
    msg = await TaskService.get_task_by_id(task_id)
    return GetTaskResponse(result=msg)
