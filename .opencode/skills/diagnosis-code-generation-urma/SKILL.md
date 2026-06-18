---
name: "diagnosis-code-generation-urma"
description: "根据 urma_failure_mode.json 故障模式列表生成对应的 C++ FailureMode 实现代码。"
---

# diagnosis-code-generation-urma

## 目标

读取 `urma_failure_mode.json` 故障模式列表文件，将其中每个故障模式节点转换为 `src/diagnosis_tool/failure_mode_realization/urma/` 下的 C++ `FailureMode` 派生类实现，并确保类定义、注册编号、根因分析和故障校验逻辑与故障树内容一致。

适用场景：

- 为 URMA 组件故障进行定界分析
- 将 URMA 故障模式列表转化为可执行的诊断代码

## 输入

- `failure_mode_path`：必选，故障模式列表 Markdown 文件路径，通常为 `./data/kvcache/urma_failure_mode.json`

输入要求：

1. `failure_mode_path` 必须是可访问的 JSON 文件
2. 故障模式节点必须包含以下字段：
   - `故障编码`
   - `故障名称`
   - `故障现象`
   - `故障原因`
   - `解决办法`
   - 叶子故障模式节点需要包含`函数名`，顶层故障模式（非叶节点）不需要
3. `FailureMode` 基类定义以 `src/diagnosis_tool/failure_mode.h` 为准。
4. 生成代码风格参考 `.opencode/skills/diagnosis-code-generation-urma/examples` 下的已有样例

## 输出

输出目录：

- `src/diagnosis_tool/failure_mode_realization/urma/`

每个故障模式节点生成两个文件：

- `<class_file_name>.h`
- `<class_file_name>.cpp`

其中：

1. `<class_file_name>` 格式固定为`urma_failure_<故障编码数字>`，故障编码数字为故障编码的三位数字码
2. 类名使用 PascalCase，格式固定为 `UrmaFailure<故障编码数字>`
3. `.h` 文件声明 `FailureMode` 派生类
4. `.cpp` 文件需实现相应虚函数，并使用 `AutoRegister` 注册带组件命名空间的完整故障编码
5. 不要覆盖用户已有的手工实现，尤其是框架代码部分，除非用户明确要求更新

## 生成规则

### FailureMode 基类契约

以 `src/diagnosis_tool/failure_mode.h` 中定义为准，生成类必须实现以下接口：

```cpp
virtual std::string GetName() const = 0;
virtual std::string GetValidationMethodDesc() const = 0;
virtual bool IsValid(const std::vector<std::string>& fields) = 0;
virtual std::string GetRootCauseDesc() const = 0;
virtual RootCause AnalyzeRootCause();
virtual std::string GetFixSuggDesc() const = 0;
virtual std::string GetId() const = 0;
```

### 故障树解析规则

解析 `urma_failure_mode_tree.md` 时：

1. 以 Markdown 标题层级识别故障树层级
2. 每个标题下直到下一个同级或更高级标题前的字段属于当前故障模式
3. 故障名称取标题去掉前置数字后的文本，例如 `##### 1.1.1 get tp list 错误码 -2` 的名称为 `get tp list 错误码 -2`。
4. `故障编码` 是生成注册编号和 `GetId` 的来源，例如 `urma_001` 对应注册编号 `urma_001`；需要数字部分时可从中派生 `001`

### 故障模式字段映射

1. `故障编码` 映射到 `GetId()` 返回值，并用于类命名、文件命名和 `AutoRegister` 注册编号
2. `故障名称` 映射到 `GetName()` 返回值
3. `故障现象` 用于 `GetValidationMethodDesc()` 的描述文本
4. `故障原因` 用于 `GetRootCauseDesc()` 的描述文本
5. `解决办法` 用于 `GetFixSuggDesc()` 的描述文本
6. `AnalyzeRootCause()` 方法默认返回一个包含 `GetRootCauseDesc()` 描述的 `RootCause` 对象，`RootCause`的第一个布尔参数表示当前故障是否为根因，参考故障模式树文件 `data/failure_mode_tree.json`：
	- 如果该故障模式的故障编码对应的节点在故障模式树中是叶子节点，则第一个参数为 `true`
	- 否则为 `false`
7. `IsValid()` 方法基于故障现象的描述实现，通常需要根据故障现象中提到的关键字段进行校验，一般只有对关键日志进行指定字符串匹配的校验逻辑
   - 故障现象提到依次匹配多个关键词时，`IsValid()` 方法取`message`为`fields[7]`，对多个关键词匹配使用逻辑与连接进行校验

### 注册变量规则

统一为 `g_urma`，注册编号为故障编码，如：
```cpp
static AutoRegister<UrmaFailureXXX> g_urma("urma_XXX");
```

## 步骤

1. 校验 `urma_failure_mode.json` 文件是否存在，解析并提取每个故障模式的相关字段
2. 读取 `src/diagnosis_tool/failure_mode.h`，确认 `FailureMode` 接口签名
3. 根据提取的故障模式字段，生成对应的 `.h` 和 `.cpp` 文件，确保类定义、方法实现和注册编号符合规范
4. 在生成的 `.cpp` 文件中实现各个虚函数，特别是 `IsValid()` 方法需要根据故障现象中的描述实现相应的校验逻辑

## 质量自检

1. 确认生成的类名、文件名和注册编号与故障编码一致
2. 确认所有必需的虚函数都已实现，并且返回值符合预期
3. 确认 `IsValid()` 方法的实现逻辑与故障现象中的描述一致，能够正确校验输入字段
4. 确认生成的代码风格与已有样例一致，且没有覆盖用户已有的手工实现
5. 当一行字符超过120时，需进行适当换行处理，确保代码风格与.clang-format文件一致
