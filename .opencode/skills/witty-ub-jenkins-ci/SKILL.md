---
name: witty-ub-jenkins-ci
description: Build, test, analyze performance, and publish Witty-UB container images in Jenkins without deploying a persistent local service, covering functional checks, an optional read-only host-mounted blue-zone real-log parse gate, HTTP baseline, source-linked Python call-stack profiling, optional DeepSeek semantic diagnosis with deterministic source validation, short stability checks, and authenticated Harbor publication. Use when creating, updating, running, or diagnosing the Witty-UB Jenkins Pipeline; configuring automated model diagnosis; validating Dockerfile or Dockerfile.base changes; parsing the two blue-zone log scenarios from a Docker-host directory; locating slow Python functions to source files and lines; publishing a verified image; or reporting whether a branch passes image build and runtime validation.
---

# Witty-UB Jenkins CI

Run Witty-UB container validation on Jenkins. Do not replace the running Witty-UB service or treat a local manual build as CI evidence.

## Inputs

Confirm these values before running:

- Repository URL. Default: `https://gitcode.com/openeuler/witty-ub.git`
- Branch. Default: `dev_openeuler24.03-sp4`
- Jenkins job name. Recommended: `witty-ub-build`
- Jenkins URL and credentials when API access is required.
- Harbor repository. Default: `hub-harbor.oepkgs.net/neocopilot/witty-ub`
- Jenkins username/password credential ID. Default: `oepkgs-harbor`
- Whether to run the blue-zone real-log parse gate. Default: disabled.
- When enabled, the absolute Docker-host directory containing the two blue-zone
  scenario directories. Do not use a Jenkins-container-only path.
- Whether to run the function call-stack profile. Default: disabled. It requires
  the blue-zone gate and profiles the UBM scenario with the same read-only input.
- Whether to run automatic DeepSeek semantic diagnosis. Default: disabled. It
  requires the call-stack profile.
- DeepSeek Jenkins Secret text credential ID. Default: `deepseek-api-key`.
- DeepSeek API base URL and model. Pipeline defaults:
  `https://api.deepseek.com` and `deepseek-v4-pro`.

Verify the remote branch exists:

```bash
git ls-remote --heads <repository-url> refs/heads/<branch>
```

Do not silently fall back to another branch.

## Preconditions

Require the Jenkins agent to have:

- Pipeline and Git plugins
- Docker CLI and Buildx
- Access to a Docker daemon
- At least 10 GB free disk space
- A Jenkins username/password credential that can push to the Harbor repository
- For automatic semantic diagnosis, outbound HTTPS access to the DeepSeek API
  and a Jenkins Secret text credential named `deepseek-api-key`
- For the optional blue-zone gate, a Docker-host directory that:
  - Is an absolute path and is not `/`
  - Is readable by the Docker daemon
  - Contains both expected scenario directories and at least one `.log` file in each
  - Has enough free space for Witty-UB parsing output

Run environment checks inside Jenkins, not as a substitute local build. Stop and report `BLOCKED` when a precondition is missing.

## Pipeline

Read [references/jenkins-pipeline.groovy](references/jenkins-pipeline.groovy), update only the repository and branch when needed, then use it as the Jenkins Pipeline script.

The Pipeline must:

1. Check out the exact requested branch and record the commit.
2. Build `Dockerfile.base` as `witty-ub-base:latest`, allowing Docker layer cache.
3. Build `Dockerfile` with a unique build-number and commit tag.
4. Check that the three Witty-UB binaries and `/entrypoint.sh` exist.
5. Start a uniquely named temporary container without publishing host ports.
   Set `PYTHONPATH=/var/witty-ub` as required by the container's `latency.*` imports.
6. Verify both internal health endpoints:
   - `http://127.0.0.1:9772/health_check`
   - `http://127.0.0.1:8080/health_check`
7. Run the repository's full API script as the functional regression test and fail the build when the script prints a failed API check.
8. When `RUN_BLUE_ZONE_PARSE=true`, bind-mount `BLUE_ZONE_LOG_HOST_DIR`
   read-only at `/testdata/blue-zone`, verify both scenario directories, create an
   isolated knowledge base, parse the real logs, and require:
   - Scale-in worker hang-up: 0 parse results, documenting the current SET-only capability boundary
   - GET UBM failure: 10,240 parse results
9. When `RUN_CALLSTACK_PROFILE=true`, rerun the UBM parse under `cProfile`,
   capture the parent process and ProcessPool workers, compare single, two, and
   automatic process modes, and generate a source-linked evidence bundle. Do not
   label the evidence bundle a root-cause report.
10. When `RUN_SEMANTIC_DIAGNOSIS=true`, send the evidence, schema, prompt, and
    selected source files to DeepSeek; validate the response against the exact
    revision; derive source anchors deterministically; and render the validated
    diagnosis. Treat model or validation failure as a diagnostic-stage failure,
    not a product-test failure.
11. Run the HTTP performance baseline and record request count, concurrency, throughput, P50, P95, P99, maximum latency, and failures.
12. Run the short stability test against both health paths and verify that the container remains running without a restart.
13. After every enabled test gate passes, log in to Harbor with Jenkins Credentials and push:
    - An immutable `<branch>-<build-number>-<commit>` tag
    - A moving `latest` tag
14. Capture container startup, FastAPI, and Nginx error logs before cleanup.
15. Archive diagnostic logs plus functional, blue-zone parse, call-stack
    evidence, performance, and stability reports.
16. Remove the temporary container and its anonymous volumes in `post.always`.

## Test Levels

### Functional

Run `src/plugins/latency/test/test_all_apis.py` inside the isolated test container. The upstream script prints failures but does not return a nonzero exit code, so inspect its output and fail Jenkins when it contains `FAIL`. Require a nonzero number of passed API checks.

### Blue-zone real-log parse

Keep this gate optional because the 288 MB test dataset is server-local and is
not stored in the source repository.

Set these Jenkins build parameters:

```text
RUN_BLUE_ZONE_PARSE=true
BLUE_ZONE_LOG_HOST_DIR=/absolute/path/on/docker-host/蓝区日志1
```

After replacing the Jenkins Pipeline script, run it once with the default
parameters if Jenkins has not yet displayed **Build with Parameters**. Then
start the real-log run with the two values above.

The Jenkins container controls the host Docker daemon through
`/var/run/docker.sock`. Therefore the bind source is resolved on the Docker
host, not inside the Jenkins container. Use Docker `--mount type=bind` so a
missing source path fails instead of silently creating an empty directory.

The Pipeline mounts the directory read-only and does not publish it as a host
port. It checks only the real-log parsing coverage currently established by the
blue-zone test:

- `lingqu_kvcache_dfx_client_process_scale_in_worker_hang_up_001_20260528_09_25_30`
- `lingqu_kvcache_dfx_client_process_get_ubm_failure_001_20260529_21_18_36`

This gate is not the complete 92-case blue-zone pytest suite. In particular, it
does not claim that the known CRUD and exception-contract problems are fixed,
and it does not claim SET/DELETE parsing or root-cause diagnosis accuracy.

### Performance analysis

Treat HTTP timing, call-stack profiling, scanner-mode comparison, and
source-linked root-cause diagnosis as parts of the same performance-analysis
workflow.

#### Function call-stack and scanner-mode analysis

Keep this profile optional because `cProfile` adds overhead and reruns the UBM
parse. Require:

```text
RUN_BLUE_ZONE_PARSE=true
RUN_CALLSTACK_PROFILE=true
BLUE_ZONE_LOG_HOST_DIR=/absolute/path/on/docker-host/蓝区日志1
```

The profile uses the repository's
`src/plugins/latency/test/test_kv_cache_log_parse_worker_profile.py` and captures
both the parent Python process and the parallel scanner's ProcessPool workers.
The Pipeline then runs
`.opencode/skills/witty-ub-jenkins-ci/scripts/analyze_cprofile.py` to generate:

- `callstack-profile.prof`: combined raw profile for `pstats` or other viewers
- `callstack-profile.txt`: functions sorted by cumulative and internal time
- `callstack-comparison.json`: all per-round single/two/automatic process
  timings, result counts, medians, and the threshold decision
- `callstack-comparison.md`: short mentor-facing answer stating which mode won,
  whether the difference is actionable, and the exact source symbol to change
- `callstack-evidence.json`: machine-readable cumulative/self/call-count views,
  callers, callees, external runtime hotspots, source anchors, source context,
  and the embedded controlled comparison
- `callstack-evidence.md`: fixed human-readable evidence summary with no
  automatically invented root cause or suggestion
- `callstack-profile-console.log`, `callstack-comparison-console.log`, and
  `callstack-evidence-console.log`: Jenkins execution evidence

Require `callstack-evidence.json` to contain at least one selected project
function. Require every comparison run to return 10,240 results. The deterministic
comparison may recommend a process-strategy change only when the fastest mode
improves the automatic baseline median by at least 15%; otherwise it must say not
to change process strategy.

Use five rounds for the default strict CI decision. Rotate mode order between
rounds to distribute warm-cache and run-order effects. A local quick check may
use three rounds, but do not change a production default without five rounds
under the same source revision, input, CPU/memory limits, and cache policy.

Use the Jenkins Linux result for a Jenkins or production recommendation. A local
macOS run is only a functional check because the operating system, Python
version, CPU architecture, and multiprocessing start method can materially
change process startup cost. Preserve these fields in the comparison report.

Interpret the comparison as follows:

- Single process wins by at least 15%: add a configurable small-task threshold
  in `ParallelFileScanner.scan_all` after file count and total bytes are known.
  Reuse the existing asyncio path below the threshold.
- A fixed process count wins by at least 15%: make the maximum scanner process
  count configurable in `KVCacheLogParseWorker._new_parallel_scanner`; do not
  hard-code the experimental value globally.
- No mode reaches 15%: keep the current process strategy and investigate worker
  file reading and line parsing instead.
- Result counts differ: invalidate all timings and treat the run as a
  correctness failure.

The evidence builder gathers and packages facts only. It must not generate
heuristic root causes or claim that a hot wrapper is the root cause.

Do not use cProfile timings as production latency or an SLA. Combined worker CPU
time is additive across processes and may exceed wall-clock duration.

#### Semantic call-stack diagnosis

Use one of two modes:

1. **Automatic Jenkins mode**: enable `RUN_SEMANTIC_DIAGNOSIS`; the Pipeline
   calls DeepSeek through `scripts/call_deepseek_diagnosis.py`.
2. **Portable agent mode**: give Codex, Claude, or another source-capable agent
   the exact repository revision, call-stack artifacts, schema, renderer, and
   [references/callstack-agent-prompt.md](references/callstack-agent-prompt.md).

Read
[references/deepseek-semantic-diagnosis.md](references/deepseek-semantic-diagnosis.md)
before configuring or troubleshooting automatic mode.

Keep responsibilities separate:

- Let the model connect observed profile behavior to a causal mechanism, user
  impact, actionable change, risks, and a falsifiable verification plan.
- Let deterministic code copy the evidence revision and target, derive unique
  file-and-line anchors from cited evidence function IDs, validate summary
  counts, enforce status rules, and render the final report.
- Preserve `callstack-evidence.json` unchanged. Its
  `semantic_diagnosis.performed=false` means the evidence collector itself did
  not infer a root cause. It does not mean the following DeepSeek stage was
  skipped. Use `callstack-diagnosis.validated.json` as the semantic-stage result.

For automatic mode require:

```text
RUN_BLUE_ZONE_PARSE=true
RUN_CALLSTACK_PROFILE=true
RUN_SEMANTIC_DIAGNOSIS=true
BLUE_ZONE_LOG_HOST_DIR=/absolute/path/on/docker-host/蓝区日志1
```

Store the API key only as Jenkins Secret text credential
`deepseek-api-key`. Never place it in parameters, Pipeline text, source,
console output, or artifacts. The caller sends profiling evidence, the schema,
the diagnosis prompt, and selected source files; it does not send the original
blue-zone `.log` files.

The automatic caller must:

1. Require a non-empty JSON response and retry an empty response up to three
   times.
2. Repair malformed JSON or an incorrect top-level structure once.
3. Copy revision, target, and artifact metadata from evidence rather than
   trusting model-generated values.
4. Derive source locations and unique anchors from cited
   `evidence_function_ids` and the checked-out source.
5. Run the same deterministic validation as the renderer and allow one
   validation-directed model repair.
6. Keep unsupported causal claims as `investigation`; never silently upgrade
   them to `confirmed`.

Validate and render the diagnosis:

```bash
python3 .opencode/skills/witty-ub-jenkins-ci/scripts/render_callstack_diagnosis.py \
  --evidence callstack-evidence.json \
  --diagnosis callstack-diagnosis.json \
  --source-root . \
  --json-report callstack-diagnosis.validated.json \
  --markdown-report callstack-diagnosis.md
```

Archive:

- `callstack-diagnosis.json`: normalized model-authored diagnosis
- `callstack-diagnosis.validated.json`: validation metadata and verified source
  locations
- `callstack-diagnosis.md`: mentor-facing root-cause and modification report
- `callstack-diagnosis.raw.txt`: first non-empty model response
- `callstack-diagnosis.repair.raw.txt`: repair response when a repair was needed
- `callstack-diagnosis-console.log`: provider attempt count, response size, and
  validation output; it must not contain the API key

The renderer rejects unknown profile function IDs, stale or ambiguous source
anchors, mismatched summary counts, confirmed findings without controlled
validation, investigations without a falsifiable experiment, and duplicated
template recommendations. It validates and formats model-authored reasoning; it
does not discover the root cause itself.

#### HTTP performance baseline

Use the Nginx-proxied health endpoint as a repeatable CI baseline:

- Requests: 300
- Concurrency: 20
- Required successful responses: 100%
- Default P95 limit: 1000 ms

Treat this as an HTTP service baseline, not a full log-parsing throughput benchmark or production SLA.

### Stability

Run a 120-second short soak test, alternating between the direct FastAPI and Nginx-proxied health endpoints. Require:

- No failed health request
- Container still running
- Docker restart count unchanged

Treat this as a CI stability gate, not a long-duration production stability test.

## Safety Rules

- Never run `docker compose up -d` as part of this validation.
- Never stop, rename, or replace an existing `witty-ub` container.
- Never reuse a fixed test-container name.
- Never expose test-container ports on the host.
- Never mount an empty, relative, or `/` blue-zone host path.
- Mount blue-zone input read-only. Never delete, rename, extract, or rewrite host log files.
- Never run global `docker system prune`, `docker builder prune`, or delete unrelated images.
- Never print registry, Git, or SSH credentials. Use Jenkins Credentials and `docker login --password-stdin`.
- Never push an image before all enabled test gates pass.
- Do not deploy the published image or push to Kubernetes unless the user explicitly requests deployment.
- Do not describe the CI performance baseline as a production load test.
- Do not enable call-stack profiling by default or describe a hotspot as a
  confirmed root cause without source inspection and a controlled rerun.
- Never describe `callstack-evidence.md` as a root-cause report.
- Never let a language model silently upgrade `investigation` to `confirmed`.
- Never store a model endpoint token or API key in source or Pipeline text.
- Never send the original blue-zone log files, Jenkins credentials, registry
  credentials, access keys, or unrelated repository files to a model provider.
- Never accept model-generated revision metadata or source anchors without
  deterministic verification against the checked-out repository.
- Do not describe the short soak test as a long-duration stability test.

## Acceptance

Call the run `PASS` only when Jenkins reports `Finished: SUCCESS` and all build and runtime stages pass.

Use these statuses:

- `PASS`: Jenkins completed every stage successfully.
- `FAIL`: Jenkins ran the stage and a build, artifact, startup, or health assertion failed.
- `BLOCKED`: Jenkins could not run because a branch, plugin, Docker capability, credential, network dependency, or disk requirement was unavailable.
- `NOT RUN`: The Pipeline was generated but not executed.

Do not infer success from an image existing on the host or from a manually run command.
When publication is enabled, require both Harbor pushes to succeed before returning `PASS`.
When the blue-zone gate is enabled, require `blue-zone-parse-report.json` to
report `status=passed` before publication. When it is disabled, report the gate
as `SKIPPED`, not `PASS`.
When call-stack profiling is enabled, require all nine call-stack evidence
artifacts, comparison result consistency, 10,240 results in every run, and a
nonzero selected project-function count. Profiling success means
`EVIDENCE_READY`; it does not mean every root cause was found.

When semantic diagnosis is enabled, require:

- `callstack-diagnosis.json`, `callstack-diagnosis.validated.json`, and
  `callstack-diagnosis.md` are non-empty
- the renderer reports `status=passed`
- every cited evidence function ID exists
- every source location is verified against the checked-out revision
- summary counts match the findings
- confirmed findings contain controlled validation
- investigation findings contain a falsifiable next experiment

If automatic semantic diagnosis fails while product tests pass, classify the
diagnostic stage separately and leave the overall Jenkins result non-successful;
do not call it a product regression and do not publish an unvalidated diagnosis
as final.

## Result Report

Return:

```text
status:
job:
build_number:
repository:
branch:
commit:
base_image:
application_image:
published_image:
published_alias:
build_result:
binary_check:
api_health:
nginx_health:
functional_passed:
functional_failed:
blue_zone_parse_enabled:
blue_zone_host_dir:
blue_zone_mount_mode:
blue_zone_scale_parse_results:
blue_zone_ubm_parse_results:
blue_zone_parse_duration_seconds:
callstack_profile_enabled:
callstack_profile_target:
callstack_profile_scope:
callstack_comparison_repeats:
callstack_comparison_result_consistency:
callstack_comparison_selected_mode:
callstack_comparison_improvement_percent:
callstack_comparison_decision:
callstack_selected_function_count:
callstack_evidence_status:
semantic_diagnosis_enabled:
semantic_diagnosis_provider:
semantic_diagnosis_model:
semantic_diagnosis_attempts:
callstack_diagnosis_status:
callstack_confirmed_findings:
callstack_investigation_findings:
callstack_verified_source_locations:
callstack_all_locations_verified:
performance_requests:
performance_concurrency:
performance_throughput_rps:
performance_p95_ms:
performance_threshold_ms:
stability_duration_seconds:
stability_requests:
stability_failures:
container_restart_count:
cleanup:
console_url:
failure_stage:
failure_summary:
```

Use values observed from Jenkins output. Do not invent build numbers, image tags, health responses, or console URLs.

## Failure Diagnosis

- Checkout failure: verify repository visibility, branch name, DNS, and Git credentials.
- Base-image failure: report the failing `dnf` or `pip` layer; do not bypass it with an unrelated prebuilt image.
- Web-build failure: report the failing `npm ci` or `npm run build-only` command.
- C++ build failure: report the first compiler or linker error.
- Container exits early: include `docker logs` and the latency log when available.
- API health passes but Nginx health fails: inspect `/etc/witty-ub/web/nginx.conf` and Nginx logs.
- Blue-zone bind mount fails: verify that the parameter is an absolute Docker-host
  path, both scenario directories exist, and the Docker daemon can read them.
- Blue-zone parse times out: inspect task status and `latency-server.log`; do not
  increase the timeout before checking whether parsing is making progress.
- Blue-zone count mismatch: preserve `blue-zone-parse-report.json` and classify
  it as a parser/data regression; do not change expected counts merely to pass CI.
- Call-stack profile fails before producing `.prof`: inspect
  `callstack-profile-console.log`, confirm the blue-zone mount and profiler test
  file, and do not install an unrelated profiler at runtime.
- Scanner-mode comparison fails: inspect `callstack-comparison-console.log`.
  If any result count differs from 10,240, discard all timing conclusions and
  diagnose correctness before performance.
- Scanner-mode comparison is noisy: increase from three to five rounds and keep
  the source revision, input directory, CPU/memory limits, and mode order policy
  fixed; do not lower the 15% decision threshold merely to obtain a winner.
- Call-stack evidence has no project function: preserve the raw `.prof`, inspect
  the runtime source-path mapping, and classify it as diagnostic-integrity
  failure rather than product performance failure.
- DeepSeek credential lookup fails: verify a Jenkins Secret text credential with
  ID `deepseek-api-key`; never print or copy the key into a build parameter.
- DeepSeek returns HTTP 401 or 403: classify it as credential/provider
  configuration failure, not a Witty-UB product failure.
- DeepSeek returns an empty response: let the caller retry up to three times.
  If every response is empty, preserve the console attempt metadata and classify
  it as a provider diagnostic failure.
- DeepSeek returns malformed JSON or an outer wrapper: let the caller perform
  one structure repair. If it still fails, preserve raw responses and do not
  bypass the schema.
- Diagnosis revision or target differs from evidence: overwrite only this fixed
  metadata from the evidence; never let the model choose it.
- Diagnosis source location is empty, stale, ambiguous, or contains invented
  text: derive locations from cited evidence function IDs and select a unique
  source-line anchor from the checked-out revision.
- Diagnosis fails deterministic validation after repair: keep the model stage
  failed or unstable, preserve the raw response and validation error, and report
  product gates separately.
- Agent diagnosis is generic or duplicated: reject it; inspect complete caller
  and callee source paths and rewrite one mechanism-specific recommendation per
  deduplicated finding.
- A cause lacks controlled validation: keep it as `investigation` and state the
  exact baseline/variant experiment instead of presenting it as fact.
- Harbor login or push failure: verify the credential ID, repository permission, registry certificate, and network access. Do not print the password.
- Cleanup failure: report it separately even when functional checks pass.
