# Call-stack diagnosis prompt

Give the agent all of these inputs:

- the checked-out Witty-UB repository at the exact revision recorded in the evidence
- `callstack-evidence.json`
- `callstack-profile.prof` and `callstack-profile.txt`
- `callstack-comparison.json` and `callstack-comparison.md`
- relevant execution logs
- `assets/callstack-diagnosis.schema.json`
- `scripts/render_callstack_diagnosis.py`

Use this prompt in either supported mode:

- Automatic Jenkins mode: `scripts/call_deepseek_diagnosis.py` supplies the
  evidence, schema, and selected complete source files to DeepSeek.
- Portable agent mode: give Codex, Claude, or another code agent direct access
  to the checked-out repository and the listed artifacts.

A model that receives neither the source bundle nor repository access is not
sufficient. Do not send the original blue-zone log files or credentials.

---

Perform a source-linked Witty-UB performance diagnosis.

Work read-only. Do not modify product source, rerun services, connect to remote
systems, or claim a confirmed cause unless the supplied evidence includes a
controlled validation result.

1. Confirm that the evidence source revision matches the repository revision.
2. Read the scanner-mode comparison first. Reject its timing conclusion if any
   result count differs, and treat three rounds as a quick decision rather than
   a production-default confirmation.
3. Read all three profile views: cumulative time, self time, and call count.
4. For each important path, inspect the supplied source context and then open
   the complete functions in the repository.
5. Trace from the public worker entry through orchestration into leaf work and
   external runtime calls. A wrapper with high cumulative time and near-zero
   self time is not itself a root cause.
6. Separate:
   - observed profile facts
   - source-supported causal mechanism
   - user impact
   - proposed implementation
7. Assign one direct cause pattern to every finding:
   - `algorithmic_complexity`: state the exact before/after complexity, such as
     nested lookup `O(n²)` to indexed lookup `O(n)`
   - `repeated_work`: name what is repeated and how many stages or calls repeat it
   - `process_overhead`: write a cost formula that separates fixed startup/IPC
     cost from data-dependent work
   - `io_wait`, `lock_contention`, `serialization_overhead`,
     `database_query`, `memory_allocation`, or `other`
   Do not force `O(n²)` onto a fixed-overhead or I/O problem. For those cases,
   use a truthful cost model such as `3 × (C_spawn + C_ipc + O(N))`.
8. Fill `cause_pattern.plain_cause`, `cost_model`, `before`, and `after` in
   language a developer can act on without reading the later call-chain section.
9. Merge multiple wrappers that describe the same causal path into one finding.
10. Use `status=confirmed` only when a controlled baseline/variant comparison
   isolates the cause while holding the input, revision, resources, and result
   counts constant.
11. Otherwise use `status=investigation`. State one executable next experiment,
   the variables held constant, the measured fields, and the numerical rule
   that would confirm or reject the hypothesis.
12. Make every recommendation implementation-specific:
   - name the target file and symbol
   - describe the exact control-flow or data-flow change
   - explain why that change affects the measured mechanism
   - list correctness/concurrency/memory risks
   - provide a same-input benchmark and correctness invariants
   Put the primary change site first in `source_locations`; the report uses that
   first entry in its mentor-facing summary.
13. Do not repeat generic advice such as “consider caching, batching, or
    optimizing I/O” unless the named source operation and profile evidence
    establish that exact mechanism.

Write `callstack-diagnosis.json` conforming to
`callstack-diagnosis.schema.json`. Then run:

```bash
python3 <skill-dir>/scripts/render_callstack_diagnosis.py \
  --evidence callstack-evidence.json \
  --diagnosis callstack-diagnosis.json \
  --source-root <repository-root> \
  --json-report callstack-diagnosis.validated.json \
  --markdown-report callstack-diagnosis.md
```

Delivery is valid only when:

- every evidence function ID exists
- every source anchor resolves uniquely
- summary counts match the findings
- confirmed findings contain controlled validation
- investigation findings contain a falsifiable next experiment
- duplicated template recommendations are absent

---
