#!/usr/bin/env python3
"""Strictly map categorized log names to dataset directories and import them.

Asset libraries are created up front.  Log directories are then submitted one
at a time, and the next directory is not submitted until the current one has
reached a terminal state.  This keeps the backend parse queue bounded.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests


TERMINAL_STATUSES = {"successful", "successful_pending_remove", "failed", "cancelled"}
SUCCESS_STATUSES = {"successful", "successful_pending_remove"}
DIRECTORY_PATTERN = re.compile(
    r"^lingqu_kvcache(?:_dfx)?_(?P<body>.+?)_\d{3}_\d{8}_\d{2}_\d{2}_\d{2}$"
)


class ApiClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.trust_env = False

    def call(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(1, 6):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                response.raise_for_status()
                payload = response.json()
                if "code" not in payload:
                    return payload
                if payload.get("code") != 200:
                    raise RuntimeError(f"API error for {method} {path}: {payload}")
                return payload.get("result") or {}
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                last_error = exc
                if attempt == 5:
                    break
                time.sleep(min(attempt * 2, 10))
        raise RuntimeError(f"request failed after retries: {method} {path}: {last_error}")


def strict_directory_map(
    category_file: Path, dataset_root: Path, start_name: str
) -> tuple[list[str], dict[str, list[Path]]]:
    categories = json.loads(category_file.read_text(encoding="utf-8"))
    try:
        start_index = next(
            index for index, item in enumerate(categories) if item["log_name"] == start_name
        )
    except StopIteration as exc:
        raise RuntimeError(f"start log_name not found: {start_name}") from exc

    names = [item["log_name"] for item in categories[start_index:]]
    parsed_directories: list[tuple[Path, str]] = []
    for path in sorted(dataset_root.iterdir(), key=lambda item: item.name):
        if not path.is_dir():
            continue
        match = DIRECTORY_PATTERN.fullmatch(path.name)
        if match:
            parsed_directories.append((path, match.group("body")))

    mapping = {
        name: [
            path
            for path, body in parsed_directories
            if body == name or body == f"{name}_fault"
        ]
        for name in names
    }
    missing = [name for name, paths in mapping.items() if not paths]
    if missing:
        raise RuntimeError(f"strict mapping has unmatched log_name values: {missing}")

    owners: dict[Path, list[str]] = {}
    for name, paths in mapping.items():
        for path in paths:
            owners.setdefault(path, []).append(name)
    collisions = {str(path): values for path, values in owners.items() if len(values) > 1}
    if collisions:
        raise RuntimeError(f"strict mapping assigned directories more than once: {collisions}")
    return names, mapping


def list_assets(api: ApiClient) -> dict[str, dict[str, Any]]:
    result = api.call(
        "POST",
        "/log_kb/list",
        json={"created_sorted_desc": True, "page_cnt": 1000, "page_num": 1},
    )
    return {
        item["name"]: item
        for item in result.get("kbs", [])
        if item.get("existed_status", True)
    }


def ensure_assets(api: ApiClient, names: list[str]) -> dict[str, str]:
    assets = list_assets(api)
    ids: dict[str, str] = {}
    for index, name in enumerate(names, 1):
        existing = assets.get(name)
        if existing:
            kb_id = existing["id"]
            if existing.get("description") != name:
                api.call("PUT", f"/log_kb/{kb_id}", json={"description": name})
            action = "existing"
        else:
            result = api.call("POST", "/log_kb", json={"name": name, "description": name})
            kb_id = result["kb_id"]
            action = "created"
        ids[name] = kb_id
        print(f"[asset {index:03d}/{len(names)}] {action}: {name} -> {kb_id}", flush=True)
    return ids


def list_log_files(api: ApiClient, kb_id: str) -> list[dict[str, Any]]:
    first = api.call(
        "POST",
        f"/log_file/list/{kb_id}",
        json={"created_sorted_desc": True, "page_cnt": 1000, "page_num": 1},
    )
    return first.get("log_files", [])


def get_log_file(api: ApiClient, log_file_id: str) -> dict[str, Any]:
    result = api.call("GET", f"/log_file/{log_file_id}")
    log_file = result.get("log_file")
    if not log_file:
        raise RuntimeError(f"log file disappeared: {log_file_id}")
    return log_file


def wait_for_terminal(
    api: ApiClient, log_file_id: str, poll_seconds: float
) -> tuple[str, float]:
    last_snapshot: tuple[str, int] | None = None
    while True:
        item = get_log_file(api, log_file_id)
        status = item.get("overall_status", "unknown")
        progress = float(item.get("overall_progress") or 0.0)
        snapshot = (status, int(progress))
        if snapshot != last_snapshot:
            print(
                f"    status={status} progress={progress:.1f}% id={log_file_id}",
                flush=True,
            )
            last_snapshot = snapshot
        if status in TERMINAL_STATUSES:
            return status, progress
        time.sleep(poll_seconds)


def import_directories(
    api: ApiClient,
    names: list[str],
    mapping: dict[str, list[Path]],
    asset_ids: dict[str, str],
    poll_seconds: float,
) -> tuple[int, int, int]:
    submitted = 0
    succeeded = 0
    failed = 0
    total = sum(len(mapping[name]) for name in names)

    for name in names:
        kb_id = asset_ids[name]
        existing_by_path = {
            item.get("file_path"): item for item in list_log_files(api, kb_id)
        }
        for path in mapping[name]:
            submitted += 1
            existing = existing_by_path.get(str(path))
            if existing:
                log_file_id = existing["id"]
                print(
                    f"[parse {submitted:03d}/{total}] resume: {name} <- {path.name}",
                    flush=True,
                )
            else:
                print(
                    f"[parse {submitted:03d}/{total}] submit: {name} <- {path.name}",
                    flush=True,
                )
                result = api.call(
                    "POST",
                    f"/log_file/{kb_id}",
                    json={
                        "upload_log_file_configs": [
                            {
                                "name": path.name,
                                "source_type": "local",
                                "source": str(path),
                                "log_type": "KVCache",
                            }
                        ]
                    },
                )
                ids = result.get("log_file_ids") or []
                if len(ids) != 1:
                    raise RuntimeError(f"unexpected upload response for {path}: {result}")
                log_file_id = ids[0]

            status, _ = wait_for_terminal(api, log_file_id, poll_seconds)
            if status in SUCCESS_STATUSES:
                succeeded += 1
                print(f"    complete: {path.name}", flush=True)
            else:
                failed += 1
                print(f"    terminal failure ({status}): {path.name}", flush=True)
    return submitted, succeeded, failed


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:9772")
    parser.add_argument("--category-file", type=Path, default=project_root / "日志分类.json")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("/home/witty-ub-logs/yxh_new_1022-train"),
    )
    parser.add_argument("--start-name", default="coordinator_cluster_exit")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--request-timeout", type=float, default=120.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api = ApiClient(args.api, args.request_timeout)
    health = api.call("GET", "/health_check")
    print(f"health: {health or 'ok'}", flush=True)

    names, mapping = strict_directory_map(
        args.category_file.resolve(), args.dataset_root.resolve(), args.start_name
    )
    directory_count = sum(len(paths) for paths in mapping.values())
    print(
        f"strict mapping: assets={len(names)} directories={directory_count} "
        f"multi_sample_assets={sum(len(paths) > 1 for paths in mapping.values())}",
        flush=True,
    )

    asset_ids = ensure_assets(api, names)
    submitted, succeeded, failed = import_directories(
        api, names, mapping, asset_ids, args.poll_seconds
    )
    print(
        f"finished: assets={len(asset_ids)} directories={submitted} "
        f"successful={succeeded} failed={failed}",
        flush=True,
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
