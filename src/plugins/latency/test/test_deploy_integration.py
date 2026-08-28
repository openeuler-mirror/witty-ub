"""Deployment-layer integration tests for deploy/*.sh + deploy.conf.

Covers bash syntax, deploy.conf parsing, deploy_pg.sh modes, deploy.sh
OS detection and function behaviour, directory layout, plus end-to-end
pipeline.

Usage:
    cd src/plugins/latency
    PYTHONPATH=$(pwd)/../.. python -m pytest test/test_deploy_integration.py -v
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_DEPLOY_DIR = _PROJECT_ROOT / "deploy"

# ── helpers ───────────────────────────────────────────────────


def _bash(*args: str, **kwargs: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", " ".join(args)],
        capture_output=True,
        text=True,
        timeout=30,
        **({"env": {**os.environ, **kwargs}} if kwargs else {}),
    )


# ──────────────────────────────────────────────────────────────


class TestDeploySyntax:
    """bash -n on all deploy scripts."""

    @pytest.mark.parametrize(
        "script",
        ["host/deploy.sh", "deploy_pg.sh", "docker/deploy_witty.sh", "docker/manage.sh"],
    )
    def test_syntax(self, script):
        r = subprocess.run(["bash", "-n", str(_DEPLOY_DIR / script)], capture_output=True, text=True)
        assert r.returncode == 0, f"{script} syntax error:\n{r.stderr}"


class TestDeployConf:
    """deploy/deploy.conf validation."""

    def test_sourceable(self):
        r = _bash(f"source {_DEPLOY_DIR}/deploy.conf && echo $PG_HOST")
        assert r.returncode == 0, f"deploy.conf source failed:\n{r.stderr}"
        assert "127.0.0.1" in r.stdout

    def test_required_fields(self):
        r = _bash(f"source {_DEPLOY_DIR}/deploy.conf && echo $PG_HOST $PG_PORT $PG_DATABASE $PG_USER")
        parts = r.stdout.strip().split()
        assert parts[0] == "127.0.0.1"
        assert parts[1] == "15432"
        assert parts[2] == "witty-ub"
        assert parts[3] == "witty-ub"


class TestDeployPgSh:
    """deploy/deploy_pg.sh mode flags and --help."""

    def test_help_shows_all_modes(self):
        r = _bash(f"bash {_DEPLOY_DIR}/deploy_pg.sh --help")
        out = r.stdout + r.stderr
        assert "--apt" in out
        assert "--rpm" in out
        assert "--docker" in out
        assert "deploy.conf" in out

    def test_deploy_apt_function_exists(self):
        src = (_DEPLOY_DIR / "deploy_pg.sh").read_text()
        assert "deploy_apt()" in src
        assert "pg_createcluster" in src
        assert "pg_lsclusters" in src

    def test_entry_point_dispatches_apt(self):
        src = (_DEPLOY_DIR / "deploy_pg.sh").read_text()
        assert 'DEPLOY_MODE="apt"' in src or "deploy_apt" in src.split(";;")[-1]


class TestDeploySh:
    """deploy/host/deploy.sh behaviour."""

    def test_help_output(self):
        r = _bash(f"bash {_DEPLOY_DIR}/host/deploy.sh --help")
        out = r.stdout + r.stderr
        assert r.returncode == 0
        assert "witty-ub" in out

    @pytest.mark.skipif(not Path("/etc/os-release").exists(), reason="_lib.sh 仅支持 openEuler/Ubuntu")
    def test_os_detection_functions(self):
        inner = (
            "set +eu; source " + str(_DEPLOY_DIR / "host" / "_lib.sh")
            + "; set +eu; "
            + "detect_os 2>/dev/null && echo OS=$OS_ID; "
            + "_is_root && echo IS_ROOT || echo NOT_ROOT; "
            + "_has_cmd bash && echo HAS_BASH; "
            + "! _has_cmd noop_xyz 2>/dev/null && echo NO_FAKE; "
            + "echo DONE"
        )
        r = _bash(inner)
        out = r.stdout + r.stderr
        assert "OS=" in out
        assert "NOT_ROOT" in out
        assert "HAS_BASH" in out
        assert "NO_FAKE" in out
        assert "DONE" in out

    @pytest.mark.skipif(not Path("/etc/os-release").exists(), reason="_lib.sh 仅支持 openEuler/Ubuntu")
    def test_check_node_accepts_current_version(self):
        inner = (
            "set +eu; source " + str(_DEPLOY_DIR / "host" / "_lib.sh")
            + "; set +eu; "
            + "_check_node 2>&1"
        )
        r = _bash(inner)
        out = r.stdout + r.stderr
        assert r.returncode == 0, f"_check_node failed:\n{out}"
        assert "v" in out

    def test_npx_not_used_in_start_services(self):
        src = (_DEPLOY_DIR / "host" / "deploy.sh").read_text()
        assert "npx vite" not in src, "must use ./node_modules/.bin/vite, not npx"

    def test_backend_kill_uses_fuser(self):
        src = (_DEPLOY_DIR / "host" / "deploy.sh").read_text()
        assert "fuser" in src and "9772" in src, "should kill by port 9772"

    def test_frontend_kill_uses_fuser(self):
        src = (_DEPLOY_DIR / "host" / "deploy.sh").read_text()
        assert "fuser" in src and "5173" in src, "should kill by port 5173"

    def test_stop_services_has_fuser(self):
        src = (_DEPLOY_DIR / "host" / "deploy.sh").read_text()
        lines = src.split("\n")
        in_stop = False
        found = False
        for line in lines:
            if "stop_services()" in line:
                in_stop = True
                continue
            if in_stop and "fuser" in line and "9772" in line:
                found = True
                break
            if in_stop and line.strip() == "}":
                break
        assert found, "stop_services must also kill by port"

    def test_npm_registry_check_in_build_frontend(self):
        src = (_DEPLOY_DIR / "host" / "deploy.sh").read_text()
        assert "npm ping" in src, "should check npm registry reachability"

    def test_node_check_in_build_frontend(self):
        src = (_DEPLOY_DIR / "host" / "deploy.sh").read_text()
        import re
        build_start = src.index("build_frontend()")
        next_func = re.search(r"^[a-z_]+\(\)", src[build_start + 16:], re.MULTILINE)
        end = build_start + 16 + next_func.start() if next_func else len(src)
        body = src[build_start:end]
        assert "_check_node" in body, "build_frontend must call _check_node"


class TestDeployDirectoryLayout:
    """deploy/ directory structure and old-path cleanup."""

    _EXPECTED = ["deploy_pg.sh", "deploy.conf", "host/deploy.sh", "docker/deploy_witty.sh", "docker/manage.sh"]

    def test_all_deploy_files_present(self):
        for fname in self._EXPECTED:
            assert (_DEPLOY_DIR / fname).is_file(), f"missing {fname}"

    def test_pg_conf_fallback_supported(self):
        """旧名 pg.conf 已改名 deploy.conf，读取方必须保留回退逻辑。"""
        for script in ["deploy_pg.sh", "docker/deploy_witty.sh", "docker/manage.sh",
                       "host/deploy.sh", "host/_lib.sh", "rpm/libexec/_lib.sh"]:
            src = (_DEPLOY_DIR / script).read_text()
            assert "pg.conf" in src, f"{script} lacks pg.conf fallback"

    def test_deploy_pg_resolves_depoy_dir(self):
        src = (_DEPLOY_DIR / "deploy_pg.sh").read_text()
        assert "DEPLOY_DIR" in src or "SCRIPT_DIR" in src

    def test_old_scripts_deploy_removed(self):
        old = _PROJECT_ROOT / "scripts" / "deploy.sh"
        assert not old.exists(), f"old path still exists: {old}"


# ──────────────────────────────────────────────────────────────
# Pipeline e2e (same as test_integration_pipeline.py)
# ──────────────────────────────────────────────────────────────

class TestFullIntegration:
    """Pipeline e2e via subprocess — ensures deploy-layer + scanner +
    aggregate + detail_rows + cache are all green."""

    @pytest.mark.integration
    def test_pipeline_e2e(self):
        test_file = Path(__file__).with_name("test_integration_pipeline.py")
        r = subprocess.run(
            [
                sys.executable, "-m", "pytest", str(test_file),
                "-v", "-m", "integration", "--tb=short",
            ],
            capture_output=True, text=True, timeout=300,
            cwd=str(test_file.parent),
            env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", "")},
        )
        sys.stdout.write(r.stdout)
        if r.stderr and "ERROR" in r.stderr:
            sys.stderr.write(r.stderr)
        assert r.returncode == 0, f"Pipeline e2e failed (rc={r.returncode})"
