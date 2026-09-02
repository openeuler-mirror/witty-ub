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
        r = _bash(
            f"source {_DEPLOY_DIR}/deploy.conf && "
            "echo $PG_HOST $PG_PORT_RPM $PG_PORT $PG_DATABASE $PG_USER"
        )
        parts = r.stdout.strip().split()
        assert parts[0] == "127.0.0.1"
        assert parts[1] == "5432"  # 源码/RPM 本机 PostgreSQL
        assert parts[2] == "15432"  # Docker 宿主机映射端口
        assert parts[3] == "witty-ub"
        assert parts[4] == "witty-ub"

    @pytest.mark.parametrize(
        "loader",
        [
            f"source {_DEPLOY_DIR}/host/_lib.sh",
            (
                f"PG_CONF_FILE={_DEPLOY_DIR}/deploy.conf; "
                f"source {_DEPLOY_DIR}/rpm/libexec/_lib.sh"
            ),
        ],
    )
    def test_native_deploy_loaders_use_5432(self, loader):
        # 即使环境中残留 Docker 的 PG_PORT=15432，原生部署也不得读取它。
        r = _bash(f"unset PG_PORT_RPM; PG_PORT=15432; {loader}; _load_pg_credentials; echo $PG_PORT")
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "5432"


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

    def test_native_modes_do_not_fall_back_to_docker_port(self):
        src = (_DEPLOY_DIR / "deploy_pg.sh").read_text()
        assert 'PG_PORT="${PG_PORT_RPM_OVERRIDE:-${PG_PORT_RPM:-5432}}"' in src


class TestOpenCodePromptConfig:
    """Agent prompt remains immutable and resolves backend variables at Bash runtime."""

    def test_source_deploy_uses_repository_prompt_directly(self):
        src = (_DEPLOY_DIR / "deploy_opencode.sh").read_text()
        assert 'OPENCODE_CONFIG_PATH="${LOCAL_BUNDLE_CONFIG}"' in src
        assert 'AGENT_PROMPT="${LOCAL_BUNDLE_PROMPT}"' in src
        assert "export WITTY_API_BASE WITTY_NO_PROXY OPENCODE_HOST" in src
        assert "LOCAL_RUNTIME_DIR" not in src
        assert "sed -i" not in src

    def test_prompt_keeps_runtime_variables(self):
        prompt = (
            _PROJECT_ROOT
            / "witty_ub_diagnostician"
            / "agents"
            / "witty-ub-diagnostician.md"
        ).read_text()
        assert "${WITTY_API_BASE}" in prompt
        assert "${WITTY_NO_PROXY}" in prompt

    def test_other_deploy_paths_do_not_render_prompt(self):
        for script in [
            _DEPLOY_DIR / "host" / "deploy.sh",
            _DEPLOY_DIR / "rpm" / "libexec" / "_lib.sh",
            _PROJECT_ROOT / "docker" / "entrypoint.sh",
        ]:
            src = script.read_text()
            assert "render_agent_prompt" not in src


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

    _EXPECTED = [
        "deploy_pg.sh", "deploy.conf",
        "host/deploy.sh", "docker/deploy_witty.sh", "docker/manage.sh",
        "rpm/witty-ub", "rpm/web.env",
        "rpm/libexec/_lib.sh", "rpm/libexec/manager.sh",
        "rpm/libexec/install_deps.sh", "rpm/libexec/deploy_pg.sh",
    ]

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
# RPM 子包化（witty-ub / -backend / -web / -manager）
# ──────────────────────────────────────────────────────────────

_RPM_DIR = _DEPLOY_DIR / "rpm"


class TestRpmSubpackageSupport:
    """子包化配套文件与角色化脚本."""

    def test_web_env_defaults(self):
        src = (_RPM_DIR / "web.env").read_text()
        for key in ("WITTY_BACKEND_URL", "WITTY_API_BASE", "WITTY_AGENT_URL", "WITTY_NO_PROXY"):
            assert f"{key}=" in src, f"web.env 缺少 {key}"

    def test_role_detection_no_autostart_agent(self):
        """OpenCode 维持手动启动，manager 不创建 witty-ub-agent.service."""
        for script in ["libexec/manager.sh", "libexec/_lib.sh", "witty-ub"]:
            src = (_RPM_DIR / script).read_text()
            assert "witty-ub-agent.service" not in src, f"{script} 不应引用 witty-ub-agent.service"

    def test_deploy_opencode_dual_layout(self):
        """deploy_opencode.sh 支持 bundle 与 config/agents 双布局."""
        src = (_PROJECT_ROOT / "deploy" / "deploy_opencode.sh").read_text()
        assert "witty_ub_diagnostician" in src
        assert "config/agents/witty-ub-diagnostician.md" in src

    def test_agent_prompt_dual_layout_render(self):
        """_lib.sh 渲染提示词时兜底 config/agents 旧布局."""
        src = (_RPM_DIR / "libexec" / "_lib.sh").read_text()
        assert "AGENT_PROMPT_FILE_LEGACY" in src


class TestRpmLib:
    """deploy/rpm/libexec/_lib.sh 角色探测 / 服务集 / 配置渲染."""

    def _source_lib(self, tmp_env: dict, snippet: str) -> subprocess.CompletedProcess:
        inner = (
            f"set +eu; source {_RPM_DIR}/libexec/_lib.sh; set +eu; {snippet}"
        )
        return subprocess.run(
            ["bash", "-c", inner], capture_output=True, text=True,
            timeout=30, env={**os.environ, **tmp_env},
        )

    def test_rpm_scripts_syntax(self):
        for script in ["libexec/_lib.sh", "libexec/manager.sh",
                       "libexec/install_deps.sh", "libexec/deploy_pg.sh", "witty-ub"]:
            r = subprocess.run(["bash", "-n", str(_RPM_DIR / script)],
                               capture_output=True, text=True)
            assert r.returncode == 0, f"rpm/{script} syntax error:\n{r.stderr}"

    @pytest.mark.parametrize("role,expected", [
        ("backend", "witty-ub-latency"),
        ("frontend", "witty-ub-web"),
        ("all", "witty-ub-web witty-ub-latency"),
    ])
    def test_role_services(self, role, expected):
        r = self._source_lib(
            {"WITTY_ROLE_FORCE": role},
            'detect_role && role_services && echo "SVC=${WITTY_SERVICES[*]}"',
        )
        out = r.stdout + r.stderr
        assert f"SVC={expected}" in out, f"role={role}:\n{out}"

    def test_detect_role_force_override(self):
        r = self._source_lib(
            {"WITTY_ROLE_FORCE": "frontend"},
            'detect_role && echo "ROLE=$WITTY_ROLE"',
        )
        assert "ROLE=frontend" in r.stdout + r.stderr

    def test_write_web_env_then_get(self, tmp_path):
        etc = tmp_path / "etc"
        r = self._source_lib(
            {"WITTY_ETC_DIR": str(etc)},
            'write_web_env http://192.168.1.10:9772 http://127.0.0.1:4096 '
            '&& web_env_get WITTY_BACKEND_URL '
            '&& web_env_get WITTY_NO_PROXY',
        )
        out = (r.stdout + r.stderr).strip().splitlines()
        assert "http://192.168.1.10:9772" in out
        assert "127.0.0.1,192.168.1.10" in out  # no_proxy 自动包含后端主机
        assert (etc / "web" / "env").is_file()

    def test_render_nginx_conf(self, tmp_path):
        template = tmp_path / "nginx.conf.template"
        template.write_text(
            "proxy_pass ${WITTY_BACKEND_URL};\nproxy_pass ${WITTY_AGENT_URL};\n"
        )
        conf = tmp_path / "web" / "nginx.conf"
        r = self._source_lib(
            {"WITTY_ETC_DIR": str(tmp_path), "NGINX_CONF_TEMPLATE": str(template)},
            'render_nginx_conf http://10.0.0.1:9772 http://127.0.0.1:4096',
        )
        rendered = conf.read_text()
        assert "http://10.0.0.1:9772" in rendered
        assert "http://127.0.0.1:4096" in rendered
        assert "${WITTY_" not in rendered  # 占位符全部替换

    def test_url_host_extracts_hostname(self):
        r = self._source_lib({}, '_url_host http://192.168.1.10:9772/x')
        assert r.stdout.strip() == "192.168.1.10"


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
