"""Verify the container startup backfill for OpenCode session metadata.

Run without Docker or third-party dependencies:
    python3 -m unittest discover -s scripts/tests -p test_docker_opencode_migration.py -v
"""

import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "docker/migrate_opencode_sessions.py"


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, value):
        payload = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/session":
            self._json(self.server.sessions)
            return
        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        session_id = self.path.rsplit("/", 1)[-1]
        session = next(item for item in self.server.sessions if item["id"] == session_id)
        session["metadata"] = body["metadata"]
        self.server.patches.append((session_id, body))
        self._json(session)


class OpenCodeSessionMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.database = self.work / "opencode.db"
        connection = sqlite3.connect(self.database)
        connection.executescript(
            """
            CREATE TABLE message (
                id TEXT, session_id TEXT, time_created INTEGER, data TEXT
            );
            CREATE TABLE part (
                id TEXT, message_id TEXT, session_id TEXT,
                time_created INTEGER, data TEXT
            );
            """
        )
        self._add_message(
            "ses_a", "msg_a", "user",
            "当前会话对应的知识库 ID 是 kb-a。\n\n问题 A",
        )
        self._add_message("ses_d", "msg_d", "user", "没有知识库前缀的问题")
        connection.commit()
        connection.close()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.server.sessions = [
            {"id": "ses_a", "metadata": {"other": "keep"}},
            {"id": "ses_b", "metadata": {"witty_ub_kb_id": "kb-b"}},
            {"id": "ses_c", "parentID": "ses_a", "metadata": {}},
            {"id": "ses_d", "metadata": {}},
        ]
        self.server.patches = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def _add_message(self, session_id, message_id, role, text):
        connection = sqlite3.connect(self.database)
        connection.execute(
            "INSERT INTO message VALUES (?, ?, ?, ?)",
            (message_id, session_id, 1, json.dumps({"role": role})),
        )
        connection.execute(
            "INSERT INTO part VALUES (?, ?, ?, ?, ?)",
            (
                f"prt_{message_id}",
                message_id,
                session_id,
                1,
                json.dumps({"type": "text", "text": text}, ensure_ascii=False),
            ),
        )
        connection.commit()
        connection.close()

    def _run(self, *extra):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--server", self.url,
                "--database", str(self.database),
                *extra,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_backfills_only_sessions_that_need_it_and_preserves_metadata(self):
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            self.server.patches,
            [
                (
                    "ses_a",
                    {"metadata": {"other": "keep", "witty_ub_kb_id": "kb-a"}},
                )
            ],
        )
        self.assertIn("restored 1 session(s)", result.stdout)

    def test_second_run_is_idempotent(self):
        self.assertEqual(self._run().returncode, 0)
        self.server.patches.clear()
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.server.patches, [])
        self.assertIn("no session metadata needed restoring", result.stdout)

    def test_dry_run_does_not_patch(self):
        result = self._run("--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.server.patches, [])
        self.assertIn("would restore ses_a -> kb-a", result.stdout)


if __name__ == "__main__":
    unittest.main()
