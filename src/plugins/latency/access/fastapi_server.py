# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import warnings

# 过滤 APScheduler 中 pkg_resources 弃用警告
warnings.filterwarnings(
    "ignore", message="pkg.resources is deprecated", category=UserWarning
)

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uvicorn
import fastapi
import os
import shutil
import logging
from latency.ENUM.general import FilePath
from latency.config.config import Config
from latency.task.task_handler import TaskHandler
from latency.task.worker import *
from latency.services.failure_mode_knowledge import FailureModeKnowledge
from latency.routers import (
    log_file,
    log_knowledge,
    log_parse_result,
    src_dst_aggregated_event,
    anomalous_event,
    anomalous_event_chain,
    task,
    failure_mode_knowledge,
    log_failure_event_result,
    diagnosis_case,
    diagnosis_config,
)
from latency.database.engine import AsyncSQLiteSingleton

app = fastapi.FastAPI(docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
scheduler = AsyncIOScheduler()

logger = logging.getLogger(__name__)


async def configure():
    app.include_router(log_file.router)
    app.include_router(log_knowledge.router)
    app.include_router(log_parse_result.router)
    app.include_router(src_dst_aggregated_event.router)
    app.include_router(anomalous_event.router)
    app.include_router(anomalous_event_chain.router)
    app.include_router(task.router)
    app.include_router(failure_mode_knowledge.router)
    app.include_router(log_failure_event_result.router)
    app.include_router(diagnosis_case.router)
    app.include_router(diagnosis_config.router)

    web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
    if os.path.isdir(web_dir):
        app.mount("/static", StaticFiles(directory=web_dir), name="static")


@app.get("/")
async def serve_index():
    web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
    index_path = os.path.join(web_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Witty-ub API Server"}


@app.get("/health_check")
async def health_check():
    return {"status": "ok"}


async def mk_dirs():
    latency_dir = os.path.dirname(os.path.dirname(__file__))
    for path in FilePath:
        full_path = os.path.join(latency_dir, path.value)
        if not os.path.exists(full_path):
            os.makedirs(full_path, exist_ok=True)
            logger.info(f"创建目录: {full_path}")


@app.on_event("startup")
async def startup_event():
    await configure()
    await mk_dirs()
    await AsyncSQLiteSingleton().init_database()
    await FailureModeKnowledge().init_failure_mode_knowledge()
    scheduler.add_job(TaskHandler.handle_tasks, "interval", seconds=5)
    scheduler.start()


def main():
    try:
        ssl_enable = Config().get_config().service.ssl_enable
        if ssl_enable:
            uvicorn.run(
                app,
                host=Config().get_config().service.uvicorn_ip,
                port=int(Config().get_config().service.uvicorn_port),
                proxy_headers=True,
                forwarded_allow_ips="*",
                ssl_certfile=Config().get_config().service.ssl_certfile,
                ssl_keyfile=Config().get_config().service.ssl_keyfile,
            )
        else:
            uvicorn.run(
                app,
                host=Config().get_config().service.uvicorn_ip,
                port=int(Config().get_config().service.uvicorn_port),
                proxy_headers=True,
                forwarded_allow_ips="*",
            )
    except Exception as e:
        err = f"启动服务失败: {e}"
        logger.error(err)
        exit(1)


if __name__ == "__main__":
    main()
