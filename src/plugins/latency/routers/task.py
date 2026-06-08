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

router = APIRouter(prefix="/task", tags=["task"])


@router.post("/create", response_model=CreateTaskResponse)
async def create_task(
    req: Annotated[CreateTaskRequest, Body()],
) -> CreateTaskResponse:
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


@router.post("/list", response_model=ListTasksResponse)
async def list_tasks(
    req: Annotated[ListTasksRequest, Body()],
) -> ListTasksResponse:
    msg = await TaskService.list_tasks(req)
    return ListTasksResponse(result=msg)


@router.get("/{task_id}", response_model=GetTaskResponse)
async def get_task_by_id(
    task_id: Annotated[str, Path()],
) -> GetTaskResponse:
    msg = await TaskService.get_task_by_id(task_id)
    return GetTaskResponse(result=msg)