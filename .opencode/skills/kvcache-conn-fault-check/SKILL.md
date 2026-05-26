---
name: kvcache-conn-fault-checker
description: 灵衢超节点kvcache通断场景的故障定界代码生成器
---

#目标：分别生成单种和多种故障对应的日志文件，编译并执行witty-ub-diag-tool工具，验证是否能够成功识别故障内容

#步骤
## 步骤1：
生成单个叶子故障日志，读取diagnosis_tool/failure_mode_realization/kvcache路径下的所有故障，为每个叶子故障生成从根节点识别叶子故障所需要的所有的日志文件（如果有多个就生成多个），日志文件放在data/kvcache-conn-fault-log/leaf-log/目录下，每个叶子故障的日志放在以该叶子故障的故障编码命名的文件下

## 步骤2：
读取data/kvcache_conn_fault_mode.md文件，检查文件中对应的故障表现和生成的叶子故障的日志是否匹配，如不匹配输出该故障编码，到data/kvcache-conn-fault-log/gen-leaf-error.md中，然后总结生成的叶子故障故障日志到data/kvcache-conn-fault-log/gen-leaf-fault.md文件的表格中，表格第一列为故障编码，第二列为故障名，第三列为是否正确生成，第四列为涉及的日志文件

## 步骤3：
编译witty-ub-diag-tool工具，只编译这个二进制即可，不需要对其他二进制进行编译，也不需要管其他二进制编译报错，配置日志路径为对应叶子故障日志的路径，检查每个故障是否能够正确识别，输出检查结果到kvcache-conn-fault-log/leaf-single-result.md文件中

## 步骤4：
生成多故障日志文件，生成日志文件包含任意非相同父节点的3个叶子故障，日志文件放在data/kvcache-conn-fault-log/multi-log目录下，日志文件所在目录通过故障编号和+拼接，例如kvcache-conn-fault-002_001+028_008+005，同时生成一个预期结果的文件，即该日志应该识别什么结果和日志放在相同目录下，生成至少5个多故障日志文件用例，在故障日志生成时注意，预期是一个故障链上的故障日志的trace id是相同的

## 步骤5：
配置日志路径为生成的故障日志的路径，检查每种故障是否能够正确识别，输出检查结果到kvcache-conn-fault-log/multi-result.md文件中