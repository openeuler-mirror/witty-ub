---
name: kvcache-diagnosis-fault-mode-generalizer
description: 灵衢超节点kvcache通断和时延场景的故障模式生成器
---
# 目标
根据../docs/observable/08-fault-triage-consolidated.md按照../references/fault_example.md的模板格式，生成kvcache的通断（中断）场景故障定界md文件，两个场景需要生成两个文档放在../docs目录下。

# 步骤
## 1.阅读故障定界说明
阅读../docs/observable/08-fault-triage-consolidated.md，了解kvcache的通断场景和时延场景的故障定界说明
## 2.阅读其他辅助资料
阅读/home/liyuanr/push/yuanrong-datasystem-agent-workbench/docs/observable目录下其他文档，了解kvcache的通断场景和时延场景的故障定界说明中可能涉及的其他故障场景和原因，例如其他组件的故障场景和原因，其他故障场景和原因的组合关系等，还比如可能涉及的命令行。
## 3.根据故障定界说明生成故障模式定界文档
输出通断场景的故障定界文档到kvcache_conn_fault_mode.md，需要遵循以下规则：
* 1.按照references/fault_example.md的模板格式，根据docs/observable/08-fault-triage-consolidated.md生成通断场景的故障定界文档，docs/observable/10-customer-fault-scenarios.md文档中的内容能匹配到docs/observable/08-fault-triage-consolidated.md中提取到的故障，对这两个文档中对于故障的描述进行对比，10-customer-fault-scenarios.md如果包含08-fault-triage-consolidated.md中已经提取到的故障的其他描述，可以作为故障的补充，但是生成的故障条目需要来自于08-fault-triage-consolidated.md，不能来自于/docs/observable/10-customer-fault-scenarios.md
* 2.故障需要使用源文档中的描述和命令行，除了命令行根据日志模板进行适配，其他不能进行任何内容篡改，。
* 3.注意识别的非文字内容，比如特殊符号→为下一步，↑为增加，↓为减少。
* 4.每行内容都需要标注来源于哪个源文档，在源文档的位置和具体行号。
* 5.给所有故障进行编码，编码规则为：kvcache_通断场景_故障编码或kvcache_时延场景_故障编码，例如kvcache_conn_fault_001，kvcache_dly_fault_001等，按照故障的顺序编码，不需要区分上下级故障。
* 6.给所有故障增加下级故障（如果有），需要给出下级故障模式的编码，例如kvcache_conn_fault_001_001，kvcache_dly_fault_001_001等，只需要给下一级故障模式的编码，不需要给所有下级故障模式的编码。
* 7.生成的模板化的定界文档是用于生成故障定界解析的代码和故障编码关联的json文件，在文档生成之前阅读故障解析代码模板，在../references/hw005_break.cpp和../references/hw005_delay.h，json文件的模板在../references/failure_mode_tree.json，让生成的文档容易转化成代码。
* 8.阅读references/log_template.md文件，和references/log_example目录下日志示例文件，了解日志的格式和日志模板的示例，根据日志模板的格式和示例，在文档中给出日志模板说明和对应的日志示例
* 9.分析故障现象中的命令（如果该故障场景有命令行），增加执行命令行会输出什么内容，然后根据命令行输出的内容，给出匹配逻辑的内容，让匹配逻辑和命令行输出结果是可以关联的
* 10.区分故障现象中命令，分成1）用于查询日志，匹配其中内容的命令，2）需要在出现故障的机器上执行，比如查看机器上dmesg之类或者ls /dev/ub*这种来确定状态的命令，对于2）类型的命令不放在故障现象中，而是放在解决办法中让用户自己到机器上执行，并在文档最后加上一列附录，列出所有涉及这种情况的故障名称及其编号
* 11.故障现象中的命令需要是根据实际对应的日志文件的格式进行匹配的
* 12.故障现象的表述需要根据文档内容从头到尾逐渐具体，文档前面可能出现对一类故障概况性的故障现象的描述，如果在后文出现更具体的描述和拆分，需要更新故障现象为更具体的内容或者更多故障模式，如前面出现“xxxx/yyyy/zzzz是属于用户侧错误，是cccc/dddd问题导致”，属于概括性说明，不具体到某个错误码，在后文会出现具体的错误码，需要更新故障现象为更具体的内容，如001xxxx故障，错误码x，故障表现xxxx，故障原因xxx，002yyyy故障，错误码y，故障表现yyy。
* 13.涉及到查询的日志写日志文件的全称，比如INFO log 文件是指ds_client_*.INFO.log，access log 文件是指ds_client_access_*.log等
* 14.故障中可能出现相同故障但是是不同的故障表现，在这类故障中增加字段说明会和哪个故障是相同的故障
* 15.文档生成后对文档进行检查，确认所有来源于源文档的内容是准确的，在源文档中行数是正确的，内容没有编造，没有篡改，没有遗漏，没有重复，没有错误的编码，没有错误的匹配逻辑，没有错误的命令行输出，没有错误的日志模板说明，没有错误的日志示例。
