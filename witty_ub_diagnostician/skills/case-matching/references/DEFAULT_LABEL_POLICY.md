# 默认标签策略：新增数值特征分类器＋全特征余弦 K4 退化

普通诊断统一调用 `scripts/default_matching.py`，策略标识为
`numeric-units-classifier-cosine-fallback-v1`。无需指定模型或实验目录。

## 正常报告生成

```bash
python3 ../diagnostic-report-generation/scripts/generate_report.py \
  /path/draft.json /path/report.html --log-dir /path/raw_logs
```

此命令实际提取日志观测，计算新增数值分类器和全特征余弦 K4，并渲染报告。
不传 `--cases` 时使用 skill 内置的带标签参考库；传入时使用指定候选，
`--api-base` 则明确从案例 API 读取候选。渲染器仍执行原报告契约校验。
`--labels-only` 导出同一路径生成的标签 JSON；`--classifier-model` 仅用于显式覆盖。

默认资源全部在本 skill 的 `assets/default_label_policy/`：

| 文件 | 作用 |
| --- | --- |
| `numeric_classifier.json.gz` | 全部 474 份开发报告拟合的部署模型，Logistic C=1，标准库推理 |
| `cosine_bank.json.gz` | 474 个来源、514 个故障候选的全特征观测及参考标签 |
| `manifest.json` | 文件校验、特征版本、训练来源与用途说明 |

运行时不读取 `/home/witty-ub-logs`、仓库根 `scripts/`、GT 或 sklearn，
也不使用 v6 的 474 套逐折权重；那些权重仅是历史评估记录。
部署模型是一次全量拟合，不代表有新的独立测试成绩；79.96% 是 v6 的逐折重训数值分类器成绩。
普通诊断不会训练或更新权重。报告中记录 `model_id` 和真实采用的路径。

## 特征和退化条件

`mined_log_features_v2.scan` 从真实 I/W/E 消息列提取角色/组件/阶段上下文。
主模型只使用 `numeric_units`：统一单位耗时/大小、样本数、均值/极值、对数分布和近似分位桶。
它不叠加基线、词语、模板或事件组合。标签、报告结论、根因文字、文件夹场景名不进入特征。
保持 v6 同版单位规则：显式 ns/us/ms/s 等单位会转换，裸字段仅推断 us/ms 后缀；
其他未识别单位的裸值保留为 `value`，不假定为微秒。扩展单位规则须升级提取器并重建部署资源。

每次同时计算 `all_context_v2` 的余弦 K4，作为历史案例参照和退化结果：
基线观测＋新增数值＋阶段/显式状态＋成功失败对比＋相对时间窗＋上下文词语、模板和组合。
仅从过滤后的参考来源确定词表和 MaxAbs 缩放，不使用分类器系数；K=4、margin=0.05。
同来源、别名和完整日志内容相同的参考来源在投票前排除，身份只用于排除，不成为匹配键。

以下情况选择余弦 K4，并记录 `fallback_reason`：

- 没有可用数值观测，或数值键全部不在冻结模型词表内。
- 默认分类器文件缺失、损坏或版本不兼容。
- 多故障报告需要逐故障归属，缺少独立故障日志时使用下述多故障规则。

没有可比观测或参考候选时保持空标签，不把缺失解释为健康，也不按类别先验强行输出标签。
明确的用户使用问题故障码规则仍优先。模型分数未做置信度校准，不能直接作为根因正确概率。
API 新候选若没有完整观测，按已知部分比较，不从标签或根因文字补造数值、模板或日志。

## 单故障与多故障

报告级结果写入顶层 `label_matching`。其 `decision` 是实际采用的标签，
`retrieval_decision` 为余弦 K4 参照；`feature_usage`、模型 ID、观测哈希和退化原因可追溯。

- 单故障：采用报告级主预测；主模型不可用时采用余弦 K4。同步更新该故障的一级标签。
- 多故障：报告级分类器照常运行并展示总体预测；不把同一总体预测复制给所有故障。
  每个故障以自身结构化观测＋共享报告日志计算全特征余弦 K4，记录
  `multiple_faults_require_fault_scoped_evidence` 和实际观测作用域。
  这是当前的逐故障退化口径，不宣称已有 79.96% 的逐故障归属准确率。

一级标签改变时清空不适用的二级标签；细粒度根因仍需现场证据。
模板展示报告级标签预测及数值分类/余弦退化来源，原渲染器校验结论标签与策略输出一致。
报告级预测在页头展示，各故障的一级/二级标签仍在各故障档案中。
分类器与同作用域的 K4 结果不一致时记录 `disagreement=true` 并在页头提示；
分类器仍按主路径采用，不因不一致本身触发退化，不比较未经校准的模型分数与余弦分数。
多故障的总体预测与某条故障标签不同属于作用域差异，不能据此将所有故障改成同一类。

## 观测导出和调用

```bash
python3 scripts/match_baseline.py --report /path/report.json \
  --log-dir /path/raw_logs --out /tmp/query.json
python3 scripts/match_baseline.py --query /tmp/query.json \
  --cases /path/cases.json --out /tmp/matches.json
```

导出 `.structured.json`、`.raw.json`、`.mined.json`，本地/HTTP 匹配自动读取旁车。
`match_cases.py` 通过同一 `default_matching.match` 作最终标签决策。
旧的 `fixed_matching.py`、[固定 K4 说明](FIXED_FEATURE_MATCHING.md)保留给历史对照，
不作为普通报告的默认决策。

部署资源构建、重训和评估在仓库根 `scripts/fault_label_loo/` 维护，
只有导出的冻结模型/参考库和推理代码进入 skill。更新数据后须离线重建资源，不能在报告流程里自动拟合。
