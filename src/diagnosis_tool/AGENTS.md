# diagnosis_tool

Static library (`libdiagnosis_tool.a`) providing fault diagnosis for witty-ub. Links into `witty-ub-diag-tool`.

## STRUCTURE

```
diagnosis_tool/
├── CMakeLists.txt                          # STATIC lib, GLOBs auto-generated sources
├── diagnosis_tool_module.{h,cpp}           # RackModule: Initialize/Start/Stop
├── failure_mode.{h,cpp}                    # Abstract base (7 virtuals), tree via AddSubFailureMode
├── failure_mode_factory.{h,cpp}            # Singleton registry + AutoRegister<T> CRTP
├── failure_mode_controller.{h,cpp}         # FailureMode + hitCount + traceId→FailureLogInfo map
├── failure_log_info.{h,cpp}                # FailureLogInfo base + Access/Runtime subtypes
├── failure_log_helper.{h,cpp}              # WildcardMatch, SplitView, timestamp parse
├── failure_mode_view.{h,cpp}               # Tree Build/Dump from controller map
└── failure_mode_realization/
    ├── urma/   urma_failure_{001..760}.{h,cpp}   # 760 pairs, DO NOT EDIT
    └── kvcache/ kvcache_conn_fault_*.{h,cpp}      # 40 pairs, DO NOT EDIT
```
14 hand-written files at root, 1600 auto-generated in `failure_mode_realization/`.

## WHERE TO LOOK

| Need | File |
|---|---|
| Entry lifecycle / pipeline | `diagnosis_tool_module.cpp` |
| Auto-registration | `failure_mode_factory.h` |
| Log parsing indices | `failure_log_info.h` |
| Mode evaluation | `failure_mode_controller.{h,cpp}` |

## KEY PATTERNS

### AutoRegister CRTP (CRITICAL)

Every auto-generated `.cpp` creates a static global that self-registers before `main()`:

```cpp
static AutoRegister<UrmaFailure001> g_urma("urma_001");
```

The executable MUST link with `--whole-archive` (`-force_load` on Apple). Without it the linker strips these unreferenced globals and `FailureModeFactory::Create(id)` returns nullptr for every ID.

### FailureMode interface

7 virtual methods: `GetName()`, `GetId()`, `IsValid(fields)`, `GetRootCauseDesc()`, `AnalyzeRootCause()`, `GetFixSuggDesc()`, `GetValidationMethodDesc()`. Tree via `AddSubFailureMode(id)` / `GetSubFailureModes()`.

### FailureLogInfo & helpers

`FailureLogInfo` (base) → `FailureLogInfoAccess` (+statusCode, action, cost, dataSize, reqMsg, respMsg) and `FailureLogInfoRuntime` (+message). Constexpr field indices in `failure_log_info.h`.

`diag::log_helper`: `SplitView()` (delimiter split), `WildcardMatch()` (glob), `FindTimestampT()` / `ToTimestampTBound()` (ISO 8601).

## PIPELINE

```
ParseDiagArgs() → ConfigureMergedPath() → ExtractLogsByTimeWindow()
→ BuildFailureModeTree() → BuildLogTypeToPathMap()
→ AnalyzeAccessLogs()          # 1st pass: KVCache root modes by HTTP status code
→ AnalyzeRuntimeLogs()         # 2nd pass: sub-modes + URMA modes by message content
→ MergeFailureModeByTraceId() → StoreFailureTraces()
→ GenerateFailureModeView()    # JSON tree dump to merged dir
```

## NOTES

- Auto-generated files regenerated via `.opencode/skills/diagnosis-code-generation-{urma,kvcache}/`. Never edit by hand.
- Failure mode hierarchy in `data/failure_mode_tree.json` (runtime), not hardcoded in C++.
- Depends on `ubse_context`, `jsoncpp`, `re2`. `log4cplus` linked at executable level.
- Entry: `src/witty_ub_diag_tool_main.cpp` creates `UbseContext`, registers `DiagnosisToolModule`.
