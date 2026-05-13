---
name: "urma-failure-mode-realization"
description: "根据 urma_failure_modes.md 故障模式树生成对应的 C++ FailureMode 实现代码。"
---

# urma-failure-mode-realization

## 目标

读取 `urma-failure-mode-generator` skill 生成的 URMA 故障模式树文件，将其中每个故障模式节点转换为 `src/diagnosis_tool/failure_mode_realization/urma/` 下的 C++ `FailureMode` 派生类实现，并确保类定义、注册编号、根因分析和故障校验逻辑与故障树内容一致。

适用场景：

- 已有 `/var/witty-ub/failure-modes/urma_failure_modes.md` 或用户指定的等价故障树文件
- 需要为故障树中的每个故障模式生成 `.h` 和 `.cpp`
- 需要把叶子节点与非叶子节点的根因判断逻辑映射到 `AnalyzeRootCause`
- 需要根据故障现象生成可执行或可扩展的 `IsValid` 日志匹配代码

## 输入

- `failure_tree_path`：必选，故障模式树 Markdown 文件路径，通常为 `/var/witty-ub/failure-modes/urma_failure_modes.md`
- `diagnosis_tool_path`：可选，诊断工具源码目录，默认使用 `src/diagnosis_tool`

输入要求：

1. `failure_tree_path` 必须是可访问的 Markdown 文件。
2. 故障树节点必须包含：
   - `故障编号`
   - `下级故障`
   - `故障现象`
   - `故障原因`
   - `解决办法` 或 `解决方法`
3. `FailureMode` 基类定义以 `src/diagnosis_tool/failure_mode.h` 为准。
4. 生成代码风格参考 `src/diagnosis_tool/failure_mode_realization/` 下已有样例。

## 输出

输出目录：

- `src/diagnosis_tool/failure_mode_realization/urma/`

每个故障模式节点生成两个文件：

- `<class_file_name>.h`
- `<class_file_name>.cpp`

其中：

1. `<class_file_name>` 由故障编号和故障名称转换得到，必须使用小写字母、数字和下划线。
2. 类名使用 PascalCase，必须唯一且可读。
3. 如果故障名称包含中文或无法直接提取有意义的 ASCII token，必须先将故障名称翻译成简短、准确的英文语义短语，再生成文件名和类名；禁止退化为 `failure`、`unknown`、`node` 等泛化名称。
4. `.h` 文件声明 `FailureMode` 派生类。
5. `.cpp` 文件实现所有虚函数，并使用 `AutoRegister` 注册带组件命名空间的完整故障编号。
6. 如果输出目录不存在，必须先创建 `src/diagnosis_tool/failure_mode_realization/urma/`。
7. 不要覆盖用户已有的手工实现，除非用户明确要求更新；如果目标文件已存在，应先读取并判断是否可安全修改。

## FailureMode 基类契约

以 `src/diagnosis_tool/failure_mode.h` 中定义为准，生成类必须实现以下接口：

```cpp
std::string GetName() const override;
std::string GetValidationMethodDesc() const override;
bool IsValid(std::string& logContent) override;
std::string GetRootCauseDesc() const override;
RootCause AnalyzeRootCause() override;
std::string GetFixSuggDesc() const override;
std::string GetId() const override;
```

类声明格式参考：

```cpp
#pragma once

#include "../../failure_mode.h"

namespace diag {
class Urma001BuildLinkFailure : public FailureMode {
public:
    Urma001BuildLinkFailure() noexcept = default;
    bool IsValid(std::string& logContent) override;
    std::string GetName() const override;
    std::string GetRootCauseDesc() const override;
    RootCause AnalyzeRootCause() override;
    std::string GetFixSuggDesc() const override;
    std::string GetValidationMethodDesc() const override;
    std::string GetId() const override;
};
} // namespace diag
```

## 故障树解析规则

解析 `urma_failure_modes.md` 时：

1. 以 Markdown 标题层级识别故障树层级。
2. 每个标题下直到下一个同级或更高级标题前的字段属于当前故障模式。
3. `故障编号` 是生成注册编号和 `GetId` 的来源，例如 `urma_001` 对应注册编号 `urma_001`；需要数字部分时可从中派生 `001`。
4. `下级故障` 是判断叶子节点的主要依据：
   - `[]` 表示叶子节点。
   - 非空数组表示非叶子节点。
5. 如果 `下级故障` 缺失或格式异常，应根据标题层级推断直属子节点，并在最终说明中标出该推断。
6. 标题中的序号只用于排序，不应作为故障编号来源。
7. 故障名称取标题去掉前置数字后的文本，例如 `##### 1.1.1 get tp list 错误码 -2` 的名称为 `get tp list 错误码 -2`。

## 单个故障模式类生成规则

每个故障模式节点生成一个从 `FailureMode` 派生的类：

1. 类名优先由 `故障编号 + 故障名称` 生成，避免重复。故障名称为中文时，应将中文语义翻译为英文后生成 PascalCase 类名，例如 `建链失败` 生成 `Urma001LinkSetupFailure`，文件名生成 `urma_001_link_setup_failure.*`。
2. 注册变量名统一为 `g_urma`，注册编号使用完整故障编号，避免与其他组件的裸数字注册号冲突：

```cpp
static AutoRegister<Urma001BuildLinkFailure> g_urma("urma_001");
```

3. `GetId` 返回完整故障编号，例如故障编号 `urma_001` 返回 `urma_001`。
4. `GetName` 返回故障名称，不返回裸编号。
5. `GetRootCauseDesc` 返回 `故障原因` 字段内容。
6. `GetFixSuggDesc` 返回 `解决办法` 字段内容；如果只有 `解决方法`，使用 `解决方法` 字段。
7. `GetValidationMethodDesc` 根据 `故障现象` 生成描述性文字。
8. `AnalyzeRootCause` 根据是否叶子节点生成：
   - 叶子节点：`return RootCause(true, GetRootCauseDesc());`
   - 非叶子节点：`return RootCause(false, GetRootCauseDesc());`

## IsValid 生成规则

`IsValid` 用于根据故障现象判断当前故障是否匹配，函数签名必须为：

```cpp
bool IsValid(std::string& logContent) override;
```

返回规则：

1. 匹配到故障时返回 `true`，并把用于确认故障存在的匹配日志或可观测内容写入 `logContent`。
2. 未匹配到故障时返回 `false`，并确保 `logContent` 为空字符串。
3. 函数入口处应先执行 `logContent.clear();`，避免调用方读到上一次匹配结果。

### 通过日志匹配

当 `故障现象` 中包含 `关键日志` 和 `日志路径` 时：

1. 提取 `关键日志` 中稳定、可匹配的短文本。
2. 提取 `日志路径`：
   - `URMA_LOG_PATH`：统一复用 `src/diagnosis_tool/failure_mode_realization/urma/urma_log_matcher.h` 中的 `diag::MatchUrmaLogLine`；如果该 helper 不存在，先生成 `urma_log_matcher.h/.cpp` 并加入构建系统。不要在每个故障模式 `.cpp` 中重复定义日志扫描函数。匹配成功时将匹配到的日志行或日志片段赋值给 `logContent`。
   - `dmesg`：若工程中已有执行命令或读取系统日志 helper，优先复用；否则生成明确的 TODO 注释和保守返回逻辑，不要编造不可用接口。匹配成功时将命中的 dmesg 日志行或片段赋值给 `logContent`。
   - `无明确日志路径`：不要硬编码不存在的日志文件，使用返回值/调试信息描述作为 `GetValidationMethodDesc`，`IsValid` 可保守返回 `false` 或复用调用方提供的日志输入机制；返回 `false` 时必须保持 `logContent` 为空。
3. 如果有多个关键字，按故障树说明生成 `all_of` 或 `any_of` 组合判断。
4. 多关键字组合匹配成功时，`logContent` 应包含足以说明故障存在的命中日志内容；可使用第一条命中日志、组合后的关键日志摘要，或多行命中内容。
5. 不要整段复制很长的日志示例到代码中，只保留足以识别故障的关键片段。

### 通过错误码或返回值匹配

当故障现象为“匹配函数 xxx 返回错误码 YYY”“返回 NULL/false”等无日志现象时：

1. `GetValidationMethodDesc` 必须说明需要结合调用方返回值、调试信息或上游日志确认。
2. 若工程没有运行态上下文可读取函数返回值，`IsValid` 不应虚构状态来源。
3. 可生成保守实现：

```cpp
bool Xxx::IsValid(std::string& logContent)
{
    logContent.clear();
    return false;
}
```

并在代码注释中简短说明该故障需要外部调用上下文才能自动判断。只要返回 `false`，`logContent` 必须为空字符串。

### 非叶子节点

非叶子节点通常只用于分类：

1. 如果现有框架会逐个调用所有 `FailureMode::IsValid`，非叶子节点的 `IsValid` 应根据直属子节点匹配结果聚合；如果任一子节点匹配成功，应返回 `true`，并把子节点返回的匹配日志写入 `logContent`。
2. 不要让非叶子节点无条件返回 `true`，避免分类节点被误判为根因。
3. `GetValidationMethodDesc` 返回“向下级故障匹配”或故障树中对应描述。
4. 只有在框架没有子节点实例访问能力时，才保守返回 `false`，并保持 `logContent` 为空。

## 字符串与代码安全规则

1. C++ 字符串必须正确转义双引号、反斜杠、换行和不可见字符。
2. 中文文本可以保留为 UTF-8。
3. 类名和文件名必须只使用 ASCII 字符；静态注册变量名固定为 `g_urma`。如果故障名称含中文，先翻译成英文语义短语再转换为 ASCII 类名/文件名，不能使用无语义兜底名。
4. 文件名避免过长；建议格式为 `urma_001_<short_slug>.h` 和 `urma_001_<short_slug>.cpp`。
5. 生成代码不要引入全局 using namespace。
6. 单个故障模式 `.cpp` 只包含自身头文件、`../../failure_mode_factory.h` 和必要依赖；需要匹配 `URMA_LOG_PATH` 时包含 `urma_log_matcher.h` 和 `<vector>`，不要重复包含 `<cstdlib>`、`<fstream>` 或重复实现文件扫描逻辑。
7. `URMA_LOG_PATH` 日志扫描 helper 统一放在 `failure_mode_realization/urma/urma_log_matcher.h/.cpp`，函数声明为 `diag::MatchUrmaLogLine(const std::vector<std::string>&, std::string&)`，避免污染其他组件命名空间。

## 执行流程

1. 校验 `failure_tree_path` 是否存在。
2. 读取 `src/diagnosis_tool/failure_mode.h`，确认 `FailureMode` 接口签名。
3. 读取 `src/diagnosis_tool/failure_mode_realization/` 下已有 `.h`、`.cpp`，确认本仓库代码风格、注册方式和命名习惯。
4. 确认输出目录 `src/diagnosis_tool/failure_mode_realization/urma/` 存在；不存在时先创建。
5. 解析故障树 Markdown，生成故障节点列表：
   - 故障编号
   - 故障名称
   - 标题层级
   - 下级故障编号
   - 故障现象
   - 故障原因
   - 解决办法/解决方法
   - 是否叶子节点
6. 校验故障编号：
   - 不为空
   - 不重复
   - 与 `下级故障` 引用一致
7. 为每个节点生成唯一文件名和类名，并使用完整故障编号作为注册编号；生成前检查中文故障名称是否已被翻译成可读英文语义名称。
8. 在 `src/diagnosis_tool/failure_mode_realization/urma/` 下生成 `.h` 文件，声明派生类。
9. 在 `src/diagnosis_tool/failure_mode_realization/urma/` 下生成 `.cpp` 文件：
   - include 自身头文件
   - include `../../failure_mode_factory.h`
   - 按需 include `urma_log_matcher.h` 和日志匹配依赖
   - 定义 `AutoRegister`，变量名固定为 `g_urma`，传入完整故障编号
   - 实现所有虚函数
10. 如果构建系统需要显式枚举源文件，检查 `src/diagnosis_tool/CMakeLists.txt`，按现有风格补充 `failure_mode_realization/urma/` 下的新 `.cpp`。
    - 如果生成了 `urma_log_matcher.cpp`，必须同时补充到构建系统。
11. 生成后执行格式和构建检查：
    - 至少运行可用的格式化或静态检查命令
    - 如果项目有明确构建命令，运行最小构建验证
12. 最终说明生成了哪些文件、是否更新构建文件、验证结果以及任何保守 `IsValid` 实现的原因。

## 质量要求

1. 生成的每个类必须能与 `FailureMode` 基类签名匹配。
2. 每个故障编号必须通过 `AutoRegister` 注册一次且只注册一次，注册变量名固定为 `g_urma`，注册编号必须是完整故障编号（例如 `urma_001`）。
3. 叶子节点 `AnalyzeRootCause` 必须返回 `RootCause(true, ...)`。
4. 非叶子节点 `AnalyzeRootCause` 必须返回 `RootCause(false, ...)`。
5. `GetName`、`GetRootCauseDesc`、`GetFixSuggDesc`、`GetValidationMethodDesc`、`GetId` 不得返回空字符串，除非故障树原字段确实为空且无法推断。
6. `IsValid` 优先实现真实可执行的日志匹配；返回 `true` 时必须通过 `logContent` 返回匹配到的日志或可观测内容，返回 `false` 时必须清空 `logContent`。
7. 无法可靠实现自动匹配时，`IsValid` 保守返回 `false` 并在 `GetValidationMethodDesc` 中保留人工判定依据。
8. 不要把不同故障编号合并到同一个类。
9. 不要为不存在于故障树的故障模式生成代码。
10. 不要编造日志路径、环境变量、修复命令或工程 helper。
11. 生成代码后必须复查是否包含未转义字符串、重复类名和重复注册编号。
12. 生成代码后必须复查文件名和类名是否存在 `failure`、`unknown`、`node` 等无语义兜底命名；除非原始故障名称本身就是“其他故障”等泛化分类，否则必须改为对应英文语义名称。
13. 生成代码后必须复查 URMA 故障实现中是否重复定义 `MatchUrmaLogLine` 或等价 `URMA_LOG_PATH` 文件扫描函数；如存在重复实现，应提取或复用 `urma_log_matcher`。
