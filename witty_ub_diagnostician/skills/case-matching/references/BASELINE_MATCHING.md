# 封闭观测输入与候选评分底座

普通诊断的最终标签使用[数值分类器与余弦 K4 默认方案](DEFAULT_LABEL_POLICY.md)。本页仅描述旧兼容观测与评分底座，不作为当前默认决策说明。

本页说明[固定特征匹配方案](FIXED_FEATURE_MATCHING.md)的兼容候选评分底座。最终一级标签由固定 K4 投票选择。已有报告是否带GT标签
不影响特征导出；无需重新生成报告。上游诊断skill负责获取真实证据，匹配脚本负责确定性
提取/计算/决策；离线LOO调用相同模块，不模拟让Agent重新执行诊断skill。

## 输入和共用入口

```bash
python3 scripts/match_baseline.py --report /path/report.json \
  --log-dir /path/raw_logs --out /tmp/baseline.json
# 单故障候选导出加 --fault-index 0。
python3 scripts/match_baseline.py --query /tmp/baseline.json \
  --cases /path/cases.json --out /tmp/matches.json
# 同一计算入口也可由原脚本路由：
python3 scripts/match_cases.py /tmp/baseline.json \
  --local-cases /path/cases.json --json /tmp/matches.json
```

`legacy-evidence-v1`为封闭schema：`schema_version/status_codes/failure_mode_ids/
latency_components/operation/log_semantic_profile`。不接受GT、根因、标题、why/detail、
结论、知识匹配、报告置信度或身份字段。日志轮廓从真实E/W消息提取，或使用有哈希与来源的
显式冻结缓存；不从报告内的同名字段兜底。日志缺失时轮廓为空，不把缺失解释为健康。

`cases.json`格式为`{"cases":[{"id":"...","source_id":"...","label":"...","profile":{...}}]}`。
标签只在候选信封，查询GT只交给评估端。多故障的候选标签映射使用独立清单，不能读取
查询结论来对齐；标签数和故障数不等时不能擅自按顺序分配。CLI仅本地读写结果，不建案或回写命中。

LOO调用方先过滤源报告及同一日志的所有版本，再调用`baseline_matching.rank`。
CLI支持多次`--exclude-source-id`，但调用方仍须发现同日志别名；不要声称这个参数自动发现了全部重复。
`Coordinator故障`、`UB管控面故障`候选不参与本地基线。线上案例确认和应用性核对仍按主SKILL执行。

## 候选评分和历史K4对照

模块直接调用已有`match_cases.py`中的`_soft_score/_domain_prior/_rerank/_label_vote`：

- 错误码集合F1、模式命中累计、阶段命中累计、旧操作软匹配及原查询分母。
- 从每轮过滤后的候选统计码/模式到一级标签的先验；默认权重0.2。
- 日志语义按本轮候选IDF重加权，余弦分数以原权重0.5加到旧软分；保留原舍入规则。
- 查询文本为空、log_keywords为空；候选文本、诊断置信度、命中数、更新时间不影响排序。
- 分数并列保留输入候选顺序；不临时按文件名/哈希重排。
- 历史K4对照、margin=0.05：前两名分差大于margin时取top1，否则前4个故障案例投票。
  这里保留历史故障案例投票单位，不悄悄改成按源报告去重。空候选返回空预测。

候选评分在上述底座上固定叠加BM25、角色、范围三个观测通道，各0.05，保留底座和原分母。
不需要`--combine`或其他算法选择参数。`rank(query,cases,query_structured=...)`只计算候选排序；普通完整匹配使用 `baseline_matching.match(query,cases,query_structured,query_raw)`。
查询旁车按`<query stem>.structured.json`自动加载；候选的观测来自信封`structured`字段。
缺失观测不记为不匹配，相应增量为0；只有真正提供的结构化候选参与新增通道的统计。

为可复现旧能力，基线暂保留旧操作头部正则和标识符拼接值的匹配语义。
例如`SET（GET 无样本）`在兼容模式中仍可能得到MIXED，不能据此宣称GET已观测到故障。
上游取证继续按GET/SET独立口径；更严操作视图作为单独实验，避免把修复抽取和替换评分混在一起。
多故障候选共享报告级统计/日志背景，不能把共享上下文冒充逐故障归属证据。

## 使用边界

普通 Agent 使用完整固定方案，不选择底座或消融开关。底层 `rank`、`decide`供候选评分和复核，
完整标签决策通过 `fixed_matching.match`调用。K4 LOO 调用同一全部特征规则流程；分类器仅通过显式入口使用，训练/验证划分由离线工具持久化。
