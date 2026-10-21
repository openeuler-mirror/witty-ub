"""Binary regression tests: python3 scripts/tests/test_runtime_multiline.py.

Build witty-ub-diag-tool first, or set WITTY_DIAG_TOOL to the binary to test.
Uses the shipped rules and checks the raw-text join used by trace persistence.
"""

import gzip
import json
import os
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
BINARY = Path(os.environ.get("WITTY_DIAG_TOOL", ROOT / "build/src/witty-ub-diag-tool"))
MODES = (1218, 1219, 1266, 1267, 1396, 1617, 2581)
# Explicit examples, independent of the rule keyword parser.
MESSAGES = {
    1218: "String to int64 failed for abc. invalid argument\n",
    1219: "String to int64 failed at pos 2 for 12x. invalid argument\n",
    1266: "MemoryCopy Failed.\n  target size: 1\n  source size: 2",
    1267: "MemoryCopy Failed: invalid\n  ShmUnitInfo size: 1\n  target size: 2\n  source size: 3",
    1396: "String to int failed, error: invalid argument\n",
    1617: "Query the Objects Global References on Worker 127.0.0.1:1234 Failed.\nRPC unavailable",
    2581: "Worker->Master CloseProducer request failed. Failed producer list: [producer ]\nrc: RPC unavailable",
}


@unittest.skipUnless(BINARY.is_file(), "Build witty-ub-diag-tool or set WITTY_DIAG_TOOL")
class RuntimeMultilineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="witty-multiline-test-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        (self.work / "data").symlink_to(ROOT / "data", target_is_directory=True)
        self.logs = self.work / "input"
        self.logs.mkdir()
        self.rules = {
            item["故障编号"]: item
            for item in json.loads((ROOT / "data/kvcache/kvcache_failure_mode.json").read_text())
        }

    def runtime(self, mode, trace, message=None, time="03:12:35"):
        filename = self.rules[f"kvcache_runtime_{mode:03}"]["文件名"]
        return (
            f"2026-07-17T{time}.100000 | E | {filename}:42 | 172.16.199.143 | "
            f"678:893 | {trace} | test | {MESSAGES[mode] if message is None else message}"
        )

    def access(self, traces):
        (self.logs / "access.log").write_text("\n".join(
            "2026-07-17T03:12:35.000000 | E | access_recorder.cpp:42 | "
            f"172.16.199.143 | 678:893 | {trace} | test | "
            "2 | DS_KV_CLIENT_GET | 100 | 10 | req | invalid"
            for trace in traces
        ) + "\n")

    def run_tool(self, name="result", end="2099-12-31 23:59:59"):
        result = subprocess.run([
            str(BINARY), "--ds-log-path", str(self.logs),
            "--start-time", "2026-07-17 03:00:00", "--end-time", end,
            "--random-str", name,
            "--ds-client-access-log-file", "ds_client_access*.log",
            "--ds-client-info-log-file", "ds_client*.INFO.log",
            "--ds-worker-access-log-file", "access*.log",
            "--ds-worker-info-log-file", "kvcache*.log*",
            "--resource-log-file", "resource.log",
        ], env={**os.environ, "WITTY_DIR": str(self.work)},
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("[ERROR]", result.stdout + result.stderr)
        output = self.work / f"log_{name}"
        extracted = {
            line.strip() for path in output.glob("*.log")
            if path.name != "failure_trace.log" for line in path.read_text().splitlines()
        }
        hits = {}
        for line in (output / "failure_trace.log").read_text().splitlines():
            modes, raw = line.split(" | ", 1)
            # The Python persistence worker joins these two files on stripped raw_text.
            self.assertIn(raw.strip(), extracted)
            trace = raw.split(" | ")[5]
            hits.setdefault(trace, set()).update(modes.split(","))
        return hits, result.stdout

    def test_all_seven_formats_and_cache(self):
        traces = [f"trace-{mode}" for mode in MODES]
        self.access(traces)
        for escaped, crlf, compressed, eof in [
            (False, False, False, False), (False, True, False, False),
            (True, False, False, False), (False, False, True, False),
            (False, True, True, True), (True, False, True, True),
            (False, False, False, True),
        ]:
            with self.subTest(escaped=escaped, crlf=crlf, gzip=compressed, eof=eof):
                text = "\n".join(self.runtime(mode, trace) for mode, trace in zip(MODES, traces))
                if escaped:
                    text = "\n".join(self.runtime(mode, trace, MESSAGES[mode].replace("\n", r"\n"))
                                     for mode, trace in zip(MODES, traces))
                if not eof:
                    text += "\n"
                if crlf:
                    text = text.replace("\n", "\r\n")
                path = self.logs / ("kvcache.INFO.log.gz" if compressed else "kvcache.INFO.log")
                path.write_bytes(gzip.compress(text.encode()) if compressed else text.encode())
                for name in ("cold", "warm"):
                    hits, stdout = self.run_tool(name)
                    for mode, trace in zip(MODES, traces):
                        self.assertIn(f"kvcache_runtime_{mode}", hits.get(trace, set()))
                    if name == "warm":
                        self.assertIn("loaded diagnosis rules from binary cache", stdout)
                path.unlink()

    def test_missing_continuation_and_trace_boundary_do_not_match(self):
        self.access(["first", "second", "incomplete-copy"])
        text = self.runtime(2581, "first", MESSAGES[2581].split("\n")[0])
        text += "\n" + self.runtime(2581, "second", "rc: unrelated error")
        text += "\n" + self.runtime(1266, "incomplete-copy", "MemoryCopy Failed.\n  target size: 1")
        (self.logs / "kvcache.INFO.log").write_text(text)
        hits, _ = self.run_tool()
        for trace, mode in (("first", 2581), ("second", 2581), ("incomplete-copy", 1266)):
            self.assertNotIn(f"kvcache_runtime_{mode}", hits[trace])

    def test_old_keyword_cache_is_rebuilt(self):
        self.access(["cache"])
        (self.logs / "kvcache.INFO.log").write_text(self.runtime(2581, "cache"))
        self.run_tool("initial")
        cache = self.work / "cache/diagnosis_rules_v1.bin"
        content = bytearray(cache.read_bytes())
        content[8:12] = struct.pack("=I", 1)  # Previous keyword semantics.
        cache.write_bytes(content)
        hits, stdout = self.run_tool("rebuilt")
        self.assertNotIn("loaded diagnosis rules from binary cache", stdout)
        self.assertIn("kvcache_runtime_2581", hits["cache"])

    def test_continuations_do_not_cross_files(self):
        self.access(["first"])
        (self.logs / "kvcache1.log").write_text(self.runtime(2581, "first", MESSAGES[2581].split("\n")[0]))
        (self.logs / "kvcache2.log").write_text("rc: unrelated error\n")
        hits, _ = self.run_tool()
        self.assertNotIn("kvcache_runtime_2581", hits["first"])

    def test_time_window_applies_to_record_header(self):
        self.access(["before", "inside", "after"])
        text = "\n".join([
            self.runtime(2581, "before", time="02:59:59"),
            self.runtime(2581, "inside", MESSAGES[2581] + " at 2099-01-01T00:00:00"),
            self.runtime(2581, "after", time="04:00:00"),
        ])
        (self.logs / "kvcache.INFO.log").write_text(text)
        hits, _ = self.run_tool(end="2026-07-17 03:59:59")
        self.assertIn("kvcache_runtime_2581", hits["inside"])
        for trace in ("before", "after"):
            self.assertNotIn("kvcache_runtime_2581", hits[trace])

    def test_gzip_continuation_across_read_buffer(self):
        self.access(["boundary"])
        header = self.runtime(2581, "boundary", MESSAGES[2581].split("\n")[0])
        # The header ends exactly at the 16 MiB gzip buffer boundary; its
        # continuation arrives after that buffer has been erased/reused.
        filler = self.runtime(1396, "ignored", "unrelated ")
        padding = 16 * 1024 * 1024 - len(filler) - len(header) - 2
        text = filler + "x" * padding + "\n" + header + "\nrc: RPC unavailable"
        (self.logs / "kvcache.INFO.log.gz").write_bytes(gzip.compress(text.encode()))
        hits, _ = self.run_tool()
        self.assertIn("kvcache_runtime_2581", hits["boundary"])


if __name__ == "__main__":
    unittest.main()
