# 导出匹配用观测特征

已有报告用于案例匹配时，不必重生成报告。调用共用提取器导出独立特征文件：

```bash
python3 scripts/export_evidence.py --report /path/report.json \
  --log-dir /path/raw_logs --out /tmp/baseline.json
# 默认legacy-evidence-v1；单故障候选可加 --fault-index 0。
# 同时自动生成 .structured.json、.raw.json 和 .mined.json，匹配时自动读取。
```

默认导出调用 `baseline_matching.py` 与 `enhanced_matching.py`生成基线与结构化观测，
由 `fixed_observations.py`生成原始观测旁车，`mined_log_features_v2.py`生成数值/上下文观测。
两者均不读取报告结论/根因/
why/detail等自由文本，不联网、不渲染、不改写报告，也不确认或沉淀案例。
输入标签是否已写在报告中不会改变导出的观测profile；GT仅由LOO或案例信封读取。

基线sidecar只保留错误码、模式ID、阶段桶、兼容操作口径和原始日志语义轮廓，
保留旧评分/先验/IDF与K4能力。它不读取报告basic_info里的语义轮廓。
缺少日志时语义轮廓为空；需要复现旧语义能力时应传真实日志或使用LOO的显式冻结轮廓缓存。
结构化 sidecar 按 GET/SET分别保留错误分布、计数、other_count、完整性、桶key和同口径数值。
bucket_share是样本请求占比，不是物理耗时比例；未知不是0，不补P99、baseline或SET细分阶段。
日志只提取真实角色、事件、错误族、传输/回退及同trace事件顺序，不从场景文件夹推断根因。

扩展事实格式为 `{fact:{value:true|false,verified:true,evidence_ref:"来源指针"}}`。
允许pod_recreated/client_process_exit/worker_process_exit/disk_full/oom_kill；
只有真实日志、K8s事件或OS指标已核对后才填。没有观测不得按“没看到”填false。

profile作为sidecar随报告归档，来源、schema_version、提取器版本及哈希一起留存。
现有 `render_report.py` 的契约校验和已有案例确认链路保持适用；导出profile不替代JSON校验。
后端StageFeaturesModel仅支持既定子集，evidence-v1不会被自动复制到案例表。
如需生产库持久化这些新字段，先扩展schema及映射，再对未确认草稿执行真实数据回填。
不得直接修改冻结的confirmed内容或标签目录。

默认计算契约见 [观测匹配基线](../../case-matching/references/BASELINE_MATCHING.md)，
LOO 与观测校验工具在仓库根目录的 `scripts/fault_label_loo/` 维护。

普通匹配同时使用baseline.json、自动生成的baseline.structured.json和baseline.raw.json，候选信封分别保存`profile`与`structured`。
例如在case-matching的scripts目录执行：

```bash
python3 match_baseline.py --query /tmp/baseline.json \
  --cases /path/cases.json --out /tmp/matches.json
```

普通匹配以新增数值分类器为主，全特征余弦 K4 为参照和退化；缺少日志数值时明确记录退化原因。
计算和运行资源见[默认匹配策略](../../case-matching/references/DEFAULT_LABEL_POLICY.md)。

新报告通过 `scripts/generate_report.py`完成默认标签选择再渲染；外部实验与运行时共用特征和推理实现。
