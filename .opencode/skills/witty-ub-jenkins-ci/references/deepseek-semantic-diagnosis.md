# DeepSeek semantic diagnosis

Use this reference to configure, run, and troubleshoot the optional automatic
call-stack diagnosis stage. Keep the original profiling evidence separate from
the model-authored diagnosis.

## Configure Jenkins once

1. Open **Manage Jenkins → Credentials → System → Global credentials → Add
   Credentials**.
2. Select **Secret text**.
3. Put the DeepSeek API key in **Secret**.
4. Set **ID** to `deepseek-api-key`.
5. Save. Never put the key in a build parameter, Pipeline source, console
   command, screenshot, or report.
6. Confirm the Jenkins agent and the temporary Witty-UB container can reach
   `https://api.deepseek.com` over HTTPS.

The reference Pipeline uses:

```text
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
```

Change provider settings only after checking the provider's current API
documentation. Keep the credential ID stable unless the Pipeline is updated at
the same time.

## Run the complete diagnostic flow

Open **Build with Parameters** and set:

```text
RUN_BLUE_ZONE_PARSE=true
BLUE_ZONE_LOG_HOST_DIR=/absolute/path/on/docker-host/蓝区日志1
RUN_CALLSTACK_PROFILE=true
RUN_SEMANTIC_DIAGNOSIS=true
```

If the new parameter is not visible after replacing the Pipeline script, run
the job once with defaults so Jenkins refreshes declarative parameters, then
return to **Build with Parameters**.

Use a Docker-host path, not a path that exists only inside the Jenkins
container. The Pipeline mounts the blue-zone directory read-only. It sends the
model profiling evidence and selected source files, not the original `.log`
files.

## Understand the stages

The execution order is:

```text
blue-zone parse
→ cProfile parent and ProcessPool workers
→ scanner-mode controlled comparison
→ deterministic call-stack evidence
→ DeepSeek semantic reasoning
→ deterministic metadata and source-link normalization
→ schema, evidence, anchor, status, and summary validation
→ deterministic fallback diagnosis when the model still leaves placeholders
→ Markdown rendering and artifact archive
```

The model owns:

- causal interpretation of measured behavior
- direct cause and cost model
- user impact
- implementation-specific modification suggestions
- risks, correctness invariants, and a falsifiable benchmark

Deterministic code owns:

- evidence revision, target, and artifact metadata
- file, line, and unique source anchor selection
- evidence-function ID validity
- summary-count consistency
- confirmed/investigation status requirements
- duplicate recommendation detection

Do not ask the model to invent a source revision, line number, or anchor.

## Read the outputs

| Artifact | Meaning |
| --- | --- |
| `callstack-evidence.json` | Immutable profiling evidence. `semantic_diagnosis.performed=false` is expected here. |
| `callstack-evidence.md` | Human-readable evidence without a claimed root cause. |
| `callstack-diagnosis.raw.txt` | First non-empty DeepSeek response. |
| `callstack-diagnosis.repair.raw.txt` | Model repair response when repair was needed. |
| `callstack-diagnosis.fallback.json` | Deterministic investigation-only diagnosis generated when the model response and one repair still fail validation. Empty or absent means the model-authored diagnosis passed. |
| `callstack-diagnosis.json` | Normalized diagnosis passed to the renderer. |
| `callstack-diagnosis.validated.json` | Verified evidence IDs, source locations, counts, and status rules. |
| `callstack-diagnosis.md` | Mentor-facing root-cause and modification report. |
| `callstack-diagnosis-console.log` | Attempt count, response size, and deterministic validation result. |

Treat `callstack-diagnosis.validated.json` and `callstack-diagnosis.md` as the
semantic-stage delivery. Do not use the raw response as the final report.

## Interpret status

- `Finished: SUCCESS`: every enabled product and diagnostic stage passed.
- `Finished: UNSTABLE` with product gates passing: the optional model or
  diagnostic-integrity stage failed. Do not call it a product regression.
- `Finished: FAILURE` before the model stage: diagnose checkout, build,
  container, functional, blue-zone, or profiling stages first.
- A finding with `status=investigation`: a supported hypothesis requiring the
  stated controlled experiment.
- A finding with `status=confirmed`: allowed only when the diagnosis references
  a controlled comparison that isolates the cause with consistent results.

## Troubleshoot automatic diagnosis

| Symptom | Classification | Action |
| --- | --- | --- |
| Credential `deepseek-api-key` not found | Configuration | Create the Jenkins Secret text credential with the exact ID. |
| HTTP 401/403 | Credential/provider | Check the key and provider permission without printing the key. |
| HTTP timeout or DNS failure | Environment/provider | Check outbound HTTPS, DNS, and provider availability. |
| Empty `content` | Provider output | Let the caller retry up to three times; do not pass an empty response to JSON repair. |
| Malformed JSON or outer wrapper | Model output contract | Let the caller perform one structure repair and preserve raw output. |
| Placeholder markers after repair | Model output quality | Keep validation strict, generate deterministic fallback from evidence, and archive `callstack-diagnosis.fallback.json` for audit. |
| Revision or target mismatch | Fixed metadata | Copy the values from evidence; do not trust the model value. |
| Empty or invented source location | Diagnostic integrity | Derive it from cited evidence function IDs and verify a unique source anchor. |
| Unknown evidence function ID | Model evidence error | Reject or repair the finding; do not silently drop the reference. |
| Confirmed finding without controlled evidence | Unsupported conclusion | Downgrade to `investigation` and require a falsifiable experiment. |
| Duplicate generic suggestions | Low-quality diagnosis | Merge the path or rewrite mechanism-specific changes. |

Do not lower validation requirements merely to turn an unstable build green. The
fallback path is intentionally conservative: it only emits `status=investigation`
findings derived from measured evidence and still must pass the same renderer
validation.

## Verified reference run

Build `#22` validated the end-to-end path on
`skill/witty-ub-jenkins-ci` commit `c8f5df7`:

- Jenkins result: `SUCCESS`
- Functional checks: 23 passed, 0 failed
- Blue-zone GET UBM results: 10,240 of 10,240
- Scanner comparison: result consistency passed; single process was 17.3%
  faster than automatic mode under that run's controlled input
- Semantic diagnosis: 4 investigation findings, 0 confirmed
- Verified source locations: 12
- HTTP baseline: 300 of 300 successful, P95 26.676 ms
- Short stability: 600 requests, 0 failures, 0 restarts
- Published immutable tag:
  `hub-harbor.oepkgs.net/neocopilot/witty-ub:skill-witty-ub-jenkins-ci-22-c8f5df7`
- Published digest:
  `sha256:f8e64acbe2ef1663971281702582a1828f48f7b5209f6b792f2ba50f30aca8a9`

Treat these values as one verified baseline, not permanent thresholds or proof
that every performance hypothesis is confirmed.
