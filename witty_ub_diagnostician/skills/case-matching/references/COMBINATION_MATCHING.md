# Agent 候选评分底座

普通调用使用[新增数值分类器＋全特征余弦 K4 退化](DEFAULT_LABEL_POLICY.md)。本页仅说明历史兼容评分加 BM25、角色、范围各 0.05 的底座；下文“默认增量”指该旧评分模块内部默认值，不代表当前报告标签策略。
用户和agent不需要选择通道、底座或算法参数。CLI不提供`--combine`、`--base`或对应local参数。

## 普通使用

```bash
python3 scripts/match_baseline.py --report /path/report.json \
  --log-dir /path/raw_logs --out /tmp/evidence.json
# 自动同时写出 /tmp/evidence.structured.json 和 /tmp/evidence.raw.json。

python3 scripts/match_baseline.py --query /tmp/evidence.json \
  --cases /path/cases.json --out /tmp/matches.json

# 原检索脚本的本地路由执行同一默认策略：
python3 scripts/match_cases.py /tmp/evidence.json \
  --local-cases /path/cases.json --json /tmp/matches.json
```

查询旁车自动按`<query stem>.structured.json`读取；已有观测位于其他路径时，`--structured-query`仅指定输入文件，
不选择算法。候选信封为`{cases:[{id,source_id,label,profile,structured}]}`。
原HTTP检索入口也自动应用相同增量策略；query可带`structured`对象或同名旁车，候选读取自身`structured`字段。

候选缺少结构化观测时，不从根因、标题、标签、文件名或场景名补造角色/范围。相应通道为未知，增量为0。
只有真实提供的候选观测参与新增通道的统计；不能把缺少旁车解释成该候选没有事件或系统健康。
服务端当前不会自动持久化任意sidecar；历史案例需要真实观测才会有相应通道增益，不伪装为已经补齐。

LOO调用方仍先排除源报告和同日志全部版本。CLI支持`--exclude-source-id`，原路由对应
`--local-exclude-source-id`；调用方负责发现别名。身份只用于排除，GT只用于评估，不能选配置或计分。
管控类在候选统计前剔除。本地匹配不联网、不确认/建案、不回写命中；HTTP检索仍遵守主SKILL的来源与确认纪律。

## 共用实现

`combination_matching.py`提供候选评分入口，不负责当前最终标签决策：

- `rank_default(query,cases,query_structured=None)`，或`baseline_matching.rank(...)`不指定experiment。
- `apply_default(rows,query_structured,case_structured)`：为已经算好的无报告文本底座排序加入相同默认增量。
- `DEFAULT_BASE='baseline'`、`DEFAULT_FEATURES=('bm25','actor','scope')`在代码中固定，不按目录或真值自动切换。

底座保留旧错误码F1、模式/阶段累计、候选池标签先验和语义IDF。
新分为`底座原分 + fsum(0.05 × 所选观测相似度)`；未知增量为0，不替换原分母、不重复加先验/语义、不加入拓扑。
分数并列保留底座原顺序。输出保留L1/L2/L5等解释及各通道值/增量，分数不是正确概率，也不代替现场核对。

最终标签统一由 `fixed_matching.match/decide`输出，普通CLI自动调用；报告标签和答案文字不会进入查询profile。原HTTP入口的报告query_text和log_keywords文字不用于默认排序。
导出/匹配输入规范见[证据导出](../../diagnostic-report-generation/references/EVIDENCE_EXPORT.md)。

## 离线实验边界

本页仅说明 Agent 候选评分。LOO 与观测校验由
仓库根目录的 `scripts/fault_label_loo/`维护，不属于 skill 的调用流程。
