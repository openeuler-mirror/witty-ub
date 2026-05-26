# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import argparse
import asyncio
import logging

from latency.task.task_handler import TaskHandler
from latency.ENUM.task import TaskTypeEnum

logger = logging.getLogger(__name__)


class ShellServer:
    """Shell 命令行入口"""

    @staticmethod
    async def run(args):
        if args.command == "init_task":
            task_id = await TaskHandler.init_task(
                TaskTypeEnum.KV_CACHE_LOG_PARSE_WORKER, args.op_id
            )
            print(f"Task initialized: {task_id}")
        elif args.command == "stop_task":
            result = await TaskHandler.stop_task(args.task_id)
            print(f"Task stopped: {result}")
        elif args.command == "delete_task":
            result = await TaskHandler.delete_task(args.task_id)
            print(f"Task deleted: {result}")
        else:
            print(f"Unknown command: {args.command}")


def main():
    parser = argparse.ArgumentParser(description="Latency Plugin Shell Server")
    parser.add_argument("command", choices=["init_task", "stop_task", "delete_task"])
    parser.add_argument("--op_id", default="", help="Operation ID for init_task")
    parser.add_argument("--task_id", default="", help="Task ID for stop/delete")
    args = parser.parse_args()
    asyncio.run(ShellServer.run(args))


if __name__ == "__main__":
    main()
