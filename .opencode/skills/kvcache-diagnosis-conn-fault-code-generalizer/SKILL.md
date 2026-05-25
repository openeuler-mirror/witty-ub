---
name: kvcache-diagnosis-conn-fault-code-generalizer
description: 灵衢超节点kvcache通断场景的故障定界代码生成器
---
# 目标
根据references/kvcache_conn_fault_mode.md中故障定界说明，按照src/diagnosis_tool/failure_mode_realization中故障模式的代码模板，为每个故障模式生成故障定界代码。

# 步骤
## 1.阅读故障定界文档
读取references/kvcache_conn_fault_mode.md故障模式定界文档，理解每个故障模式的内容和故障模式之间的关联关系。
## 2.阅读故障模式定界的module代码
阅读src/diagnosis_tool目录下的故障模式定界的代码，从diagnosis_tool_module.h文件作为入口，理解module中故障模式是如何注册、管理和使用的，怎么对故障进行遍历，怎么判断是否为根因，需要在进行判断时执行什么操作，收集什么信息，然后理解src/diagnosis_tool/failure_mode_realization目录下的具体故障模式的示例代码。
## 3.根据故障定界文档生成故障模式定界代码
1、根据references/kvcache_conn_fault_mode.md故障模式定界文档，src/diagnosis_tool下故障诊断module的框架，为每个故障模式生成代码到src/diagnosis_tool/failure_mode_realization/kvcache目录下，故障模式的代码需要遵循的规则如下：
a. 生成的故障代码中文字的内容需要来自于源文档，使用源文档中的描述和命令行，不能进行内容篡改，并用注释标注来源于文档的哪行。
b. 故障代码中如果是从文档中提取或者转化的的内容都需要标注来源于源文档的位置和具体行号。
c. 故障代码中逻辑判断代码的部分需要有注释说明
d. 故障代码的文件命名规则为：kvcache_conn_fault_故障编码.cpp，例如kvcache_conn_fault_001.cpp，kvcache_conn_fault_001_001.cpp等。
e. 日志文件的路径环境变量设为$WITTY-UB-FAULT-LOG
f. 需要在故障判断执行中获取到匹配的日志行，检查执行日志内容匹配命令行，如果命令行中存在对日志行的聚合或者处理，则增加获取实际的日志行的内容传递给解析函数
g. 如果日志匹配的命令行中存在tail命令来限定匹配的日志行数，删除命令行中的tail命令
h. 日志匹配命令行中如果grep匹配了多个文件，输出结果会是文件路径：日志行，对于此类命令增加对输出的结果的处理，只保留日志行
h. 如果kvcache的故障模式代码已存在，判断代码是否需要更新
## 4.故障模式中命令检查
代码生成后检查每个故障模式中的调用的命令是否能执行成功，如果有命令没有安装，输出这个条未执行的命令清单和他属于哪个故障模式在代码的哪个文件中的哪行到ignore-cmd.md文件中,如果有命令执行失败，输出这条当前错误的命令和他属于哪个故障模式在代码的哪个文件中的哪行到error-cmd.md文件中，md文件保存在data/date(替换为当前时间)-skills-cmd-check目录下。
## 5.自测
对witty-ub-diag-tool进行编译，保证代码能够编译通过，只编译这一个二进制通过，无需编译项目其他二进制

2、根据references/kvcache_conn_fault_mode.md故障模式定界文档中故障编号之间的关联关系，按照data/failure_mode_tree.json中的模板，生成一份json文件，文件名为kvcache_conn_fault_mode_tree.json，放在data/kvcache目录下，需要遵循规则如下：
* 故障树中每个节点的id需要和references/kvcache_conn_fault_mode.md故障模式定界文档中的故障故障编码的全称保持一致，不要只截取读取数字部分。
* 故障树中每个节点的children需要和references/kvcache_conn_fault_mode.md故障模式定界文档中该故障模式的下级故障模式的故障编码的全称保持一致，不要只截取数字部分。
* 生成json文件中，一个故障的下级故障编码不换行
3、根据references/kvcache_conn_fault_mode.md故障模式定界文档生成一份csv格式的文件，文件名为kvcache_conn_fault_mode.csv，放在data/kvcache目录下，需要遵循规则如下：
* csv文件中包含每个故障中的所有字段，每个字段作为一列，最左侧为故障编码列。
* 如果已有该文件，判断是否需要更新
