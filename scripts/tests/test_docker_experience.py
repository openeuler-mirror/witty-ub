"""Execute container startup and health checks with isolated service/HTTP doubles.

Run without Docker or third-party dependencies:
    python3 -m unittest discover -s scripts/tests -p test_docker_experience.py -v
"""

import os
import shlex
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DockerExperienceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.bin = self.work / "bin"
        self.bin.mkdir()
        self.calls = self.work / "calls"
        self.calls.touch()
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "CALLS": str(self.calls),
            "WITTY_DIR": str(self.work),
            "WITTY_BACKEND_URL": "http://remote:9772",
            "PYTHONPATH": "/existing/backend",
            "FAIL_MATCH": "",
            "SYNC_STATUS": "0",
            "WEB_EXIT": "0",
            "READY": str(self.work / "ready"),
            "SERVICE_PID": str(self.work / "service.pid"),
        }
        self._executable(self.bin / "curl", '''#!/bin/bash
echo "curl $*" >> "$CALLS"
if [ -n "$FAIL_MATCH" ] && [[ "$*" == *"$FAIL_MATCH"* ]]; then
    exit 22
fi
''')
        # Only retry delays are replaced; the service uses real sleep via /bin/sleep.
        self._executable(self.bin / "sleep", "#!/bin/sh\nexit 0\n")
        self.scripts = self.work / "witty_ub_diagnostician/.opencode/skills/experience-skill/scripts"
        self.python = self.scripts / ".venv/bin/python"
        self._executable(self.python, '''#!/bin/bash
echo "python cwd=$PWD path=$PYTHONPATH args=$*" >> "$CALLS"
if [ "${3:-}" = "sync" ]; then
    echo "sync log"
    exit "$SYNC_STATUS"
fi
echo "web log"
if [ "$WEB_EXIT" = "1" ]; then exit 33; fi
echo $$ > "$SERVICE_PID"
trap 'echo terminated >> "$CALLS"; exit 0' TERM INT
while :; do /bin/sleep 0.02; done
''')
        entrypoint = (ROOT / "docker/entrypoint.sh").read_text()
        entrypoint = entrypoint.replace("\nload_pg_secret\n", "\n", 1)
        entrypoint = entrypoint.replace("/var/log/witty-ub", str(self.work / "logs"))
        entrypoint = entrypoint.replace(
            "/healthcheck.sh --experience",
            f"bash {shlex.quote(str(ROOT / 'docker/healthcheck.sh'))} --experience",
        )
        # Run the real dispatcher and lifecycle traps, replacing unrelated services.
        marker = "# 清理后台服务"
        doubles = '''
sync_backend_data() { echo data >> "$CALLS"; }
start_nginx() { echo nginx >> "$CALLS"; }
start_backend() { echo backend >> "$CALLS"; }
wait_backend_ready() { echo remote >> "$CALLS"; }
start_opencode() { echo opencode >> "$CALLS"; }
tail() { echo ready > "$READY"; }
'''
        self.entrypoint = self.work / "entrypoint.sh"
        self.entrypoint.write_text(entrypoint.replace(marker, doubles + "\n" + marker, 1))

    @staticmethod
    def _executable(path, contents):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        path.chmod(0o755)

    def _health(self, role="all", fail="", experience_only=False):
        self.calls.write_text("")
        result = subprocess.run(
            ["bash", str(ROOT / "docker/healthcheck.sh")]
            + (["--experience"] if experience_only else []),
            env={**self.env, "WITTY_ROLE": role, "FAIL_MATCH": fail},
            capture_output=True, text=True, timeout=5,
        )
        return result, self.calls.read_text()

    def _run_startup(self, role="frontend", **env):
        return subprocess.run(
            ["bash", str(self.entrypoint)],
            env={**self.env, "WITTY_ROLE": role, **env},
            capture_output=True, text=True, timeout=5,
        )

    def _start_until_ready(self, role):
        self.calls.write_text("")
        self.work.joinpath("ready").unlink(missing_ok=True)
        result = subprocess.Popen(
            ["bash", str(self.entrypoint)],
            env={**self.env, "WITTY_ROLE": role},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        def cleanup():
            if result.poll() is None:
                result.terminate()
            result.communicate(timeout=5)

        self.addCleanup(cleanup)
        deadline = time.monotonic() + 5
        while not self.work.joinpath("ready").exists():
            if result.poll() is not None:
                self.fail(f"Startup failed: {result.communicate()}")
            if time.monotonic() > deadline:
                self.fail("Startup never became ready")
            time.sleep(0.01)
        return result

    def _assert_service_terminated(self):
        deadline = time.monotonic() + 3
        while "terminated" not in self.calls.read_text() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertIn("terminated", self.calls.read_text())

    def test_health_checks_both_apis_for_all_and_frontend(self):
        for role in ("all", "frontend"):
            with self.subTest(role=role):
                result, calls = self._health(role)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("exp_type=SKILL&page_size=1", calls)
                self.assertIn("exp_type=WIKI&page_size=1", calls)
                backend = "remote" if role == "frontend" else "127.0.0.1"
                self.assertIn(f"http://{backend}:9772/health_check", calls)

    def test_either_experience_api_failure_makes_container_unhealthy(self):
        for role in ("all", "frontend"):
            for api in ("exp_type=SKILL", "exp_type=WIKI"):
                with self.subTest(role=role, api=api):
                    result, _ = self._health(role, fail=api)
                    self.assertNotEqual(result.returncode, 0)

    def test_backend_health_does_not_require_experience(self):
        result, calls = self._health("backend", fail="experience_api")
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("experience_api", calls)

    def test_backend_failure_still_makes_container_unhealthy(self):
        for role in ("all", "frontend", "backend"):
            with self.subTest(role=role):
                result, _ = self._health(role, fail="health_check")
                self.assertNotEqual(result.returncode, 0)

    def test_experience_startup_check_does_not_depend_on_backend(self):
        result, calls = self._health(fail="health_check", experience_only=True)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("/health_check", calls)

    def test_all_and_frontend_sync_start_and_forward_shutdown(self):
        for role in ("all", "frontend"):
            with self.subTest(role=role):
                result = self._start_until_ready(role)
                calls = self.calls.read_text()
                self.assertIn("args=-m experience_skill_cli.cli sync", calls)
                self.assertIn(
                    "args=-m experience_skill_cli.cli web --host 127.0.0.1 --port 8082 --no-browser", calls,
                )
                self.assertIn(f"cwd={self.scripts} path={self.scripts}/src:/existing/backend", calls)
                self.assertLess(calls.index("cli sync"), calls.index("cli web"))
                self.assertLess(calls.index("cli web"), calls.index("\nopencode\n"))
                self.assertIn("exp_type=SKILL", calls)
                self.assertIn("exp_type=WIKI", calls)
                log = (self.work / "logs/experience_server.log").read_text()
                self.assertIn("sync log", log)
                self.assertIn("web log", log)
                result.terminate()
                out, err = result.communicate(timeout=5)
                self.assertEqual(result.returncode, 0, out + err)
                self._assert_service_terminated()

    def test_backend_startup_does_not_start_experience(self):
        result = self._run_startup("backend")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("python", self.calls.read_text())

    def test_missing_venv_fails_startup(self):
        self.python.unlink()
        result = self._run_startup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("venv is missing", result.stdout)

    def test_sync_failure_prevents_web_and_opencode_startup(self):
        result = self._run_startup(SYNC_STATUS="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sync failed", result.stdout)
        calls = self.calls.read_text()
        self.assertNotIn("cli web", calls)
        self.assertNotIn("\nopencode\n", calls)

    def test_api_failure_fails_startup_and_cleans_up_service(self):
        result = self._run_startup(FAIL_MATCH="exp_type=WIKI")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed their health check", result.stdout)
        self.assertNotIn("\nopencode\n", self.calls.read_text())
        self._assert_service_terminated()

    def test_web_process_exit_fails_startup(self):
        result = self._run_startup(WEB_EXIT="1", FAIL_MATCH="experience_api")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("web server exited", result.stdout)

    def test_deployment_creates_and_mounts_experience_volume_by_role(self):
        source = (ROOT / "deploy/docker/deploy_witty.sh").read_text()
        volumes = source.split("# 3.2 准备数据卷", 1)[1].split("# 3.3", 1)[0]
        run = source.split("# 3.6 启动容器", 1)[1].split('log_ok "Container', 1)[0]
        harness = '''set -e
log_info() { :; }; log_ok() { :; }
docker() { echo "docker $*" >> "$CALLS"; }
'''
        for role in ("all", "frontend", "backend"):
            with self.subTest(role=role):
                self.calls.write_text("")
                result = subprocess.run(
                    ["bash", "-c", harness + volumes + run],
                    env={**self.env, "ROLE": role, "SELECTED_IMAGE": "test-image"},
                    capture_output=True, text=True, timeout=5,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = self.calls.read_text()
                mount = "-v witty-ub-experience-data:/var/witty-ub/witty_ub_diagnostician/.opencode/skills/experience-skill/data"
                if role in ("all", "frontend"):
                    self.assertIn("docker volume create witty-ub-experience-data", calls)
                    self.assertIn(mount, calls)
                else:
                    self.assertNotIn("witty-ub-experience-data", calls)
                if role in ("all", "backend"):
                    self.assertIn("--health-cmd=/healthcheck.sh", calls)

    def test_experimental_publish_context_includes_current_lifecycle_scripts(self):
        # Execute the actual packager; the Docker double validates its build context.
        web = self.work / "web/dist"
        web.mkdir(parents=True)
        (web / "index.html").write_text("<html></html>")
        self._executable(self.bin / "docker", '''#!/bin/bash
set -e
if [ "$1 $2" = "buildx build" ]; then
    context="${!#}"
    cmp "$context/docker/entrypoint.sh" "$EXPECTED_ROOT/docker/entrypoint.sh"
    cmp "$context/docker/healthcheck.sh" "$EXPECTED_ROOT/docker/healthcheck.sh"
    test -f "$context/dist/index.html"
    grep -q 'root /var/witty-ub/web-exp;' "$context/nginx.conf.template"
    echo validated >> "$CALLS"
fi
''')
        result = subprocess.run(
            ["bash", str(ROOT / "scripts/publish_frontend_exp.sh")],
            env={**self.env, "EXPECTED_ROOT": str(ROOT), "BASE_RELEASE": "test-release",
                 "EXP_SOURCE_DIR": str(web.parent), "SKIP_BUILD": "1", "PUSH": "0",
                 "KEEP_CONTEXT": "0", "TMPDIR": str(self.work)},
            capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("validated", self.calls.read_text())


if __name__ == "__main__":
    unittest.main()
