# 全部特征：混合 K4 LOO 与分类器随机留出

当前部署默认已切换为“新增数值特征（统一单位）＋分类器”，全特征余弦 K4 为退化；
部署说明见 case-matching skill 的 `references/DEFAULT_LABEL_POLICY.md`。
下文 v5/v6 表格和命令描述历史评估协议，不自动改写历史结果。

公共特征与推理代码在 `witty_ub_diagnostician/skills/case-matching/scripts/`。
本目录负责冻结输入、持久化划分、训练、评估、核验和汇总。所有数据和结果在仓库外。
本轮结果目录：`/home/witty-ub-logs/loo_1117_v5`，不改写 v4 结果。

## 同一特征、两种用途

两条路径都使用 `feature_vectors.build_observations`，包含基础标识、结构化分布/数值/相对时间、
核对事实、角色/事件/错误族/传输/交互/链、机制、遥测、去身份词语/短语、进程/主机影响和静态组件。
身份、目录场景名、绝对日期、报告答案和采集文件数不进入新增向量。

K4 保留旧底座与 BM25/角色/范围各 0.05，另加 16 个家族相似度的固定总预算 0.30，
各 0.01875，未知比较为零增量。然后沿用 K4、margin=0.05，不用结果挑权重或 K。
分类器直接使用同一观测向量；另有“全部观测＋分标签检索统计”对照。
基础观测分类器只使用兼容标识/语义，作为输入增量的参照。

Agent 默认走全部特征 K4。分类器须显式提供模型，不自动接管默认诊断；
两条路径的报告调用见 skill 的 `references/FIXED_FEATURE_MATCHING.md`。
候选的 `raw_observations` 与 `structured` 旁车必须真实存在；缺失保持未知。
实验会导出可直接传给 Agent 的候选信封，完整复现验证必须用训练来源候选。

## 实验协议

输入仍为 reports/train 与 reports/v7，合并五类范围内 474 份报告、514 个故障候选；
87 份仅有 Coordinator/UB 管控面故障的报告按原范围排除。
报告级单标签命中任一外部 GT 即算正确；不是逐故障归属准确率。

1. K4 只做所有数据混在一起的全量来源留一：基础 K4、原三个增量 K4、全部特征 K4。
2. 分类器随机分组留出：固定 seed=1717，使用打乱的五折分层来源组的第一个折作验证，约 80/20。
   多标签报告以最少见 GT 标签为分层主类。实际为 379 份训练、95 份验证。
3. `split.json` 在任何拟合之前保存来源、索引、组、分层标签和训练集内部折；复用时核对输入哈希，不能换种子挑成绩。
4. 训练集内部 3 折选配置，固定网格为 Logistic C=0.1/1/10、ExtraTrees depth=6/12；
   每种输入单独按内部命中数选配置，并列按固定顺序。每折词表、缩放、候选库、IDF、先验和权重只用本折训练来源。
5. 最终模型只使用 379 份训练来源拟合，验证集不选配置。另在相同 95 份验证报告、相同训练候选库上计算三种 K4，公平比较。
   训练样本构建检索特征时也排除其自身及同源历史案例。
6. 本轮不做模型 LOO，不在评估后用 474 份全量重训导出模型。训练集表现与验证成绩分开列出。

每种分类器输入都在同一参数网格内选择配置，最终模型类型可能不同；对比体现整条建模管线，而非单一特征的因果收益。
本批数据曾用于方案探索，本次随机留出也不能当作从未研究过的新数据独立测试。

## 运行与核验

从仓库根执行：

```bash
python3 -m venv /tmp/witty-ub-rerank-venv
/tmp/witty-ub-rerank-venv/bin/python -m pip install -r scripts/fault_label_loo/requirements.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/witty-ub-rerank-venv/bin/python \
  scripts/fault_label_loo/compare_paths.py \
  --prepared /home/witty-ub-logs/loo_1117_v4/inputs/prepared.json \
  --raw /home/witty-ub-logs/loo_1117_v4/preflight/verified_features/raw_observations.json \
  --reports-root /home/witty-ub-logs/reports \
  --gt-labels /home/witty-ub-logs/gt_labels.json \
  --out /home/witty-ub-logs/loo_1117_v5
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/witty-ub-rerank-venv/bin/python \
  scripts/fault_label_loo/validate_comparison.py --root /home/witty-ub-logs/loo_1117_v5
python3 scripts/fault_label_loo/summarize_comparison.py --root /home/witty-ub-logs/loo_1117_v5
```

`--stage prepare/k4/classifier/all` 可分阶段执行；复用结果须满足同一输入和源码哈希。
需要新的独立实验时使用新输出目录，不能覆盖或重抽本轮验证划分。
`validate_comparison.py` 重放全部 K4，通过 Agent 公共入口核对；再独立重拟合训练内 45 个配置/折组合，
核对配置选择与隔离；复核训练/验证所有可移植分类器输出和全部指标。

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/witty-ub-rerank-venv/bin/python \
  -m unittest discover -s scripts/fault_label_loo/tests -v
```

测试覆盖新增原始特征真正影响 K4、未知与实测零、同源隔离、固定划分、训练词表隔离、
可移植推理、本地/HTTP/报告一致性以及显式分类器报告。

## 产物

- `report.html`、`summary.json`、`comparison.csv`：按协议分开的对照表。
- `split.json`、`split.csv`：持久化训练/验证划分与内部折。
- `k4_loo/`：474 条混合数据的三种 K4 预测和指标。
- `classifier/`：训练/验证预测、内部选参、三个训练来源模型。
- `agent/cases_train.json`：复现验证和显式分类器调用用的训练来源案例。
- `agent/cases_all.json`：默认 K4 使用的全部历史候选；不能用于复现严格留出验证。
- `feature_coverage.json`、`manifest.json`、`source_snapshot/`、`validation.json`：特征、输入、代码和核验。

`prepare_*`、`verify_fixed_features.py` 仍支持从原始日志生成与逐值核对观测缓存。
`eval_loo.py/validate_loo.py/summarize_loo.py` 是仅 K4 的单路径入口，完整对照以 compare_paths.py 为准。
历史模型/训练暴露结果保存在 `/home/witty-ub-logs/loo_1117_v4/classifier_archive/`，不混入本轮指标。

## 真实标签监督的特征挖掘

运行时的候选提取器、显式推理入口位于 case-matching skill；本目录只负责离线训练和评估。
默认 v5 模型、Agent 策略、原始报告和 379/95 划分均不被这些实验替换。
研究说明见 `witty_ub_diagnostician/skills/case-matching/references/SUPERVISED_FEATURE_MINING.md`。

第一轮比较角色/组件词语、INFO、消息模板、数值、相邻模式与组合：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/witty-ub-rerank-venv/bin/python \
  scripts/fault_label_loo/mine_label_features.py \
  --reference /home/witty-ub-logs/loo_1117_v5 \
  --data-root /home/witty-ub-logs/data --reports-root /home/witty-ub-logs/reports \
  --gt-labels /home/witty-ub-logs/gt_labels.json \
  --out /home/witty-ub-logs/loo_1117_v5/feature_mining
```

第二轮修正带单位的小数，补充阶段/状态分布、显式成功失败对照与相对时间窗。
它复用第一轮的去身份词语和模板缓存，因此输出目录位于第一轮目录之下：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/witty-ub-rerank-venv/bin/python \
  scripts/fault_label_loo/mine_label_features_v2.py \
  --reference /home/witty-ub-logs/loo_1117_v5 \
  --data-root /home/witty-ub-logs/data --reports-root /home/witty-ub-logs/reports \
  --gt-labels /home/witty-ub-logs/gt_labels.json \
  --out /home/witty-ub-logs/loo_1117_v5/feature_mining/unit_conditioned_v2
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/witty-ub-rerank-venv/bin/python \
  scripts/fault_label_loo/validate_feature_mining.py \
  --reference /home/witty-ub-logs/loo_1117_v5 \
  --root /home/witty-ub-logs/loo_1117_v5/feature_mining/unit_conditioned_v2 --revision 2
/tmp/witty-ub-rerank-venv/bin/python scripts/fault_label_loo/report_feature_mining.py \
  --reference /home/witty-ub-logs/loo_1117_v5 \
  --root /home/witty-ub-logs/loo_1117_v5/feature_mining/unit_conditioned_v2 --revision 2
```

第一轮核验/报告使用同样入口，将 `--root` 改为 `feature_mining`、`--revision` 改为 `1`。
代码、日志、输入、划分、GT 哈希及训练内选择随结果持久化；复现时使用相同源码和依赖版本。
`training_selection.json`、`primary_selection.json` 先于验证推理保存。主方案按训练内部成绩决定，
验证最高的一行仍只是消融观察，不替换主方案。K4 行使用新表示的余弦评分，另标注有无训练标签监督的度量选择。
这些对照是随机留出开发研究，不能当作全量混合 LOO 成绩，也不宣称是从未研究过的独立验证数据。

`report.html`、`comparison.csv`、`pattern_evidence.json`、`primary_feature_effects.json` 分别提供结果、
训练模式的真实标签支持和主模型贡献；`refit_validation.json` 记录独立重拟合和验证预测重放结果。
第一版小数与单位解析不足，保留作原型；第二版数值表示用于后续候选研究。

映射方法对照与三轮汇总：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/witty-ub-rerank-venv/bin/python \
  scripts/fault_label_loo/compare_feature_mappings.py \
  --reference /home/witty-ub-logs/loo_1117_v5 \
  --context-root /home/witty-ub-logs/loo_1117_v5/feature_mining/unit_conditioned_v2 \
  --reports-root /home/witty-ub-logs/reports --gt-labels /home/witty-ub-logs/gt_labels.json \
  --out /home/witty-ub-logs/loo_1117_v5/feature_mining/mapping_comparison
python3 scripts/fault_label_loo/summarize_feature_research.py \
  --reference /home/witty-ub-logs/loo_1117_v5 \
  --root /home/witty-ub-logs/loo_1117_v5/feature_mining
```

映射对照固定使用训练内支持≥3、chi2 前 1000 维，比较线性/核 SVC 和 ExtraTrees，
因此与 Logistic 的差异同时包含预处理选择；四个模型均保存后重放并独立重拟合核对预测。
三轮入口为 `feature_mining/research_report.html`，原 `loo_1117_v5/report.html` 不改写。

## 新特征的全量来源 LOO（v6）

`eval_feature_loo.py` 将上述随机留出研究改为全量来源留一对照：7 种表示各做完整 LOO，
每折从其余来源重新拟合 Logistic，并用同折词表/缩放计算无监督余弦 K4。
因此每种表示有 474 套折内权重，成绩评估这套特征/训练方法，不是某一套全量冻结权重的测试成绩。
全量冻结权重只能用未参与训练的新数据验证，不能将本批训练集回归表现当作该模型的泛化成绩。
配置在开始前固定：v5、第二版数值 C=1；数值原型、模板、顺序组合、行为合并、全表示合并 C=0.1。
不同表示的 C 沿用此前开发配置，因此这不是单变量特征消融；不依据本轮成绩再选参数。
这次不增加嵌套选参，也不载入全量训练权重。每折模型、候选来源及划分持久化。

输入覆盖 train/v7 的全部 561 份报告，延续五类范围评估 474 份；其余 87 份仅管控面报告单列排除。
来源留一还排除同源、别名和完整日志相同来源。原始日志重新计算解压后内容哈希，缓存必须匹配相同提取器与输入。

从仓库根执行（初次运行使用空的新输出目录；已有结果的源码与输入清单必须严格一致）：

```bash
python3 scripts/fault_label_loo/eval_loo.py \
  --prepared /home/witty-ub-logs/loo_1117_v5/inputs/prepared.json \
  --raw /home/witty-ub-logs/loo_1117_v5/inputs/raw_observations.json \
  --reports-root /home/witty-ub-logs/reports --gt-labels /home/witty-ub-logs/gt_labels.json \
  --out /home/witty-ub-logs/loo_1117_v6/default_k4
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/witty-ub-rerank-venv/bin/python \
  scripts/fault_label_loo/eval_feature_loo.py \
  --reference /home/witty-ub-logs/loo_1117_v5 \
  --context-root /home/witty-ub-logs/loo_1117_v5/feature_mining/unit_conditioned_v2 \
  --reports-root /home/witty-ub-logs/reports --data-root /home/witty-ub-logs/data \
  --gt-labels /home/witty-ub-logs/gt_labels.json --out /home/witty-ub-logs/loo_1117_v6 --jobs 8
python3 scripts/fault_label_loo/validate_loo.py --run /home/witty-ub-logs/loo_1117_v6/default_k4
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/witty-ub-rerank-venv/bin/python \
  scripts/fault_label_loo/validate_feature_loo.py --out /home/witty-ub-logs/loo_1117_v6 --jobs 8
python3 scripts/fault_label_loo/report_feature_loo.py --out /home/witty-ub-logs/loo_1117_v6
```

核验会检查全部折模型的训练来源、词表和缩放，重放全部分类器输出及新表示 K4；
另独立重拟合预设的首/中/末折和各标签首例，核对参数及预测。
其中用于检查的全数据统计不参与任何模型拟合。
`report.html`、`comparison_summary.json`、`comparison.csv`、`errors.csv` 是汇总；
`folds.json`、`fold_audits/`、`models/<表示>/<折号>.json.gz` 保存划分、审计和逐折权重。
这批数据已用于方案开发，结果是本批来源 LOO，不能当作新采集数据的独立测试。默认 Agent 不自动切换。
本次混合库来源留一允许同场景的其他来源进入训练，不是跨场景留出测试。

## 构建随 skill 打包的部署资源

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/witty-ub-rerank-venv/bin/python \
  scripts/fault_label_loo/build_runtime_assets.py \
  --reference /home/witty-ub-logs/loo_1117_v6 \
  --context-root /home/witty-ub-logs/loo_1117_v5/feature_mining/unit_conditioned_v2 \
  --reports-root /home/witty-ub-logs/reports --gt-labels /home/witty-ub-logs/gt_labels.json \
  --out witty_ub_diagnostician/skills/case-matching/assets/default_label_policy
```

这里仅训练一套全量部署模型（Logistic C=1，numeric_units）并打包参考库，
不挑选某个 LOO 折的权重，不把训练表现当作新的独立测试成绩。
资源为标准库可读的 JSON.gz，模型、参考来源向量和文件/版本校验均在 skill 内。
普通 Agent 不读取实验目录或训练依赖，不在生成报告时拟合。

用既有折内模型核对实际运行时协议（不会用部署全量权重评估旧数据）：

```bash
python3 scripts/fault_label_loo/verify_runtime_policy.py \
  --reference /home/witty-ub-logs/loo_1117_v6 \
  --context-root /home/witty-ub-logs/loo_1117_v5/feature_mining/unit_conditioned_v2 \
  --out /home/witty-ub-logs/loo_1117_v6/deployment_validation --jobs 8
```

此核验重放数值分类器与全特征余弦 K4，并单独记录缺数值时的混合退化结果。
历史默认 K4 仍由 `fixed_matching.py` 明确调用，普通报告/本地/HTTP 最终决策改用 `default_matching.py`。
