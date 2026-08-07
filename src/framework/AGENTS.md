# Framework — Shared C++ Libraries

## OVERVIEW

Four static libraries consumed by all 5 C++ executables. Shared headers in `../include/`.

## STRUCTURE

```
src/framework/
├── CMakeLists.txt              # add_subdirectory for all 4 libs
├── context/                    # ubse_context — singleton, ALL 5 executables
│   ├── ubse_context.{h,cpp}    #   Module registry, topo-sort dep resolution, CLI arg parse
├── com/                        # rack_http — HTTP server/client, 3 executables
│   ├── common/                 #   RackHttpModule lifecycle wrapper
│   ├── http/                   #   cpp-httplib wrapper
├── database/                   # database — SQLite CRUD, BUILT but 0 executables link it
│   ├── database.{h,cpp}        #   Legacy from commented-out copilot-worker
├── json-io/                    # witty_json — thread-safe JSON writer, 1 executable
│   ├── witty_json.{h,cpp}      #   flock + atomic rename, witty_json_module
└── ../include/                 # 7 shared headers, every .cpp includes ≥2 of them
    ├── logger.h                #   log4cplus macros
    ├── rack_module.h           #   Abstract base: Initialize/Start/Stop/UnInitialize
    ├── rack_error.h            #   Error code enum
    ├── failure_def.h           #   Failure event struct
    ├── node_data_def.h         #   Node data struct
    ├── urma_data_def.h         #   URMA data struct
    └── code_analyzer_def.h     #   Code analysis data struct
```

## WHERE TO LOOK

| Library | Files | Used By | Function |
|---------|-------|---------|----------|
| ubse_context | context/ubse_context.{h,cpp} | ALL 5 exes | Module registry, lifecycle orchestration, arg parse |
| rack_http | com/common/*, com/http/* | witty-ub-log, witty-ub-topo, util-code-analyzer | HTTP server/client via cpp-httplib |
| witty_json | json-io/witty_json.{h,cpp} | witty-ub-topo only | Thread-safe JSON I/O with file locks |
| database | database/database.{h,cpp} | NONE currently | SQLite wrapper (legacy, kept for future use) |

## KEY PATTERNS

**RackModule lifecycle**: `Initialize(args) → Start() → Stop() → UnInitialize()`. Pure virtuals on abstract base. Modules auto-register with UbseContext via `AutoRegister<T>` CRTP. UbseContext topo-sorts dependencies, calls lifecycle in order.

**Static libraries**: All `add_library(... STATIC)`. No shared objects. Linked directly into each executable's CMake target.

**Executable dependency graph**:
```
witty-ub-log          → ubse_context + failure_log + rack_http
witty-ub-topo         → ubse_context + topology + lcne + rack_http + urma + witty_json
witty-ub-diag-tool    → ubse_context + diagnosis_tool
util-code-analyzer    → ubse_context + code_analyzer + rack_http
util-view-visualizer  → ubse_context + view_visualizer
```

## NOTES

- `ubse_context` and `rack_http` are the most cross-cutting: context hits all 5, rack_http hits 3 of 5.
- `database` is compiled but unlinked. If reactivated, add `target_link_libraries` in the consuming executable.
- Every new executable MUST register modules through UbseContext — the singleton pattern is non-negotiable.
- Do NOT add framework dependencies to `../include/` headers; those are data-definition-only, no logic.
