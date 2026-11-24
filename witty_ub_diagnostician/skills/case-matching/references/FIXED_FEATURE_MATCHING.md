# 全部特征的 K4 与显式分类器

> 本页保留 v5/v6 的旧固定 K4 对照说明。普通诊断默认已切换到
> [新增数值分类器＋全特征余弦 K4 退化](DEFAULT_LABEL_POLICY.md)；下文旧命令仅用于历史方案复现。

观测提取与向量构建由 `fixed_observations.py`、`feature_vectors.py` 共用。
默认一级标签为 `fixed_matching.py` 的全部特征评分与 K4，策略 `all-feature-vote-v1`。
分类器是显式可选方案，策略 `all-feature-classifier-v1`；默认调用不会加载模型权重。

## 导出和默认匹配

在本 skill 的 scripts 目录执行：

```bash
python3 match_baseline.py --report /path/report.json --log-dir /path/logs --out /tmp/query.json
python3 match_baseline.py --query /tmp/query.json --cases /path/cases.json --out /tmp/result.json
```

导出基线、`.structured.json` 和 `.raw.json`。匹配自动读取已有旁车。
历史候选信封为 `{cases:[{id,source_id,label,profile,structured,raw_observations}]}`；
标签只在历史案例信封，不进入查询观测。原始观测来自真实日志，不从报告答案补造。
历史候选缺少结构化或原始观测时，相应比较为未知、增量为零；不能从标签反推特征。
HTTP 入口也读取案例的 structured/raw_observations 字段；后端未保存这些字段时不会自动补造。
需要完整复现实验时，使用实验导出的 `agent/cases_all.json` 或 `agent/cases_train.json`。

## 所有特征如何使用

`feature_vectors.build_observations` 是两条路径共同的观测入口。

| 观测 | K4 路径 | 分类器路径 |
| --- | --- | --- |
| 错误码、故障模式、阶段、操作、日志语义、角色 | 保留兼容底座及原 BM25/角色/范围通道 | 相应标识/数值向量 |
| GET/SET 逐码分布、桶、计数与完整性、数值、相对时间 | 分布、数值、时间家族相似度 | 相同观测值和已知标记 |
| 核对事实、机制、事件、错误族、传输、交互、事件链、观测范围 | 对应家族相似度 | 相同观测向量 |
| 原始遥测、事件计数 | telemetry 数值比较 | 相同遥测向量，max 数值 log1p |
| 去身份词语与短语 | 候选来源统计的 IDF 余弦 | 相同去身份词/短语向量 |
| 进程/主机影响比例、进程计数、相对跨度 | structure 数值及覆盖比较 | 相同观测向量 |
| 静态软件组件 basename | components 余弦 | 相同组件比例向量 |

K4 在旧评分加 BM25/角色/范围各 0.05 的基础上，对 16 个观测家族固定增加总预算 0.30，
各家族 0.01875。公式在实验前固定，不根据留一或验证成绩调权重。
数值比较使用共同已知项的距离及覆盖；未知不是健康，不补造零。
词语统计仅使用当前过滤后的历史候选来源，不纳入查询或验证来源。
代码位置、IP、Pod/主机/集群名字、PID、对象键、trace ID、绝对日期和报告答案不成为向量特征。
组件只使用静态 basename；身份仅用于来源排除与观测数量/比例统计。采集文件数不进入新增向量。

候选排序后，前两名分差大于 0.05 时取第一名标签，否则前 4 个故障案例等权投票。
无候选保持空标签，明确误操作错误码沿用共用知识规则。
`decision` 保留投票分支与支持案例，候选的 `all_feature_values/delta/coverage` 可复核各家族贡献。
分数不是诊断正确概率，采纳案例仍须做现场核对。

## 显式分类器与 Agent 报告

默认报告仍用全部特征 K4：

```bash
python3 ../diagnostic-report-generation/scripts/generate_report.py /path/draft.json /tmp/report.html \
  --cases /home/witty-ub-logs/loo_1117_v5/agent/cases_all.json --log-dir /path/logs
```

用户明确指定分类器时传入模型：

```bash
python3 ../diagnostic-report-generation/scripts/generate_report.py /path/draft.json /tmp/model-report.html \
  --cases /home/witty-ub-logs/loo_1117_v5/agent/cases_train.json --log-dir /path/logs \
  --classifier-model /home/witty-ub-logs/loo_1117_v5/classifier/models/all_observations.json
```

分类器共用同一观测向量，可仅用全部观测，或另加分标签候选分数/分差/支持比例等检索统计。
`classifier_matching.py` 做输入构建和显式推理，`portable_classifier.py` 用标准库执行导出权重；
诊断时不训练模型、不搜索特征和超参数。模型必须声明兼容的 feature_version。
全部输入、推理路径与观测来源写入 label_matching；分类器另记录 model_id。
报告每个故障按 fault_index 调用同一提取器；本次离线成绩为报告级单标签口径，不能当作逐故障准确率。
一级标签改变后清空不适用的二级标签，后续细分仍依赖真实证据和有效标签对。

## v5 评估边界

流程在仓库根目录 `scripts/fault_label_loo/compare_paths.py`，结果在 `/home/witty-ub-logs/loo_1117_v5`。
K4 只做 train/v7 合并的完整来源留一。分类器按来源分组随机留出，split.json/split.csv 持久化；
训练集内部 3 折选配置，候选库、IDF、词表、缩放与权重只使用相应训练来源。
验证集不选择权重、配置或随机种子。模型只用训练部分拟合，不在验证后全量重训。
同时在同一验证集/训练候选库上计算 K4，用于与分类器公平对比。
本轮不再做模型 LOO。历史 77% 和 92.83% 属于不同方案和协议，不混入本轮成绩。
本批数据曾用于方案探索，本次随机留出也不能当作从未研究过的新数据独立测试。

匹配、可移植推理仅需 Python 标准库；报告渲染另需 Jinja2。
训练依赖仅在离线脚本中，Agent 不依赖仓库根 scripts 或实验目录代码。
