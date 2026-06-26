---
name: "diagnosis-failure-mode-generation-urma"
description: "分析 URMA 组件源码，以代码中 ERROR 日志输出宏为单位，生成对应的故障模式树"
---
# diagnosis-failure-mode-generation-urma

## 目标

根据 URMA 组件的源码生成对应的故障模式树。故障模式树以 URMA 组件的函数调用关系为参考，以源码中各个函数内部的 ERROR 日志输出为单位，覆盖整个源码仓的故障发生点。你需要 URMA 组件的源码仓路径作为输入，输出指定格式的故障模式树。

## 输入

- URMA 组件的源码仓路径

## 输出

- 生成的故障模式树以markdown格式输出，基础模板说明参考.opencode/skills/diagnosis-failure-mode-generation-urma/references/failure_mode_tree_example.md文件，输出路径为./data/urma/urma_failure_mode_tree.md
- 故障模式树的每个节点对应一个函数中的一个 ERROR 日志输出点（URMA_LOG_ERR日志宏），节点内容包括以下标题和字段：
    - **故障名称**：该字段是节点标题
    - **故障现象**：参见failure_mode_tree_example.md中的说明和示例，对 URMA 组件需要给出查看该日志的日志文件路径和识别该日志的关键字，不得新增别的字段；日志路径暂时定为环境变量URMA_LOG_PATH
    - **故障原因**：参见failure_mode_tree_example.md中的说明和示例，需要体现该函数的作用和该故障模式发生的具体的直接原因，不能仅体现代码字面量或很宽泛的描述；对于.opencode/skills/diagnosis-failure-mode-generation-urma/references/function_additional_info.md中有说明的函数，需结合说明内容进行填写
    - **解决办法**：参见failure_mode_tree_example.md中的说明和示例，对 URMA 组件默认填写“无”；对于.opencode/skills/diagnosis-failure-mode-generation-urma/references/function_additional_info.md中有说明的函数，需结合说明内容进行填写
    - **故障编号**：按顺序对所有故障节点进行编号，格式为`urma_xxx`，其中`xxx`是从001开始的三位数
    - **函数名**：调用 URMA_LOG_ERR 日志宏的函数，填写`find_urma_log_err.py`脚本输出中的函数名
- 无需增加别的字段或补充信息，不用输出故障发生的源码位置

### `故障名称`要求

1. 故障名称必须体现触发该日志的直接原因，对日志文本和上下文对原因进行翻译和总结，不得只写“依赖的参数、资源状态或下层调用结果不满足继续执行条件；操作执行过程中发生错误”这种宽泛的描述，也不能直接抽取代码或日志的字面内容。
2. 需要避免故障名称过于宽泛，如“删除资源失败”，需要说明是为什么失败；“操作执行过程中发生错误”，需要说明是具体是什么错误，可以从日志内容、下层函数调用或if条件中获取关键信息
3. 若日志点位于 if 分支中，需要把 if 条件翻译成业务原因，但不要直接输出if语句的字面内容
    - `ctx == NULL`：调用方未传入有效 URMA context
    - `ops == NULL || ops->xxx == NULL`：provider 未提供对应操作实现
    - `ret != 0`：下层资源创建/驱动命令返回失败
    - `errno`：系统调用失败，需说明对应文件、fd、目录或 ioctl 对象
4. 部分故障可以参考`高频日志专项规则`

### `故障现象`要求

1. 故障现象需要明确应该从哪个文件进行怎样的关键字匹配，要有`日志路径`和`关键日志`两个字段
2. 需要匹配到所有的关键字，关键字来源如下：
    - 函数名
    - 错误日志字面量，如：匹配 `Provider Bond register ops failed`
    - 如果有格式占位符，如`%d`、`%s`，需要以这样的占位符为分割，将前后的所有字面量作为关键字，如：依次匹配 `Failed to create bondp comp, dev_name:`、`, eid_idx:`
3. 关键日志最终输出格式为：依次匹配`关键字1`、`关键字2`

### `故障原因`要求

1. 根据 if 条件或下层函数调用的语义总结产生该故障的根本原因，最好是结合本函数的作用
2. 不允许直接借用故障名称的内容，但可以在此基础上扩展

### 高频日志专项规则

- `Invalid parameter`：
    - 必须结合 if 条件指出具体无效对象，如 ctx、dev、ops、jfs、jfr、jetty、seg、wr、sgl、tjetty，不得只写“参数无效”。
- `Failed to alloc args`：
    - 必须说明分配的是哪个命令参数、资源参数或临时结构，以及失败会阻断哪个 URMA 操作。
- `ioctl failed`：
    - 必须说明 ioctl 对应的 URMA_CMD 命令语义，如创建 context、注册 segment、导入 jetty、查询 tp list 等。
- `Failed open/read/parse sysfs`：
    - 必须说明读取的是设备、EID、端口、能力或 cdev 路径信息。

### 故障聚合要求

对于同一个函数中的多个 URMA_LOG_ERR 日志点，如果它们的日志内容完全相同（全字匹配），需要将它们聚合成一个故障节点，部分重复的日志内容如下：
- `Invalid parameter`

## 故障模式树结构

故障模式树的节点由顶层故障模式节点和叶子故障模式节点两种节点组成，树的层数只有2层，将所有叶节点进行分类并挂载到对应的顶层故障模式节点下即可

### 顶层故障模式节点

顶层故障模式作为故障模式的类别呈现，此类故障节点对应failure_mode_tree_example.md中需要向下级匹配的节点，如：
- `初始化失败`
- `建链失败`
- `资源创建失败`
- `资源查询失败`
- `资源导入/注册失败`
- `数据收发失败`
- `资源销毁/清理失败`
- `设备/驱动交互失败`
- `其他URMA故障`

### 叶子故障模式节点

叶子故障模式节点是直接对应到`URMA_LOG_ERR`的节点，各个字段需要从代码中获取合理的信息

## 操作步骤

### 步骤一：提取 URMA_LOG_ERR 日志点

1. 调用本 skill 的脚本，获取所有 URMA_LOG_ERR 日志点的信息，包括文件名、函数名、函数起始行、日志所在行数、日志内容

```bash
python .opencode/skills/diagnosis-failure-mode-generation-urma/scripts/find_urma_log_err.py <path-to-urma-source-code>
```

该脚本输出格式如下：

```json
{
    "log_macro": "URMA_LOG_ERR",
    "search_symbols": [
        "URMA_LOG_ERR",
        "URMA_CHECK_CTX_INVALID_RETURN_STATUS",
        "URMA_CHECK_OP_INVALID_RETURN_POINTER",
        "URMA_CHECK_OP_INVALID_RETURN_STATUS",
        "URMA_CHECK_OP_INVALID_RETURN_NEG_STATUS"
    ],
    "total": 866,
    "entries": [
        {
            "file": "bond/bondp_api.c",
            "function": "bondp_create_pjfce",
            "function_start_line": 85,
            "log_line": 96,
            "log_content": "\"Failed to create pjfce %d.\\n\", i"
        }
    ]
}
```

2. 修正脚本中的可能存在的错误信息
    - 根据输出中给定的文件路径和函数名，检查输出中的函数起始行是否正确
    - 根据输出中给定的文件路径和日志内容，检查输出中的日志所在行数是否正确

## 步骤二：构建故障模式树

1. 根据脚本输出，定位所有日志宏输出错误日志的函数和代码位置
2. 结合顶层故障模式节点语义，对所有故障点进行归纳总结，构建符合要求的故障模式树结构

### 步骤三：填充故障模式节点

1. 根据每个故障点的代码上下文和业务逻辑，撰写符合要求的故障名称、故障现象、故障原因和解决办法
2. 根据./references/function_additional_info.md的内容对部分函数的故障原因和解决办法进行修正
3. 将生成的故障模式树以markdown格式输出到./data/urma_failure_mode_tree.md文件中
4. 按顺序对所有故障模式节点（包括顶层故障模式节点和叶子故障模式节点）进行编号

## 质量自检

1. 生成的故障模式树需要覆盖 URMA 组件源码中所有带有 ERROR 日志输出的函数，若某个函数不存在于函数调用关系中，仍需将其作为一个独立的节点添加到故障模式树中
2. 生成的故障模式树需要满足输出说明中规定的格式要求，且每个节点的内容需要合理且符合 URMA 组件的业务逻辑
3. 生成的故障名称、故障原因需要能够体现故障的本质和业务含义，便于用户理解，不应简单重复或抽取代码或日志的字面量，也不应简单描述为“xxx函数故障”
4. 是否将function_additional_info.md里部分函数的补充信息体现在故障模式树中
5. 故障编号必须按照最终markdown文件中的顺序进行编号，不能重复
