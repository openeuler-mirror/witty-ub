# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import warnings

# 过滤 APScheduler 中 pkg_resources 弃用警告
warnings.filterwarnings(
    "ignore", message="pkg_resources is deprecated", category=UserWarning
)

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uvicorn
import fastapi
import os
import shutil
import logging
from latency.ENUM.general import FilePath
from latency.config.config import Config
from latency.task.task_handle import TaskHandler
from latency.routers import log_file
from latency.database.engine import AsyncSQLiteSingleton

app = fastapi.FastAPI(docs_url=None, redoc_url=None)
scheduler = AsyncIOScheduler()

logger = logging.getLogger(__name__)


async def configure():
    app.include_router(log_file.router)


@app.get("/health_check")
async def health_check():
    return {"status": "ok"}


async def mk_dirs():
    for path in FilePath:
        if not os.path.exists(path.value):
            os.makedirs(path.value)
            logger.info(f"创建目录: {path.value}")


@app.on_event("startup")
async def startup_event():
    await configure()
    await mk_dirs()
    await AsyncSQLiteSingleton.init_database()
    scheduler.add_job(TaskHandler.handle_tasks, "interval", seconds=5)
    scheduler.start()


def main():
    try:
        ssl_enable = Config().get_config().run_config.ssl_enable
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
