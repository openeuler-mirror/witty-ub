"""Exercise classifier packaging and deployment launchers without live services."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / 'witty_ub_diagnostician/skills/case-matching'


def run(command, *, env=None, cwd=None):
    result = subprocess.run(command, env={**os.environ, **(env or {})}, cwd=cwd,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_packaged_backend_trains_and_agent_reads_shared_weights_without_backend_dependencies(tmp_path):
    deployed = tmp_path / 'var/witty-ub'
    target = deployed / 'classifier-runtime'
    run(['bash', str(ROOT / 'deploy/rpm/install_classifier_runtime.sh'), str(SKILL), str(target)])
    assert not list(target.rglob('__pycache__'))
    assert not (deployed / 'witty_ub_diagnostician').exists()
    # Model updates must not depend on the source checkout or web/Agent RPM.
    for relative in ('__init__.py', 'services/fault_classifier.py', 'database/engine.py', 'database/models.py',
                     'common/local_time.py', 'ENUM/general.py'):
        dest = deployed / 'latency' / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'src/plugins/latency' / relative, dest)
    env = {'WITTY_DIR': str(deployed), 'WITTY_CLASSIFIER_MODEL_DIR': '',
           'WITTY_CASE_MATCHING_DIR': '', 'PYTHONPATH': str(deployed), 'OPENBLAS_NUM_THREADS': '1'}
    result = run([sys.executable, '-c', '''
import asyncio,json
from pathlib import Path
from latency.services.fault_classifier import runtime,build_in_process
rt=runtime()
assert Path(rt.__file__).parent.parent==Path(__import__('os').environ['WITTY_DIR'])/'classifier-runtime'
result=asyncio.run(build_in_process([],set(),'packaged-backend'))
rt.model_registry.atomic_json(rt.model_registry.model_root()/'active.json',{'version':result['version']})
print(json.dumps({'version':result['version'],'samples':result['sample_count']}))
'''], env=env, cwd=tmp_path)
    published = json.loads(result.stdout)
    assert published['samples'] > 400
    agent_scripts = tmp_path / 'frontend/skills/case-matching/scripts'
    shutil.copytree(SKILL / 'scripts', agent_scripts, ignore=shutil.ignore_patterns('__pycache__'))
    agent = run([sys.executable, '-S', '-c', '''
import default_matching as rt,json
model=rt.asset('numeric_classifier')
context=rt.unknown_context()
key=model['feature_names'][0].removeprefix('mined2:numeric_units:')
context['families']['numeric_units']={key:1.}
profile={'schema_version':'legacy-evidence-v1','status_codes':[],'failure_mode_ids':[],
         'latency_components':[],'operation':'GET','log_semantic_profile':{}}
result=rt.match(profile,context=context)
assert result['decision']['method']=='numeric_units_classifier'
print(json.dumps(result['decision']))
'''], env={**env, 'PYTHONPATH': str(agent_scripts)}, cwd=tmp_path)
    assert json.loads(agent.stdout)['model_id'] == published['version']


def test_reinstall_seed_does_not_overwrite_published_state(tmp_path):
    target = tmp_path / 'classifier-runtime'
    models = tmp_path / 'fault_classifier'
    models.mkdir()
    marker = models / 'active.json'
    marker.write_text('{"version":"trained"}')
    for _ in range(2):
        run(['bash', str(ROOT / 'deploy/rpm/install_classifier_runtime.sh'), str(SKILL), str(target)])
    assert marker.read_text() == '{"version":"trained"}'


def test_host_agent_and_backend_export_same_runtime_paths(tmp_path):
    source = tmp_path / 'source'
    (source / 'deploy/host').mkdir(parents=True)
    (source / 'src/plugins/latency/.venv/bin').mkdir(parents=True)
    shutil.copy2(ROOT / 'deploy/host/run_backend.sh', source / 'deploy/host/run_backend.sh')
    shutil.copy2(ROOT / 'deploy/deploy_opencode.sh', source / 'deploy/deploy_opencode.sh')
    # Let the real backend launcher export its environment, with its interpreter doubled.
    executable = source / 'src/plugins/latency/.venv/bin/python'
    executable.write_text('#!/bin/sh\nprintf "%s\\n%s\\n" "$WITTY_REPORT_DIR" "$WITTY_CLASSIFIER_MODEL_DIR"\n')
    executable.chmod(0o755)
    deployed = tmp_path / 'var/witty-ub'
    env = {'WITTY_DIR': str(deployed), 'WITTY_REPORT_DIR': '', 'WITTY_CLASSIFIER_MODEL_DIR': '',
           'WITTY_RAG_ENV_FILE': str(tmp_path / 'no-rag'), 'PG_PASSWORD': 'test-only'}
    backend = run(['bash', str(source / 'deploy/host/run_backend.sh')], env=env)
    # Read the real shared Agent export block without installing or starting OpenCode.
    script = (ROOT / 'deploy/deploy_opencode.sh').read_text()
    exports = script.split('export WITTY_DIR=', 1)[1].split('echo "[INFO] Validating', 1)[0]
    agent = run(['bash', '-c', 'set -eu\nexport WITTY_DIR=' + exports +
                 '\nprintf "%s\\n%s\\n" "$WITTY_REPORT_DIR" "$WITTY_CLASSIFIER_MODEL_DIR"'],
                env={**env, 'WITTY_ROOT': str(source), 'OPENCODE_CONFIG_PATH': str(source / 'deploy/deploy_opencode.sh')})
    assert backend.stdout.splitlines() == agent.stdout.splitlines() == [str(deployed / 'reports'), str(deployed / 'fault_classifier')]


def test_rpm_uses_same_mount_override_for_manager_and_systemd(tmp_path):
    etc = tmp_path / 'etc'
    etc.mkdir()
    shared = tmp_path / 'shared-models'
    (etc / 'classifier.env').write_text('WITTY_CLASSIFIER_MODEL_DIR=' + shlex.quote(str(shared)) + '\n')
    result = run(['bash', '-c', 'source ' + shlex.quote(str(ROOT / 'deploy/rpm/libexec/_lib.sh')) +
                  '; WITTY_ROLE=frontend; prepare_classifier_runtime; printf "%s" "$WITTY_CLASSIFIER_MODEL_DIR"'],
                 env={'WITTY_DIR': str(tmp_path / 'var'), 'WITTY_ETC_DIR': str(etc), 'WITTY_CLASSIFIER_MODEL_DIR': ''})
    assert result.stdout == str(shared) and shared.is_dir()
    unit = (ROOT / 'src/plugins/latency/deploy/witty-ub-latency.service').read_text()
    assert 'EnvironmentFile=-/etc/witty-ub/classifier.env' in unit


def test_docker_all_roles_share_named_model_volume():
    import yaml
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    for role in ('witty-ub', 'witty-ub-backend', 'witty-ub-frontend'):
        assert 'witty-ub-classifier-models:/var/witty-ub/fault_classifier' in compose['services'][role]['volumes']
    assert compose['volumes']['witty-ub-classifier-models']['name'] == 'witty-ub-classifier-models'
    for filename in ('Dockerfile', 'Dockerfile.rpm'):
        content = (ROOT / filename).read_text()
        for line in content.splitlines():
            if line.startswith('VOLUME '):assert '"/var/witty-ub/fault_classifier"' in line


def test_source_systemd_backend_and_agent_receive_identical_custom_directories(tmp_path):
    import re
    config = tmp_path / 'user-config'
    calls = tmp_path / 'calls'
    deployed = tmp_path / 'runtime'
    shared = tmp_path / 'shared'
    reports = tmp_path / 'reports'
    env = {'WITTY_DIR': str(deployed), 'WITTY_CLASSIFIER_MODEL_DIR': str(shared),
           'WITTY_REPORT_DIR': str(reports), 'WITTY_ROLE': 'backend', 'XDG_CONFIG_HOME': str(config),
           'SCRIPT_DIR': str(ROOT / 'deploy/host'), 'PROJECT_DIR': str(ROOT), 'CALLS': str(calls)}
    source = (ROOT / 'deploy/host/deploy.sh').read_text()
    function = re.search(r'^install_systemd_units\(\) \{\n.*?^\}', source, re.M | re.S).group()
    run(['bash', '-c', '''
_step_header() { :; }; _warn() { :; }; _log() { :; }
systemd_user_available() { return 0; }; systemctl() { echo "$*" >> "$CALLS"; }
''' + function + '\ninstall_systemd_units'], env=env)
    # Execute the Agent service installer, replacing system commands only.
    commands = tmp_path / 'bin'
    commands.mkdir()
    for name in ('systemctl', 'curl', 'sleep'):
        path = commands / name
        path.write_text('#!/bin/sh\nexit 0\n')
        path.chmod(0o755)
    run(['bash', str(ROOT / 'deploy/host/install_opencode_service.sh'), 'install'],
        env={**env, 'PATH': str(commands) + ':' + os.environ['PATH'], 'OPENCODE_BIN': '/bin/true'})
    for name in ('witty-ub-backend.service', 'witty-ub-opencode.service'):
        unit = (config / 'systemd/user' / name).read_text()
        assert '__' not in unit
        assert 'Environment=WITTY_CLASSIFIER_MODEL_DIR=' + str(shared) in unit
        assert 'Environment=WITTY_REPORT_DIR=' + str(reports) in unit
        assert 'Environment=WITTY_DIR=' + str(deployed) in unit
    assert shared.is_dir() and reports.is_dir()


@pytest.mark.parametrize('role,keep_model', [('frontend', True), ('backend', False)])
def test_rpm_clean_respects_backend_ownership_of_shared_models(tmp_path,role,keep_model):
    import re
    model = tmp_path / 'shared-models'
    model.mkdir()
    active = model / 'active.json'
    active.write_text('{"version":"published"}')
    source = (ROOT / 'deploy/rpm/libexec/manager.sh').read_text()
    function = re.search(r'^do_clean\(\) \{\n.*?^\}', source, re.M | re.S).group()
    run(['bash', '-c', 'source ' + shlex.quote(str(ROOT / 'deploy/rpm/libexec/_lib.sh')) + '''
WITTY_SERVICES=(test-only-service)
systemctl() { return 0; }; _has_cmd() { return 1; }; _confirm() { return 0; }
''' + function + '\ndo_clean'], env={'WITTY_DIR': str(tmp_path / 'runtime'), 'WITTY_ETC_DIR': str(tmp_path / 'etc'),
    'WITTY_CLASSIFIER_MODEL_DIR': str(model), 'WITTY_ROLE': role, 'CLEAN_SCOPE':'1'})
    assert active.exists() == keep_model
