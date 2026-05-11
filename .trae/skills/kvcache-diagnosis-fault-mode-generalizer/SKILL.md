---
name: kvcache-diagnosis-fault-mode-generalizer
description: 灵衢超节点kvcache通断和时延场景的故障模式生成器
---
# 目标
根据../docs/observable/08-fault-triage-consolidated.md和../docs/observable/10-customer-fault-scenarios.md故障定界说明，按照../references/fault_example.md的模板格式，生成kvcache的通断场景和时延场景的故障定界md文件，两个场景需要生成两个文档放在../docs目录下。

# 步骤
## 1.阅读故障定界说明
阅读../docs/observable/08-fault-triage-consolidated.md和../docs/observable/10-customer-fault-scenarios.md文件，了解kvcache的通断场景和时延场景的故障定界说明
## 2.阅读其他辅助资料
阅读/home/liyuanr/push/yuanrong-datasystem-agent-workbench/docs/observable目录下其他文档，了解kvcache的通断场景和时延场景的故障定界说明中可能涉及的其他故障场景和原因，例如其他组件的故障场景和原因，其他故障场景和原因的组合关系等，还比如可能涉及的命令行。
## 3.根据故障定界说明生成故障模式定界文档
输出通断场景的故障定界文档到../docs/kvcache_conn_fault_mode.md，输出时延场景的故障定界文档到../docs/kvcache_dly_fault_mode.md，需要遵循以下规则：
* 根据../references/fault_example.md的模板格式，生成通断场景的故障定界文档和时延场景的故障定界文档。
* 内容需要来自于源文档，使用源文档中的描述和命令行，不能进行内容篡改。
* 如果有无法识别的内容，比如特殊符号→等，在文档中加粗标准。
* 每行内容都需要标注来源于哪个源文档，在源文档的位置和具体行号。
* 给所有故障进行编码，编码规则为：kvcache_通断场景_故障编码或kvcache_时延场景_故障编码，例如kvcache_conn_fault_001，kvcache_dly_fault_001等，按照故障的顺序编码，不需要区分上下级故障。
* 给所有故障增加下级故障（如果有），需要给出下级故障模式的编码，例如kvcache_conn_fault_001_001，kvcache_dly_fault_001_001等，只需要给下一级故障模式的编码，不需要给所有下级故障模式的编码。
* 生成的模板化的定界文档是用于生成故障定界解析的代码和故障编码关联的json文件，故障解析代码模板在../references/hw005_break.cpp和../references/hw005_delay.h，json文件的模板在../references/failure_mode_tree.json。
* 首先理解文档中会读取的日志的格式（比如../docs/observable/08-fault-triage-consolidated.md第14行附近ds_client_access.log日志的格式），在文档的开头给出日志格式的说明，然后分析采集日志的命令（如果该故障场景有命令行），增加执行命令行会输出什么内容，然后根据命令行输出的内容，给出匹配逻辑的内容，让匹配逻辑和命令行输出结果是可以关联的。