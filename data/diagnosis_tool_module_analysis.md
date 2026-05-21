# DiagnosisToolModule 执行逻辑分析

## 一、整体架构概览

整个诊断系统由 5 个核心类协作完成，形成 **"注册 → 加载 → 遍历 → 定界"** 的完整链路：

```
┌─────────────────────────────────────────────────────────────────┐
│                     DiagnosisToolModule                         │
│  (入口：Initialize → Start)                                     │
│                                                                 │
│  ┌──────────────┐   ┌──────────────────┐   ┌───────────────┐  │
│  │FailureMode    │   │FailureModeFactory│   │FailureMode    │  │
│  │Factory        │   │::Instance()      │   │Controller     │  │
│  │(注册表)       │   │(创建实例)         │   │(遍历控制)      │  │
│  └──────┬───────┘   └────────┬─────────┘   └───────┬───────┘  │
│         │                    │                      │           │
│         ▼                    ▼                      ▼           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              FailureMode (故障模式基类)                    │  │
│  │  ┌─────────────────┐  ┌─────────────────┐               │  │
│  │  │KvcacheConnFault │  │KvcacheConnFault │  ...           │  │
│  │  │001 (非叶子)      │  │003 (叶子)        │               │  │
│  │  └─────────────────┘  └─────────────────┘               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、故障注册机制（静态自动注册）

故障模式的注册发生在 **程序加载阶段**（`main()` 执行之前），通过 C++ 静态初始化机制完成。

### 注册流程

以 `kvcache_conn_fault_001.cpp` 为例：

```cpp
// 第1步：定义全局静态 AutoRegister 对象
static AutoRegister<KvcacheConnFault001> g_KvcacheConnFault001("kvcache_conn_fault_001");
```

这行代码的执行链路：

1. **`AutoRegister` 构造函数**（`failure_mode_factory.h:41-47`）被调用，传入 `typeId = "kvcache_conn_fault_001"`

2. 构造函数内部调用 `FailureModeFactory::Instance().Register(typeId, &AutoRegister::Create)`

3. **`FailureModeFactory::Register`** 将 `{typeId → Creator函数}` 存入 `m_creators` 哈希表

4. `Creator` 函数是 `AutoRegister::Create`，它调用 `std::make_shared<T>()` 创建实例

**关键设计**：每个 `.cpp` 文件中的 `static AutoRegister` 对象在程序启动时自动执行构造，无需手动调用注册代码。只要 `.cpp` 被编译链接，对应的故障模式就自动注册到工厂中。

注册完成后，`FailureModeFactory` 内部的 `m_creators` 哈希表结构如下：

```
m_creators = {
    "kvcache_conn_fault_001" → Creator(创建KvcacheConnFault001实例),
    "kvcache_conn_fault_002" → Creator(创建KvcacheConnFault002实例),
    ...
    "kvcache_conn_fault_050" → Creator(创建KvcacheConnFault050实例),
    "005"                     → Creator(创建HwBreak005实例),     // 已有示例
}
```

---

## 三、故障树加载与实例化（Initialize 阶段）

### InitializeFailureModeTree 执行流程

`diagnosis_tool_module.cpp:38-82` 的 `InitializeFailureModeTree()` 完成以下工作：

```
读取 JSON 文件 → 解析 → 创建实例 → 建立父子关系 → 识别子根节点
```

具体步骤：

**1. 读取并解析 JSON 文件**

从 `/var/witty-ub/data/failure_mode_tree.json` 读取，结构为：
```json
{
    "kvcache_conn": {
        "kvcache_conn_fault_001": ["kvcache_conn_fault_002", "kvcache_conn_fault_008", ...],
        "kvcache_conn_fault_002": ["kvcache_conn_fault_003", ...],
        ...
    }
}
```

**2. 遍历 JSON，填充三个核心数据结构**

对每个 `outerKey`（如 `"kvcache_conn"`），遍历其内部的所有故障节点：

```cpp
// 对每个 innerKey（如 "kvcache_conn_fault_001"）：
failureModeInstanceMap[innerKey] = FailureModeFactory::Instance().Create(innerKey);
// → 通过工厂创建 FailureMode 实例

// 对每个 children 元素：
failureModeInstanceMap[innerKey]->AddSubFailureMode(element.asString());
// → 在实例上添加子故障ID
```

**3. 识别子根节点（subRootFailureModes）**

```cpp
for (std::string failureMode : allFailureModes) {
    if (nonSubRootFailureModes.find(failureMode) == nonSubRootFailureModes.end()) {
        subRootFailureModes.push_back(failureMode);
    }
}
```

逻辑：**从未出现在任何节点的 children 列表中的节点就是子根节点**。对于 `kvcache_conn` 模块，`kvcache_conn_fault_001` 从未作为其他节点的 child 出现，所以它是子根节点。

**初始化完成后的三个核心数据结构：**

| 数据结构 | 类型 | 内容 |
|---------|------|------|
| `failureModeJson` | `map<string, map<string, vector<string>>>` | JSON 原始结构，按模块分组 |
| `failureModeInstanceMap` | `map<string, shared_ptr<FailureMode>>` | 故障ID → 实例映射 |
| `subRootFailureModesMap` | `map<string, vector<string>>` | 模块名 → 子根节点ID列表 |

---

## 四、故障遍历与根因定界（Start 阶段）

这是整个系统最核心的部分，采用 **深度优先遍历（DFS）** 算法在故障树上进行匹配。

### Start() 执行流程

`diagnosis_tool_module.cpp:112-133`：

```cpp
RackResult DiagnosisToolModule::Start()
{
    for (auto subRootFailures : subRootFailureModesMap) {
        // 对每个模块（如 "kvcache_conn"）
        for (auto subRootFailureModes : subRootFailures.second) {
            // 从子根节点开始 DFS
            Visit(FailureModeController(failureModeInstanceMap[subRootFailureModes]));
        }
        // 输出所有有效路径
        for (std::vector<FailureModeController> route : validRoutes) {
            // 打印路径：KVCache通断异常→用户侧错误→参数非法
        }
    }
}
```

### Visit() 递归遍历算法

`diagnosis_tool_module.cpp:92-110`：

```
Visit(controller):
    1. 调用 IsValid() 判断当前故障是否匹配
       → 不匹配：return false（回退）

    2. 匹配了：将当前节点加入 visited 路径

    3. 调用 AnalyzeRootCause() 判断是否叶子节点
       → isFinalRootCause=true（叶子）：
           将当前 visited 路径存入 validRoutes

       → isFinalRootCause=false（非叶子）：
           遍历所有子故障，递归 Visit
           如果所有子故障都不匹配（nonValidFlag=true）：
               将当前 visited 路径存入 validRoutes（停在当前非叶子节点）

    4. 从 visited 弹出当前节点（回溯）
    5. return true
```

### 用具体例子演示遍历过程

假设故障树如下，且实际故障是"参数非法"（fault_003）：

```
kvcache_conn_fault_001 (KVCache通断异常)         ← 非叶子
├── kvcache_conn_fault_002 (用户侧错误)           ← 非叶子
│   ├── kvcache_conn_fault_003 (参数非法)         ← 叶子 ✓ 匹配
│   ├── kvcache_conn_fault_004 (未配置Init)       ← 叶子 ✗ 不匹配
│   ├── kvcache_conn_fault_005 (buffer重复Publish)← 叶子 ✗ 不匹配
│   ├── kvcache_conn_fault_006 (批次超限)         ← 叶子 ✗ 不匹配
│   └── kvcache_conn_fault_007 (对象不存在)       ← 叶子 ✗ 不匹配
├── kvcache_conn_fault_008 (DS进程内错误)         ← 非叶子 ✗ 不匹配
├── ...
```

遍历过程：

```
1. Visit(001)
   IsValid()=true (检测到KVCache错误码非0)
   visited = [001]
   AnalyzeRootCause() → isFinalRootCause=false (非叶子)

   2. Visit(002) ← 001的子节点
      IsValid()=true (检测到错误码2/3/8)
      visited = [001, 002]
      AnalyzeRootCause() → isFinalRootCause=false (非叶子)

      3. Visit(003) ← 002的子节点
         IsValid()=true (检测到K_INVALID)
         visited = [001, 002, 003]
         AnalyzeRootCause() → isFinalRootCause=true (叶子!)
         validRoutes += [001, 002, 003]  ← 记录完整路径
         visited.pop → [001, 002]
         return true

      4. Visit(004) ← 002的子节点
         IsValid()=false (无ConnectOptions was not configured)
         return false

      5-7. Visit(005/006/007) → 都不匹配, return false

      nonValidFlag=false (因为003匹配了)
      visited.pop → [001]

   8. Visit(008) ← 001的子节点
      IsValid()=false (错误码不含19/23/29/31/32)
      return false

   ... 其余子节点也不匹配

   visited.pop → []
   return true

最终输出: KVCache通断异常→用户侧错误→参数非法
```

---

## 五、故障组织根因的核心机制总结

故障之间通过 **三重关联** 组织根因：

| 关联方式 | 实现位置 | 作用 |
|---------|---------|------|
| **1. AutoRegister 注册** | 每个 `.cpp` 的 `static AutoRegister<T> g_xxx("id")` | 将故障类注册到工厂，使 `Create("id")` 能创建实例 |
| **2. AddSubFailureMode 父子关系** | 构造函数中 `AddSubFailureMode("child_id")` | 运行时 `GetSubFailureModes()` 返回子故障列表，驱动 DFS 遍历 |
| **3. AnalyzeRootCause 叶子判定** | 叶子返回 `RootCause(true, ...)`，非叶子返回 `RootCause(false, ...)` | 控制遍历是否继续深入：`false` → 继续遍历子节点；`true` → 停止，当前为最终根因 |

**根因定界的核心逻辑**：从子根节点开始 DFS，每一层先验证 `IsValid()`，匹配后通过 `AnalyzeRootCause()` 判断是否叶子——叶子即为最终根因，非叶子则继续向下匹配子故障，直到找到最深层的匹配叶子节点。如果非叶子节点的所有子节点都不匹配，则该非叶子节点本身作为当前最深层根因。
