#!/usr/bin/env python3
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# witty-ub is licensed under the Mulan PSL v2.
"""Backfill the knowledge-base link of existing OpenCode sessions.

The web UI stores each conversation's knowledge-base id in two places:

* OpenCode session metadata (durable, server-side, survives browsers);
* the first user prompt prefix (legacy fallback).

Before session metadata was used, older images only had the prompt prefix, and
the browser kept the mapping in localStorage. This script reads the first
matching user prompt from OpenCode's SQLite store and writes the id into
metadata through the local OpenCode HTTP API. It runs in the background after
OpenCode starts, is idempotent, and never rewrites metadata that already has
the key.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_METADATA_KEY = "witty_ub_kb_id"
# Must stay in sync with src/web/src/App.vue.
KB_ID_PATTERN = re.compile(r"^当前(?:页面选中|会话对应)的知识库 ID 是 ([^。]+)。")
LOG_PREFIX = "[opencode-session-migration]"


def log(message):
    print(f"{LOG_PREFIX} {message}", flush=True)


def default_database():
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(data_home, "opencode", "opencode.db")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="http://127.0.0.1:4096")
    parser.add_argument("--database", default=default_database())
    parser.add_argument("--metadata-key", default=DEFAULT_METADATA_KEY)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report matches without patching session metadata",
    )
    return parser.parse_args(argv)


def api_request(server, method, path, body=None):
    payload = None
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        server.rstrip("/") + path,
        data=payload,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8")) if raw else None


def first_prompt_kb_id(database, session_id):
    """Return the first knowledge-base id embedded in a user prompt."""
    try:
        messages = database.execute(
            "SELECT id, data FROM message WHERE session_id = ? "
            "ORDER BY time_created, id LIMIT 100",
            (session_id,),
        ).fetchall()
    except sqlite3.Error:
        return ""

    for message_id, raw_message in messages:
        try:
            message = json.loads(raw_message)
        except (TypeError, ValueError):
            continue
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        try:
            parts = database.execute(
                "SELECT data FROM part WHERE message_id = ? "
                "ORDER BY time_created, id LIMIT 100",
                (message_id,),
            ).fetchall()
        except sqlite3.Error:
            return ""
        for (raw_part,) in parts:
            try:
                part = json.loads(raw_part)
            except (TypeError, ValueError):
                continue
            if not isinstance(part, dict) or part.get("type") != "text":
                continue
            match = KB_ID_PATTERN.match(part.get("text") or "")
            if match:
                return match.group(1).strip()
    return ""


def restore_sessions(server, database, metadata_key, dry_run):
    try:
        sessions = api_request(server, "GET", "/session")
    except (OSError, urllib.error.URLError, ValueError) as error:
        log(f"OpenCode API is unavailable, skipping: {error}")
        return 0

    if not isinstance(sessions, list):
        log("OpenCode /session returned an unexpected payload, skipping")
        return 0

    restored = 0
    failed = 0
    for session in sessions:
        if not isinstance(session, dict):
            continue
        session_id = session.get("id")
        if not session_id or session.get("parentID"):
            continue
        metadata = session.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        if metadata.get(metadata_key):
            continue

        kb_id = first_prompt_kb_id(database, session_id)
        if not kb_id:
            continue

        if dry_run:
            log(f"would restore {session_id} -> {kb_id}")
            restored += 1
            continue

        merged = dict(metadata)
        merged[metadata_key] = kb_id
        path = "/session/" + urllib.parse.quote(str(session_id), safe="")
        try:
            api_request(server, "PATCH", path, {"metadata": merged})
        except (OSError, urllib.error.URLError, ValueError) as error:
            failed += 1
            log(f"failed to restore {session_id}: {error}")
            continue
        restored += 1

    if restored or failed:
        log(f"restored {restored} session(s), {failed} failure(s)")
    else:
        log("no session metadata needed restoring")
    return 0


def main(argv=None):
    args = parse_args(argv)
    if not os.path.isfile(args.database):
        log(f"OpenCode database not found, skipping: {args.database}")
        return 0
    try:
        database = sqlite3.connect(args.database, timeout=5)
    except sqlite3.Error as error:
        log(f"cannot open OpenCode database, skipping: {error}")
        return 0
    try:
        return restore_sessions(
            args.server, database, args.metadata_key, args.dry_run
        )
    finally:
        database.close()


if __name__ == "__main__":
    sys.exit(main())
