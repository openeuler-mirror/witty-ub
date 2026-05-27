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
阅读src/diagnosis_tool目录下的故障模式定界的代码，从diagnosis_tool_module.h文件作为入口，先理解module内故障模式是如何注册、管理和使用的，然后理解src/diagnosis_tool/failure_mode_realization目录下的具体故障模式的示例代码，输出代码逻辑到.trae/skills/kvcache-diagnosis-conn-fault-code-generalizer目录。
## 3.根据故障定界文档生成故障模式定界代码
需要完成：
1、根据references/kvcache_conn_fault_mode.md故障模式定界文档，为每个故障模式生成代码到src/diagnosis_tool/failure_mode_realization目录下，需要遵循规则如下：
* 生成的故障代码内容需要来自于源文档，使用源文档中的描述和命令行，不能进行内容篡改。
* 如果有无法识别的内容或者无法转换成代码的内容，在代码中增加注释，以"// Warning:"开头。
* 故障代码中如果是从文档中提取或者转化的的内容都需要标注来源于源文档的位置和具体行号。
* 故障代码的文件命名规则为：kvcache_conn_fault_故障编码.cpp，例如kvcache_conn_fault_001.cpp，kvcache_conn_fault_001_001.cpp等。
* 代码生成后检查每个故障模式中的调用的命令是否能执行成功，如果有命令没有安装，输出这个条未执行的命令清单和他属于哪个故障模式在代码的哪个文件中的哪行到ignore-cmd.md文件中，md文件保存在data目录下，如果有命令执行失败，输出这条当前错误的命令和他属于哪个故障模式在代码的哪个文件中的哪行到error-cmd.md文件中，md文件保存在data目录下。
2、根据references/kvcache_conn_fault_mode.md故障模式定界文档中故障编号之间的关联关系，按照data/failure_mode_tree.json中的模板，生成一份json文件，文件名为kvcache_conn_fault_mode_tree.json，放在data目录下，需要遵循规则如下：
* 故障树中每个节点的id需要和references/kvcache_conn_fault_mode.md故障模式定界文档中的故障故障编码的全称保持一致，不要只截取读取数字部分。
* 故障树中每个节点的children需要和references/kvcache_conn_fault_mode.md故障模式定界文档中该故障模式的下级故障模式的故障编码的全称保持一致，不要只截取数字部分。
* 生成json文件中，一个故障的下级故障编码不换行
3、根据references/kvcache_conn_fault_mode.md故障模式定界文档生成一份csv格式的文件，文件名为kvcache_conn_fault_mode.csv，放在data目录下，需要遵循规则如下：
* csv文件中包含每个故障中的所有字段，每个字段作为一列，最左侧为故障编码列。
