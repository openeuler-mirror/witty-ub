pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 90, unit: 'MINUTES')
        skipDefaultCheckout(true)
    }

    parameters {
        booleanParam(
            name: 'RUN_BLUE_ZONE_PARSE',
            defaultValue: false,
            description: 'Mount a host directory read-only and run the blue-zone real-log parse gate.'
        )
        string(
            name: 'BLUE_ZONE_LOG_HOST_DIR',
            defaultValue: '',
            trim: true,
            description: 'Absolute path on the Docker host containing the two blue-zone scenario directories.'
        )
        booleanParam(
            name: 'RUN_CALLSTACK_PROFILE',
            defaultValue: false,
            description: 'Profile the blue-zone UBM parse with cProfile and generate source-linked hotspot reports. Requires RUN_BLUE_ZONE_PARSE.'
        )
        booleanParam(
            name: 'RUN_SEMANTIC_DIAGNOSIS',
            defaultValue: false,
            description: 'Call DeepSeek to generate and validate a source-linked diagnosis. Requires RUN_CALLSTACK_PROFILE.'
        )
    }

    environment {
        REPO_URL = 'https://gitcode.com/openeuler/witty-ub.git'
        BRANCH = 'dev_openeuler24.03-sp4'
        BASE_IMAGE = 'witty-ub-base:latest'
        REGISTRY = 'hub-harbor.oepkgs.net'
        IMAGE_REPOSITORY = 'hub-harbor.oepkgs.net/neocopilot/witty-ub'
        HARBOR_CREDENTIALS_ID = 'oepkgs-harbor'
        TEST_CONTAINER = "witty-ub-ci-${BUILD_NUMBER}"
        DOCKER_BUILDKIT = '1'
        PERF_REQUESTS = '300'
        PERF_CONCURRENCY = '20'
        PERF_P95_MS = '1000'
        STABILITY_SECONDS = '120'
        CALLSTACK_PROFILE_LIMIT = '20'
        CALLSTACK_SOURCE_CONTEXT_LINES = '8'
        CALLSTACK_COMPARE_REPEATS = '5'
        CALLSTACK_COMPARE_MODES = 'single,2,auto'
        CALLSTACK_COMPARE_THRESHOLD_PERCENT = '15'
        DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
        DEEPSEEK_MODEL = 'deepseek-v4-pro'
        BLUE_ZONE_CONTAINER_DIR = '/testdata/blue-zone'
        BLUE_ZONE_PARSE_TIMEOUT_SECONDS = '900'
        BLUE_ZONE_SCALE_DIR = 'lingqu_kvcache_dfx_client_process_scale_in_worker_hang_up_001_20260528_09_25_30'
        BLUE_ZONE_UBM_DIR = 'lingqu_kvcache_dfx_client_process_get_ubm_failure_001_20260529_21_18_36'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: "${BRANCH}", url: "${REPO_URL}"
                script {
                    env.GIT_SHORT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                    env.BRANCH_TAG = env.BRANCH.replaceAll('[^A-Za-z0-9_.-]', '-')
                    env.APP_IMAGE = "witty-ub:ci-${BUILD_NUMBER}-${env.GIT_SHORT}"
                    env.PUBLISH_IMAGE = "${env.IMAGE_REPOSITORY}:${env.BRANCH_TAG}-${BUILD_NUMBER}-${env.GIT_SHORT}"
                    env.PUBLISH_ALIAS = "${env.IMAGE_REPOSITORY}:latest"
                }
                sh 'git log -1 --oneline'
            }
        }

        stage('Check Environment') {
            steps {
                sh 'docker --version'
                sh 'docker buildx version'
                sh 'test -f Dockerfile'
                sh 'test -f Dockerfile.base'
                sh 'test -f src/plugins/latency/test/test_all_apis.py'
                sh 'test -f src/plugins/latency/test/test_kv_cache_log_parse_worker_profile.py'
                sh 'test -f .opencode/skills/witty-ub-jenkins-ci/scripts/analyze_cprofile.py'
                sh 'test -f .opencode/skills/witty-ub-jenkins-ci/scripts/call_deepseek_diagnosis.py'
                sh 'test -f .opencode/skills/witty-ub-jenkins-ci/scripts/render_callstack_diagnosis.py'
                sh 'test -f .opencode/skills/witty-ub-jenkins-ci/references/callstack-agent-prompt.md'
                sh 'test -f .opencode/skills/witty-ub-jenkins-ci/assets/callstack-diagnosis.schema.json'
            }
        }

        stage('Build Base Image') {
            steps {
                sh '''
                    docker build \
                      --progress=plain \
                      -f Dockerfile.base \
                      -t "$BASE_IMAGE" .
                '''
            }
        }

        stage('Build Application Image') {
            steps {
                sh '''
                    docker build \
                      --progress=plain \
                      -f Dockerfile \
                      -t "$APP_IMAGE" \
                      -t witty-ub:ci-latest .
                '''
            }
        }

        stage('Verify Image Artifacts') {
            steps {
                sh '''
                    docker image inspect "$APP_IMAGE" \
                      --format "image={{.RepoTags}} arch={{.Architecture}} size={{.Size}}"
                '''
                sh '''
                    docker run --rm --entrypoint /bin/sh "$APP_IMAGE" -c '
                      test -x /usr/bin/witty-ub-log &&
                      test -x /usr/bin/witty-ub-topo &&
                      test -x /usr/bin/witty-ub-diag-tool &&
                      test -x /entrypoint.sh
                    '
                '''
            }
        }

        stage('Start Test Container') {
            steps {
                sh '''#!/bin/bash
                    set -eu
                    docker rm -fv "$TEST_CONTAINER" >/dev/null 2>&1 || true

                    docker_run=(
                      docker run -d
                      --name "$TEST_CONTAINER"
                      -e PYTHONPATH=/var/witty-ub
                      -e LOG_LEVEL=info
                    )

                    run_blue_zone="${RUN_BLUE_ZONE_PARSE:-false}"
                    blue_zone_host_dir="${BLUE_ZONE_LOG_HOST_DIR:-}"

                    if [ "$run_blue_zone" = "true" ]; then
                      case "$blue_zone_host_dir" in
                        /*) ;;
                        *)
                          echo "BLUE_ZONE_LOG_HOST_DIR must be an absolute host path"
                          exit 1
                          ;;
                      esac
                      if [ "$blue_zone_host_dir" = "/" ]; then
                        echo "Refusing to mount the Docker host root"
                        exit 1
                      fi
                      docker_run+=(
                        --mount
                        "type=bind,src=$blue_zone_host_dir,dst=$BLUE_ZONE_CONTAINER_DIR,readonly"
                      )
                    fi

                    docker_run+=("$APP_IMAGE")
                    "${docker_run[@]}"

                    ready=0
                    for i in $(seq 1 30); do
                      if docker exec "$TEST_CONTAINER" \
                           curl -fsS http://127.0.0.1:8080/health_check; then
                        ready=1
                        break
                      fi

                      if ! docker inspect \
                           --format '{{.State.Running}}' "$TEST_CONTAINER" |
                           grep -q true; then
                        break
                      fi
                      sleep 2
                    done

                    if [ "$ready" -ne 1 ]; then
                      echo "Witty-UB did not become healthy"
                      docker logs "$TEST_CONTAINER" \
                        > container-startup.log 2>&1 || true
                      docker cp \
                        "$TEST_CONTAINER:/var/log/witty-ub/latency_server.log" \
                        latency-server.log 2>/dev/null || true
                      docker cp \
                        "$TEST_CONTAINER:/var/log/witty-ub-web/error.log" \
                        nginx-error.log 2>/dev/null || true
                      cat container-startup.log || true
                      cat latency-server.log || true
                      cat nginx-error.log || true
                      exit 1
                    fi

                    docker exec "$TEST_CONTAINER" \
                      curl -fsS http://127.0.0.1:9772/health_check
                    docker exec "$TEST_CONTAINER" \
                      curl -fsS http://127.0.0.1:8080/health_check

                    if [ "$run_blue_zone" = "true" ]; then
                      docker exec \
                        -e BLUE_ZONE_CONTAINER_DIR="$BLUE_ZONE_CONTAINER_DIR" \
                        -e BLUE_ZONE_SCALE_DIR="$BLUE_ZONE_SCALE_DIR" \
                        -e BLUE_ZONE_UBM_DIR="$BLUE_ZONE_UBM_DIR" \
                        "$TEST_CONTAINER" \
                        /bin/bash -c '
                          set -eu
                          test -d "$BLUE_ZONE_CONTAINER_DIR/$BLUE_ZONE_SCALE_DIR"
                          test -d "$BLUE_ZONE_CONTAINER_DIR/$BLUE_ZONE_UBM_DIR"
                          scale_logs=$(find \
                            "$BLUE_ZONE_CONTAINER_DIR/$BLUE_ZONE_SCALE_DIR" \
                            -type f -name "*.log" | wc -l)
                          ubm_logs=$(find \
                            "$BLUE_ZONE_CONTAINER_DIR/$BLUE_ZONE_UBM_DIR" \
                            -type f -name "*.log" | wc -l)
                          test "$scale_logs" -gt 0
                          test "$ubm_logs" -gt 0
                          printf "mount_mode=readonly\\nscale_log_files=%s\\nubm_log_files=%s\\n" \
                            "$scale_logs" "$ubm_logs"
                        ' | tee blue-zone-mount-check.txt
                    fi
                '''
            }
        }

        stage('Functional Test') {
            steps {
                sh '''#!/bin/bash
                    set -euo pipefail
                    docker exec "$TEST_CONTAINER" \
                      mkdir -p /var/witty-ub/latency/test
                    docker cp \
                      "$WORKSPACE/src/plugins/latency/test/test_all_apis.py" \
                      "$TEST_CONTAINER:/var/witty-ub/latency/test/test_all_apis.py"

                    docker exec \
                      -w /var/witty-ub/latency \
                      "$TEST_CONTAINER" \
                      /var/witty-ub/latency/.venv/bin/python \
                      test/test_all_apis.py |
                      tee functional-test.log

                    passed=$(grep -c 'PASS' functional-test.log || true)
                    failed=$(grep -c 'FAIL' functional-test.log || true)
                    echo "functional_passed=$passed functional_failed=$failed"

                    test "$passed" -gt 0
                    test "$failed" -eq 0
                '''
            }
        }

        stage('Blue Zone Real Log Parse') {
            when {
                expression {
                    return params.RUN_BLUE_ZONE_PARSE == true
                }
            }
            steps {
                sh '''#!/bin/bash
                    set -euo pipefail
                    docker exec -i \
                      -e BLUE_ZONE_CONTAINER_DIR="$BLUE_ZONE_CONTAINER_DIR" \
                      -e BLUE_ZONE_SCALE_DIR="$BLUE_ZONE_SCALE_DIR" \
                      -e BLUE_ZONE_UBM_DIR="$BLUE_ZONE_UBM_DIR" \
                      -e BLUE_ZONE_PARSE_TIMEOUT_SECONDS="$BLUE_ZONE_PARSE_TIMEOUT_SECONDS" \
                      "$TEST_CONTAINER" \
                      /var/witty-ub/latency/.venv/bin/python - \
                      <<'PY' | tee blue-zone-parse-report.json
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE_URL = "http://127.0.0.1:9772"
ROOT = os.environ["BLUE_ZONE_CONTAINER_DIR"]
SCALE_DIR = os.environ["BLUE_ZONE_SCALE_DIR"]
UBM_DIR = os.environ["BLUE_ZONE_UBM_DIR"]
TIMEOUT = int(os.environ["BLUE_ZONE_PARSE_TIMEOUT_SECONDS"])
EXPECTED = {
    "scale-in-worker-hang-up": 0,
    "get-ubm-failure": 10240,
}


def request(method, path, payload=None, timeout=30):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path}: HTTP {exc.code}: {raw}") from exc
    if status != 200:
        raise RuntimeError(f"{method} {path}: HTTP {status}: {body}")
    if isinstance(body, dict) and "code" in body and body["code"] != 200:
        raise RuntimeError(f"{method} {path}: application error: {body}")
    return body


def result(body):
    return body.get("result") or {}


def list_result(path, payload):
    return result(request("POST", path, payload))


started = time.monotonic()
kb_id = None
log_file_ids = []
report = {
    "status": "failed",
    "gate": "blue-zone-real-log-parse",
    "mount": {
        "container_root": ROOT,
        "read_only": True,
    },
    "expected": EXPECTED,
    "capability_note": (
        "The scale-in sample is SET-only and the current parser supports GET, "
        "so its expected parse count remains zero."
    ),
}

try:
    create = result(
        request(
            "POST",
            "/log_kb",
            {
                "name": f"jenkins-blue-zone-{uuid.uuid4().hex[:8]}",
                "description": "Jenkins blue-zone real-log parse gate",
            },
        )
    )
    kb_id = create["kb_id"]
    configs = [
        {
            "name": "scale-in-worker-hang-up",
            "source_type": "local",
            "source": f"{ROOT}/{SCALE_DIR}",
        },
        {
            "name": "get-ubm-failure",
            "source_type": "local",
            "source": f"{ROOT}/{UBM_DIR}",
        },
    ]
    upload = result(
        request(
            "POST",
            f"/log_file/{kb_id}",
            {"upload_log_file_configs": configs},
        )
    )
    log_file_ids = upload.get("log_file_ids") or []
    if len(log_file_ids) != len(configs):
        raise RuntimeError(f"expected 2 log ids, got: {upload}")

    deadline = time.monotonic() + TIMEOUT
    last_status = {}
    counts = {}
    while time.monotonic() < deadline:
        files = list_result(
            f"/log_file/list/{kb_id}",
            {"page_cnt": 100, "page_num": 1},
        ).get("log_files") or []
        by_name = {item["name"]: item for item in files}
        if set(EXPECTED).issubset(by_name):
            tasks = list_result(
                "/task/list",
                {"kb_id": kb_id, "page_cnt": 100, "page_num": 1},
            ).get("tasks") or []
            parse_tasks = {
                task["op_id"]: task
                for task in tasks
                if task.get("task_type") == "kv_cache_log_parse_worker"
            }
            last_status = {
                name: (parse_tasks.get(item["id"]) or {}).get("status")
                for name, item in by_name.items()
                if name in EXPECTED
            }
            if any(status == "failed" for status in last_status.values()):
                raise RuntimeError(f"parse task failed: {last_status}")
            if all(last_status.get(name) == "successful" for name in EXPECTED):
                counts = {
                    name: list_result(
                        "/log_parse_result/list",
                        {
                            "kb_id": kb_id,
                            "log_id": by_name[name]["id"],
                            "page_cnt": 1,
                            "page_num": 1,
                        },
                    ).get("total", 0)
                    for name in EXPECTED
                }
                if counts == EXPECTED:
                    break
        time.sleep(2)
    else:
        raise TimeoutError(
            f"parse did not reach expected counts in {TIMEOUT}s; "
            f"statuses={last_status}, counts={counts}"
        )

    report.update(
        {
            "status": "passed",
            "kb_id": kb_id,
            "task_status": last_status,
            "actual": counts,
        }
    )
except Exception as exc:
    report["error"] = str(exc)
finally:
    for log_file_id in log_file_ids:
        try:
            request("DELETE", f"/log_file/{log_file_id}")
        except Exception as cleanup_exc:
            report.setdefault("cleanup_errors", []).append(str(cleanup_exc))
    if kb_id:
        try:
            request("DELETE", f"/log_kb/{kb_id}")
        except Exception as cleanup_exc:
            report.setdefault("cleanup_errors", []).append(str(cleanup_exc))
    report["duration_seconds"] = round(time.monotonic() - started, 3)

print(json.dumps(report, ensure_ascii=False))
sys.exit(0 if report["status"] == "passed" else 1)
PY
                '''
            }
        }

        stage('Performance Analysis - Call Stack') {
            when {
                expression {
                    return params.RUN_CALLSTACK_PROFILE == true
                }
            }
            steps {
                sh '''#!/bin/bash
                    set -euo pipefail
                    if [ "${RUN_BLUE_ZONE_PARSE:-false}" != "true" ]; then
                      echo "RUN_CALLSTACK_PROFILE requires RUN_BLUE_ZONE_PARSE"
                      exit 1
                    fi

                    profile_dir=/tmp/witty-ub-callstack-profile
                    profile_target="$BLUE_ZONE_CONTAINER_DIR/$BLUE_ZONE_UBM_DIR"

                    docker exec "$TEST_CONTAINER" \
                      rm -rf "$profile_dir"
                    docker exec "$TEST_CONTAINER" \
                      mkdir -p "$profile_dir" /var/witty-ub/latency/test

                    docker cp \
                      "$WORKSPACE/src/plugins/latency/test/test_kv_cache_log_parse_worker_profile.py" \
                      "$TEST_CONTAINER:/var/witty-ub/latency/test/test_kv_cache_log_parse_worker_profile.py"
                    docker cp \
                      "$WORKSPACE/.opencode/skills/witty-ub-jenkins-ci/scripts/analyze_cprofile.py" \
                      "$TEST_CONTAINER:/tmp/analyze_cprofile.py"

                    docker exec \
                      -w /var/witty-ub/latency \
                      "$TEST_CONTAINER" \
                      /var/witty-ub/latency/.venv/bin/python \
                      test/test_kv_cache_log_parse_worker_profile.py \
                      pipeline "$profile_target" \
                      --output "$profile_dir/callstack-profile.prof" \
                      --report "$profile_dir/callstack-profile.txt" \
                      --limit "$CALLSTACK_PROFILE_LIMIT" |
                      tee callstack-profile-console.log

                    docker exec \
                      -w /var/witty-ub/latency \
                      "$TEST_CONTAINER" \
                      /var/witty-ub/latency/.venv/bin/python \
                      test/test_kv_cache_log_parse_worker_profile.py \
                      compare "$profile_target" \
                      --comparison-modes "$CALLSTACK_COMPARE_MODES" \
                      --comparison-repeats "$CALLSTACK_COMPARE_REPEATS" \
                      --expected-results 10240 \
                      --decision-threshold-percent \
                      "$CALLSTACK_COMPARE_THRESHOLD_PERCENT" \
                      --comparison-json \
                      "$profile_dir/callstack-comparison.json" \
                      --comparison-markdown \
                      "$profile_dir/callstack-comparison.md" |
                      tee callstack-comparison-console.log

                    docker exec "$TEST_CONTAINER" \
                      /var/witty-ub/latency/.venv/bin/python \
                      /tmp/analyze_cprofile.py \
                      --profile "$profile_dir/callstack-profile.prof" \
                      --json-report "$profile_dir/callstack-evidence.json" \
                      --markdown-report "$profile_dir/callstack-evidence.md" \
                      --target "$BLUE_ZONE_UBM_DIR" \
                      --source-revision "$GIT_SHORT" \
                      --limit "$CALLSTACK_PROFILE_LIMIT" \
                      --context-lines "$CALLSTACK_SOURCE_CONTEXT_LINES" \
                      --experiment-json \
                      "$profile_dir/callstack-comparison.json" |
                      tee callstack-evidence-console.log

                    docker exec "$TEST_CONTAINER" \
                      /var/witty-ub/latency/.venv/bin/python -c \
                      'import json, sys; report=json.load(open(sys.argv[1], encoding="utf-8")); assert report["status"] == "passed"; assert report["result_consistency"] == "passed"; assert report["observed_result_counts"] == [10240]' \
                      "$profile_dir/callstack-comparison.json"

                    docker exec "$TEST_CONTAINER" \
                      /var/witty-ub/latency/.venv/bin/python -c \
                      'import json, sys; report=json.load(open(sys.argv[1], encoding="utf-8")); assert report["status"] == "evidence_ready"; assert report["selection"]["selected_function_count"] > 0; assert report["controlled_experiment"]["result_consistency"] == "passed"; assert report["semantic_diagnosis"]["performed"] is False' \
                      "$profile_dir/callstack-evidence.json"

                    docker cp \
                      "$TEST_CONTAINER:$profile_dir/callstack-profile.prof" \
                      callstack-profile.prof
                    docker cp \
                      "$TEST_CONTAINER:$profile_dir/callstack-profile.txt" \
                      callstack-profile.txt
                    docker cp \
                      "$TEST_CONTAINER:$profile_dir/callstack-comparison.json" \
                      callstack-comparison.json
                    docker cp \
                      "$TEST_CONTAINER:$profile_dir/callstack-comparison.md" \
                      callstack-comparison.md
                    docker cp \
                      "$TEST_CONTAINER:$profile_dir/callstack-evidence.json" \
                      callstack-evidence.json
                    docker cp \
                      "$TEST_CONTAINER:$profile_dir/callstack-evidence.md" \
                      callstack-evidence.md

                    test -s callstack-profile.prof
                    test -s callstack-profile.txt
                    test -s callstack-comparison.json
                    test -s callstack-comparison.md
                    test -s callstack-evidence.json
                    test -s callstack-evidence.md
                    sed -n '1,160p' callstack-comparison.md
                    sed -n '1,120p' callstack-evidence.md
                '''
            }
        }

        stage('Semantic Diagnosis - DeepSeek') {
            when {
                expression {
                    return params.RUN_SEMANTIC_DIAGNOSIS == true
                }
            }
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    withCredentials([
                        string(
                            credentialsId: 'deepseek-api-key',
                            variable: 'DEEPSEEK_API_KEY'
                        )
                    ]) {
                        sh '''#!/bin/bash
                            set -euo pipefail
                            if [ "${RUN_CALLSTACK_PROFILE:-false}" != "true" ]; then
                              echo "RUN_SEMANTIC_DIAGNOSIS requires RUN_CALLSTACK_PROFILE"
                              exit 1
                            fi

                            profile_dir=/tmp/witty-ub-callstack-profile
                            diagnosis_source=/tmp/witty-ub-diagnosis-source

                            copy_diagnosis_debug_artifacts() {
                              docker cp \
                                "$TEST_CONTAINER:$profile_dir/callstack-diagnosis.raw.txt" \
                                callstack-diagnosis.raw.txt 2>/dev/null || true
                              docker cp \
                                "$TEST_CONTAINER:$profile_dir/callstack-diagnosis.repair.raw.txt" \
                                callstack-diagnosis.repair.raw.txt \
                                2>/dev/null || true
                            }
                            trap copy_diagnosis_debug_artifacts EXIT

                            docker exec "$TEST_CONTAINER" \
                              rm -rf "$diagnosis_source"
                            docker exec "$TEST_CONTAINER" \
                              mkdir -p "$diagnosis_source/src/plugins"

                            docker cp \
                              "$WORKSPACE/src/plugins/latency" \
                              "$TEST_CONTAINER:$diagnosis_source/src/plugins/latency"
                            docker cp \
                              "$WORKSPACE/.opencode/skills/witty-ub-jenkins-ci/scripts/call_deepseek_diagnosis.py" \
                              "$TEST_CONTAINER:/tmp/call_deepseek_diagnosis.py"
                            docker cp \
                              "$WORKSPACE/.opencode/skills/witty-ub-jenkins-ci/scripts/render_callstack_diagnosis.py" \
                              "$TEST_CONTAINER:/tmp/render_callstack_diagnosis.py"
                            docker cp \
                              "$WORKSPACE/.opencode/skills/witty-ub-jenkins-ci/references/callstack-agent-prompt.md" \
                              "$TEST_CONTAINER:/tmp/callstack-agent-prompt.md"
                            docker cp \
                              "$WORKSPACE/.opencode/skills/witty-ub-jenkins-ci/assets/callstack-diagnosis.schema.json" \
                              "$TEST_CONTAINER:/tmp/callstack-diagnosis.schema.json"

                            docker exec \
                              -e DEEPSEEK_API_KEY \
                              -e DEEPSEEK_BASE_URL \
                              -e DEEPSEEK_MODEL \
                              "$TEST_CONTAINER" \
                              /var/witty-ub/latency/.venv/bin/python \
                              /tmp/call_deepseek_diagnosis.py \
                              --evidence "$profile_dir/callstack-evidence.json" \
                              --schema /tmp/callstack-diagnosis.schema.json \
                              --prompt /tmp/callstack-agent-prompt.md \
                              --source-root "$diagnosis_source" \
                              --output "$profile_dir/callstack-diagnosis.json" \
                              2>&1 | tee callstack-diagnosis-console.log

                            docker exec "$TEST_CONTAINER" \
                              /var/witty-ub/latency/.venv/bin/python \
                              /tmp/render_callstack_diagnosis.py \
                              --evidence "$profile_dir/callstack-evidence.json" \
                              --diagnosis "$profile_dir/callstack-diagnosis.json" \
                              --source-root "$diagnosis_source" \
                              --json-report \
                              "$profile_dir/callstack-diagnosis.validated.json" \
                              --markdown-report \
                              "$profile_dir/callstack-diagnosis.md" \
                              2>&1 | tee -a callstack-diagnosis-console.log

                            docker cp \
                              "$TEST_CONTAINER:$profile_dir/callstack-diagnosis.json" \
                              callstack-diagnosis.json
                            docker cp \
                              "$TEST_CONTAINER:$profile_dir/callstack-diagnosis.validated.json" \
                              callstack-diagnosis.validated.json
                            docker cp \
                              "$TEST_CONTAINER:$profile_dir/callstack-diagnosis.md" \
                              callstack-diagnosis.md

                            test -s callstack-diagnosis.json
                            test -s callstack-diagnosis.validated.json
                            test -s callstack-diagnosis.md
                            sed -n '1,200p' callstack-diagnosis.md
                        '''
                    }
                }
            }
        }

        stage('Performance Analysis - HTTP Baseline') {
            steps {
                sh '''#!/bin/bash
                    set -euo pipefail
                    docker exec -i \
                      -e PERF_REQUESTS="$PERF_REQUESTS" \
                      -e PERF_CONCURRENCY="$PERF_CONCURRENCY" \
                      -e PERF_P95_MS="$PERF_P95_MS" \
                      "$TEST_CONTAINER" \
                      /var/witty-ub/latency/.venv/bin/python - \
                      <<'PY' | tee performance-report.json
import concurrent.futures
import json
import math
import os
import sys
import time
import urllib.request

requests_count = int(os.environ["PERF_REQUESTS"])
concurrency = int(os.environ["PERF_CONCURRENCY"])
p95_limit_ms = float(os.environ["PERF_P95_MS"])
urls = [
    "http://127.0.0.1:8080/health_check",
    "http://127.0.0.1:9772/health_check",
]

def request_once(index):
    url = urls[index % len(urls)]
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            response.read()
            status = response.status
        error = None if status == 200 else f"HTTP {status}"
    except Exception as exc:
        error = str(exc)
    return (time.perf_counter() - started) * 1000.0, error

for index in range(10):
    request_once(index)

started = time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
    results = list(executor.map(request_once, range(requests_count)))
elapsed = time.perf_counter() - started

latencies = sorted(latency for latency, error in results if error is None)
errors = [error for _, error in results if error is not None]

def percentile(values, ratio):
    if not values:
        return None
    index = max(0, min(len(values) - 1, math.ceil(len(values) * ratio) - 1))
    return round(values[index], 3)

report = {
    "requests": requests_count,
    "concurrency": concurrency,
    "successes": len(latencies),
    "failures": len(errors),
    "elapsed_seconds": round(elapsed, 3),
    "throughput_rps": round(requests_count / elapsed, 3) if elapsed else None,
    "p50_ms": percentile(latencies, 0.50),
    "p95_ms": percentile(latencies, 0.95),
    "p99_ms": percentile(latencies, 0.99),
    "max_ms": round(max(latencies), 3) if latencies else None,
    "p95_limit_ms": p95_limit_ms,
}
print(json.dumps(report, ensure_ascii=False))

passed = (
    len(errors) == 0
    and report["p95_ms"] is not None
    and report["p95_ms"] <= p95_limit_ms
)
sys.exit(0 if passed else 1)
PY
                '''
            }
        }

        stage('Short Stability Test') {
            steps {
                sh '''#!/bin/bash
                    set -euo pipefail
                    restart_before=$(docker inspect \
                      --format '{{.RestartCount}}' "$TEST_CONTAINER")

                    docker exec -i \
                      -e STABILITY_SECONDS="$STABILITY_SECONDS" \
                      "$TEST_CONTAINER" \
                      /var/witty-ub/latency/.venv/bin/python - \
                      <<'PY' | tee stability-report.json
import json
import os
import sys
import time
import urllib.request

duration = int(os.environ["STABILITY_SECONDS"])
interval = 0.2
urls = [
    "http://127.0.0.1:8080/health_check",
    "http://127.0.0.1:9772/health_check",
]
deadline = time.monotonic() + duration
requests_count = 0
failures = []

while time.monotonic() < deadline:
    url = urls[requests_count % len(urls)]
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            response.read()
            if response.status != 200:
                failures.append(f"HTTP {response.status}: {url}")
    except Exception as exc:
        failures.append(f"{url}: {exc}")
    requests_count += 1
    time.sleep(max(0.0, interval - (time.monotonic() - started)))

report = {
    "duration_seconds": duration,
    "requests": requests_count,
    "failures": len(failures),
    "first_errors": failures[:5],
}
print(json.dumps(report, ensure_ascii=False))
sys.exit(0 if not failures else 1)
PY

                    test "$(docker inspect \
                      --format '{{.State.Running}}' "$TEST_CONTAINER")" = "true"
                    restart_after=$(docker inspect \
                      --format '{{.RestartCount}}' "$TEST_CONTAINER")
                    echo "restart_before=$restart_before restart_after=$restart_after"
                    test "$restart_before" = "$restart_after"
                '''
            }
        }

        stage('Publish Image') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: env.HARBOR_CREDENTIALS_ID,
                    usernameVariable: 'HARBOR_USERNAME',
                    passwordVariable: 'HARBOR_PASSWORD'
                )]) {
                    sh '''#!/bin/bash
                        set -euo pipefail
                        printf '%s' "$HARBOR_PASSWORD" |
                          docker login "$REGISTRY" \
                            --username "$HARBOR_USERNAME" \
                            --password-stdin
                        trap 'docker logout "$REGISTRY" >/dev/null 2>&1 || true' EXIT

                        docker tag "$APP_IMAGE" "$PUBLISH_IMAGE"
                        docker tag "$APP_IMAGE" "$PUBLISH_ALIAS"
                        docker push "$PUBLISH_IMAGE"
                        docker push "$PUBLISH_ALIAS"

                        echo "published_image=$PUBLISH_IMAGE"
                        echo "published_alias=$PUBLISH_ALIAS"
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "Witty-UB Jenkins validation and publish passed: ${PUBLISH_IMAGE}"
        }
        always {
            sh '''
                docker logs "$TEST_CONTAINER" \
                  > container-startup.log 2>&1 || true
                docker cp \
                  "$TEST_CONTAINER:/var/log/witty-ub/latency_server.log" \
                  latency-server.log 2>/dev/null || true
                docker cp \
                  "$TEST_CONTAINER:/var/log/witty-ub-web/error.log" \
                  nginx-error.log 2>/dev/null || true
            '''
            archiveArtifacts(
                artifacts: 'container-startup.log,latency-server.log,nginx-error.log,functional-test.log,blue-zone-mount-check.txt,blue-zone-parse-report.json,callstack-profile-console.log,callstack-comparison-console.log,callstack-evidence-console.log,callstack-diagnosis-console.log,callstack-profile.prof,callstack-profile.txt,callstack-comparison.json,callstack-comparison.md,callstack-evidence.json,callstack-evidence.md,callstack-diagnosis.json,callstack-diagnosis.validated.json,callstack-diagnosis.md,callstack-diagnosis.raw.txt,callstack-diagnosis.repair.raw.txt,performance-report.json,stability-report.json',
                allowEmptyArchive: true
            )
            sh 'docker rm -fv "$TEST_CONTAINER" >/dev/null 2>&1 || true'
            deleteDir()
        }
    }
}
