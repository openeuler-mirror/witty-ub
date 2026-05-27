---
name: "diagnosis-code-generation-urma"
description: "根据 urma_failure_mode_tree.md 故障模式树生成对应的 C++ FailureMode 实现代码。"
---

# diagnosis-code-generation-urma

## 目标

读取 `urma-failure-mode-generator` skill 生成的 URMA 故障模式树文件，将其中每个故障模式节点转换为 `src/diagnosis_tool/failure_mode_realization/urma/` 下的 C++ `FailureMode` 派生类实现，并确保类定义、注册编号、根因分析和故障校验逻辑与故障树内容一致。

适用场景：

- 为 URMA 组件故障进行定界分析
- 将 URMA 故障模式树转化为可执行的诊断代码

## 输入

- `failure_mode_tree_path`：必选，故障模式树 Markdown 文件路径，通常为 `./data/urma_failure_modes_tree.md`

输入要求：

1. `failure_mode_tree_path` 必须是可访问的 Markdown 文件
2. 故障树节点必须包含以下字段：
   - `故障编号`
   - `故障现象`
   - `故障原因`
   - `解决办法`
   - `函数名`
3. `FailureMode` 基类定义以 `src/diagnosis_tool/failure_mode.h` 为准。
4. 生成代码风格参考 `src/diagnosis_tool/failure_mode_realization/` 下已有样例

## 输出

输出目录：

- `src/diagnosis_tool/failure_mode_realization/urma/`

每个故障模式节点生成两个文件：

- `<class_file_name>.h`
- `<class_file_name>.cpp`

其中：

1. `<class_file_name>` 格式固定为`urma_failure_<故障编号数字>`，故障编号数字为故障编号的三位数字码
2. 类名使用 PascalCase，格式固定为 `UrmaFailure<故障编号数字>`
3. `.h` 文件声明 `FailureMode` 派生类
4. `.cpp` 文件需实现相应虚函数，并使用 `AutoRegister` 注册带组件命名空间的完整故障编号
5. 不要覆盖用户已有的手工实现，尤其是框架代码部分，除非用户明确要求更新

### FailureMode 基类契约

以 `src/diagnosis_tool/failure_mode.h` 中定义为准，生成类必须实现以下接口：

```cpp
std::string GetName() const override;
std::string GetValidationMethodDesc() const override;
bool IsValid() override;
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
class UrmaFailure001 : public FailureMode {
public:
    UrmaFailure001() noexcept = default;
    bool IsValid() override;
    std::string GetName() const override;
    std::string GetRootCauseDesc() const override;
    RootCause AnalyzeRootCause() override;
    std::string GetFixSuggDesc() const override;
    std::string GetValidationMethodDesc() const override;
    std::string GetId() const override;
};
} // namespace diag
```

## 生成规则

### 故障树解析规则

解析 `urma_failure_mode_tree.md` 时：

1. 以 Markdown 标题层级识别故障树层级
2. 每个标题下直到下一个同级或更高级标题前的字段属于当前故障模式
3. 故障名称取标题去掉前置数字后的文本，例如 `##### 1.1.1 get tp list 错误码 -2` 的名称为 `get tp list 错误码 -2`。
4. `故障编号` 是生成注册编号和 `GetId` 的来源，例如 `urma_001` 对应注册编号 `urma_001`；需要数字部分时可从中派生 `001`

### 单个故障模式类生成规则

每个故障模式节点生成一个从 `FailureMode` 派生的类：

1. 注册变量名统一为 `g_urma`，注册编号使用完整故障编号，避免与其他组件的裸数字注册号冲突：

```cpp
static AutoRegister<UrmaFailure001> g_urma("urma_001");
```

2. `GetId` 返回完整故障编号，例如故障编号 `urma_001` 返回 `urma_001`
3. `GetName` 返回故障名称
4. `GetRootCauseDesc` 返回 `故障原因` 字段内容
5. `GetFixSuggDesc` 返回 `解决办法` 字段内容
6. `GetValidationMethodDesc` 根据 `故障现象` 生成描述性文字
7. `AnalyzeRootCause` 根据是否为叶节点生成：
   - 非叶节点：`return RootCause(false, GetRootCauseDesc());`
   - 叶节点：`return RootCause(true, GetRootCauseDesc());`
8. `IsValid` 的实现根据是否为叶节点生成：
   - 非叶节点：`return true;`
   - 叶节点：根据 `故障现象` 生成校验逻辑，需要调用urma_log_helper.h的RunCommand方法，根据 `故障现象` 中描述的现象生成命令（通常需要匹配函数名和日志字面量）进行字符串匹配并返回日志内容，然后对日志信息进行提取，最后返回是否匹配成功的布尔值；对于多个字符串匹配，需要同时满足
```cpp
bool UrmaFailure002::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_provider_bond_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Provider Bond register ops failed'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}
```

### 字符串与代码安全规则

1. C++ 字符串必须正确转义双引号、反斜杠、换行和不可见字符。
2. 中文文本可以保留为 UTF-8。
3. 生成代码不要引入全局 using namespace
4. 单个故障模式 `.cpp` 只包含自身头文件、`../../failure_mode_factory.h` 和必要依赖
5. `URMA_LOG_PATH` 日志扫描 helper 已统一声明在 `src/diagnosis_tool/failure_mode_realization/urma/urma_log_helper.h`，不允许新增额外的辅助函数

## 步骤

1. 校验 `failure_mode_tree_path` 是否存在。
2. 读取 `src/diagnosis_tool/failure_mode.h`，确认 `FailureMode` 接口签名。
3. 读取 `src/diagnosis_tool/failure_mode_realization/` 下已有 `.h`、`.cpp`，确认本仓库代码风格、注册方式和命名习惯。
4. 确认输出目录 `src/diagnosis_tool/failure_mode_realization/urma/` 存在；不存在时先创建。
5. 解析故障树 Markdown，生成故障节点列表：
   - 故障编号
   - 故障名称
   - 标题层级
   - 故障现象
   - 故障原因
   - 解决办法
   - 是否叶子节点
6. 校验故障编号：
   - 不为空
   - 不重复
7. 为每个节点生成唯一文件名和类名，并使用完整故障编号作为注册编号
8. 8. 在 `src/diagnosis_tool/failure_mode_realization/urma/` 下生成 `.h` 文件，声明派生类。
9. 在 `src/diagnosis_tool/failure_mode_realization/urma/` 下生成 `.cpp` 文件：
   - include 自身头文件
   - include `../../failure_mode_factory.h`
   - 按需 include `urma_log_helper.h` 和日志匹配依赖
   - 定义 `AutoRegister`，变量名固定为 `g_urma`，传入完整故障编号
   - 实现所有要求的虚函数
10. 如果构建系统需要显式枚举源文件，检查 `src/diagnosis_tool/CMakeLists.txt`，按现有风格补充 `failure_mode_realization/urma/` 下的新 `.cpp`。
11. 生成后执行格式和构建检查：
   - 至少运行可用的格式化或静态检查命令
   - 如果项目有明确构建命令，运行最小构建验证
12. 最终说明生成了哪些文件、是否更新构建文件、验证结果

## 质量自检

1. 生成的每个类必须能与 `FailureMode` 基类签名匹配。
2. 每个故障编号必须通过 `AutoRegister` 注册一次且只注册一次，注册变量名固定为 `g_urma`，注册编号必须是完整故障编号（例如 `urma_001`）。
3. 叶子节点 `AnalyzeRootCause` 必须返回 `RootCause(true, ...)`，非叶子节点 `AnalyzeRootCause` 必须返回 `RootCause(false, ...)`。
4. `GetName`、`GetRootCauseDesc`、`GetFixSuggDesc`、`GetValidationMethodDesc`、`GetId` 不得返回空字符串，除非故障树原字段确实为空且无法推断。
5. `IsValid` 对于叶节点优先实现真实可执行的日志匹配逻辑，除非故障现象无法通过现有日志匹配实现，此时保守返回 `false`；非叶节点无条件返回 `true`。
6. 不要把不同故障编号合并到同一个类。
7. 不要为不存在于故障树的故障模式生成代码。
8. 不要编造日志路径、环境变量、修复命令或工程 helper。
9. 生成代码后必须复查是否包含未转义字符串、重复类名和重复注册编号。
10. 生成代码后必须复查文件名和类名是否存在 `failure`、`unknown`、`node` 等无语义兜底命名；除非原始故障名称本身就是“其他故障”等泛化分类，否则必须改为对应英文语义名称。
11. 生成代码后必须复查 URMA 故障实现中是否重复定义 helper 函数或引入重复依赖；如果需要日志匹配 helper，只能调用 `urma_log_helper.h/.cpp` 中的函数，不允许额外新增辅助函数。
