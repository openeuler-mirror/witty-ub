/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#include <gtest/gtest.h>

#include <filesystem>
#include <memory>
#include <string>
#include <typeindex>
#include <vector>

#include "logger.h"
#include "ubse_context.h"

namespace ubse::context {
// ubse_context.cpp 中的内部自由函数（外部链接），直接前向声明进行直测
std::vector<std::string> split(const std::string &s, char delimiter);
bool IsValidPodId(const std::string &id);
std::string TrimSpace(const std::string &str);
bool IsValidPathEntry(const std::string &entry, std::string &outPodId, std::string &outPath, std::string &outError);
} // namespace ubse::context

namespace {

// 被测实现中打日志，log4cplus 必须先初始化
struct LoggerInit {
    LoggerInit() noexcept { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// 测试用模块：A 无依赖，B 依赖 A，C 依赖 B
class ModA : public rack::module::RackModule {
public:
    RackResult Initialize() override { return RACK_OK; }
    void UnInitialize() override {}
    RackResult Start() override { return RACK_OK; }
    void Stop() override {}
};

class ModB : public rack::module::RackModule {
public:
    ModB() { dependencies.push_back(typeid(ModA)); }
    RackResult Initialize() override { return RACK_OK; }
    void UnInitialize() override {}
    RackResult Start() override { return RACK_OK; }
    void Stop() override {}
};

class ModC : public rack::module::RackModule {
public:
    ModC() { dependencies.push_back(typeid(ModB)); }
    RackResult Initialize() override { return RACK_OK; }
    void UnInitialize() override {}
    RackResult Start() override { return RACK_OK; }
    void Stop() override {}
};

// 可注入失败行为的模块
class ModFlaky : public rack::module::RackModule {
public:
    bool failInit = false;
    bool failStart = false;
    RackResult Initialize() override { return failInit ? RACK_FAIL : RACK_OK; }
    void UnInitialize() override {}
    RackResult Start() override { return failStart ? RACK_FAIL : RACK_OK; }
    void Stop() override {}
};

// 循环依赖：X <-> Y（两个构造均延后到双方定义之后实现，typeid 需要完整类型）
class ModX : public rack::module::RackModule {
public:
    ModX();
    RackResult Initialize() override { return RACK_OK; }
    void UnInitialize() override {}
    RackResult Start() override { return RACK_OK; }
    void Stop() override {}
};

class ModY : public rack::module::RackModule {
public:
    ModY();
    RackResult Initialize() override { return RACK_OK; }
    void UnInitialize() override {}
    RackResult Start() override { return RACK_OK; }
    void Stop() override {}
};

ModX::ModX() { dependencies.push_back(typeid(ModY)); }
ModY::ModY() { dependencies.push_back(typeid(ModX)); }

// 把字符串参数转换为 argv（字符串需保持存活）
std::vector<char *> MakeArgv(std::vector<std::string> &storage, const std::vector<std::string> &args)
{
    storage = args;
    std::vector<char *> argv;
    for (auto &arg : storage) {
        argv.push_back(arg.data());
    }
    argv.push_back(nullptr);
    return argv;
}

} // namespace

// ---------------------------------------------------------------------------
// 注意：UbseContext 是单例，状态跨用例累积，用例顺序有意安排：
// GetRole 缺参用例必须先于任何 --role 解析；循环依赖用例必须放最后（会永久污染模块排序）。
// ---------------------------------------------------------------------------

TEST(UbseGetRole, ReturnsEmptyWhenRoleArgMissing)
{
    // 尚未解析过任何 --role 参数：返回空串
    EXPECT_EQ(ubse::context::UbseContext::GetInstance().GetRole(), "");
}

// ---------------------------------------------------------------------------
// 纯函数直测
// ---------------------------------------------------------------------------

TEST(UbseSplit, SplitsByDelimiter)
{
    auto tokens = ubse::context::split("a,b,c", ',');
    ASSERT_EQ(tokens.size(), 3u);
    EXPECT_EQ(tokens[0], "a");
    EXPECT_EQ(tokens[1], "b");
    EXPECT_EQ(tokens[2], "c");
}

TEST(UbseSplit, EmptyAndEdgeCases)
{
    EXPECT_TRUE(ubse::context::split("", ',').empty());
    EXPECT_EQ(ubse::context::split("a", ',').size(), 1u);
    // 连续分隔符保留空段
    auto withEmpty = ubse::context::split("a,,b", ',');
    ASSERT_EQ(withEmpty.size(), 3u);
    EXPECT_EQ(withEmpty[1], "");
    // 尾随分隔符不产生空段
    EXPECT_EQ(ubse::context::split("a,", ',').size(), 1u);
}

TEST(UbseIsValidPodId, ValidatesFormat)
{
    EXPECT_TRUE(ubse::context::IsValidPodId("abc-123"));
    EXPECT_TRUE(ubse::context::IsValidPodId("a"));
    // 首尾必须为字母数字，长度 <= 253
    EXPECT_FALSE(ubse::context::IsValidPodId(""));
    EXPECT_FALSE(ubse::context::IsValidPodId("-abc"));
    EXPECT_FALSE(ubse::context::IsValidPodId("abc-"));
    // 大写字母与小写字母外的符号不被允许（大写被字符集校验拒绝）
    EXPECT_FALSE(ubse::context::IsValidPodId("Abc"));
    EXPECT_FALSE(ubse::context::IsValidPodId("ab_c"));
    // 边界长度
    EXPECT_TRUE(ubse::context::IsValidPodId(std::string(253, 'a')));
    EXPECT_FALSE(ubse::context::IsValidPodId(std::string(254, 'a')));
}

TEST(UbseTrimSpace, TrimsBothEnds)
{
    EXPECT_EQ(ubse::context::TrimSpace("  a b "), "a b");
    EXPECT_EQ(ubse::context::TrimSpace("\t x \r\n"), "x");
    EXPECT_EQ(ubse::context::TrimSpace("   "), "");
    EXPECT_EQ(ubse::context::TrimSpace(""), "");
}

TEST(UbseIsValidPathEntry, ParsesPodIdAndPath)
{
    std::string podId;
    std::string path;
    std::string error;
    ASSERT_TRUE(ubse::context::IsValidPathEntry("pod1:/var/log/umq.log", podId, path, error));
    EXPECT_EQ(podId, "pod1");
    EXPECT_EQ(path, "/var/log/umq.log");

    // 两侧空白被修剪
    ASSERT_TRUE(ubse::context::IsValidPathEntry(" pod1 : /var/log/x.log ", podId, path, error));
    EXPECT_EQ(podId, "pod1");
    EXPECT_EQ(path, "/var/log/x.log");
}

TEST(UbseIsValidPathEntry, RejectsBadEntries)
{
    std::string podId;
    std::string path;
    std::string error;
    // 缺少冒号
    EXPECT_FALSE(ubse::context::IsValidPathEntry("pod1", podId, path, error));
    EXPECT_FALSE(error.empty());
    // 非法 pod id 字符
    EXPECT_FALSE(ubse::context::IsValidPathEntry("pod 1:/var/log", podId, path, error));
    // 相对路径
    EXPECT_FALSE(ubse::context::IsValidPathEntry("pod1:relative/path", podId, path, error));
    // 空路径
    EXPECT_FALSE(ubse::context::IsValidPathEntry("pod1:", podId, path, error));
}

// ---------------------------------------------------------------------------
// ParseArgs
// ---------------------------------------------------------------------------

TEST(UbseParseArgs, ParsesKeyValuePairs)
{
    std::vector<std::string> storage;
    auto argv = MakeArgv(storage, {"prog", "--k1", "v1", "--k2", "v2"});
    EXPECT_EQ(ubse::context::UbseContext::GetInstance().ParseArgs(static_cast<int>(argv.size() - 1), argv.data()),
              RACK_OK);
    const auto &argMap = ubse::context::UbseContext::GetInstance().GetArgMap();
    EXPECT_EQ(argMap.at("k1"), "v1");
    EXPECT_EQ(argMap.at("k2"), "v2");
}

TEST(UbseParseArgs, EmptyArgsSucceed)
{
    std::vector<std::string> storage;
    auto argv = MakeArgv(storage, {"prog"});
    EXPECT_EQ(ubse::context::UbseContext::GetInstance().ParseArgs(static_cast<int>(argv.size() - 1), argv.data()),
              RACK_OK);
}

TEST(UbseParseArgs, RejectsMalformedArgs)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    std::vector<std::string> storage;
    // 非 -- 前缀
    auto argv = MakeArgv(storage, {"prog", "positional"});
    EXPECT_EQ(ctx.ParseArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // 只有 "--"：键为空
    argv = MakeArgv(storage, {"prog", "--", "v"});
    EXPECT_EQ(ctx.ParseArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // 末尾缺值
    argv = MakeArgv(storage, {"prog", "--key"});
    EXPECT_EQ(ctx.ParseArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // 值以 '-' 开头被视作缺值
    argv = MakeArgv(storage, {"prog", "--key", "-v"});
    EXPECT_EQ(ctx.ParseArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
}

// ---------------------------------------------------------------------------
// GetRole（依赖前面 ParseArgs 用例写入的 role 值）
// ---------------------------------------------------------------------------

TEST(UbseGetRole, ReturnsKnownRoles)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    std::vector<std::string> storage;
    auto argv = MakeArgv(storage, {"prog", "--role", "analyzer"});
    ASSERT_EQ(ctx.ParseArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_OK);
    EXPECT_EQ(ctx.GetRole(), "analyzer");

    argv = MakeArgv(storage, {"prog", "--role", "collector"});
    ASSERT_EQ(ctx.ParseArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_OK);
    EXPECT_EQ(ctx.GetRole(), "collector");
}

TEST(UbseGetRole, UnknownRoleMapsToUnknown)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    std::vector<std::string> storage;
    auto argv = MakeArgv(storage, {"prog", "--role", "bogus"});
    ASSERT_EQ(ctx.ParseArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_OK);
    EXPECT_EQ(ctx.GetRole(), "UNKNOWN");
}

TEST(UbseGetArgMap, ReflectsParsedArgs)
{
    // 自包含：本用例自行解析参数（ctest 按用例独立进程运行），随后键可见
    std::vector<std::string> storage;
    auto argv = MakeArgv(storage, {"prog", "--k1", "v1", "--role", "analyzer"});
    EXPECT_EQ(ubse::context::UbseContext::GetInstance().ParseArgs(static_cast<int>(argv.size() - 1), argv.data()),
              RACK_OK);
    const auto &argMap = ubse::context::UbseContext::GetInstance().GetArgMap();
    EXPECT_NE(argMap.find("k1"), argMap.end());
    EXPECT_NE(argMap.find("role"), argMap.end());
    EXPECT_EQ(argMap.at("role"), "analyzer");
}

// ---------------------------------------------------------------------------
// CreateWittyDir
// ---------------------------------------------------------------------------

TEST(UbseCreateWittyDir, BehaviorDependsOnDirectoryState)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    if (std::filesystem::exists("/var/witty-ub")) {
        // 目录已存在：直接成功
        EXPECT_EQ(ctx.CreateWittyDir(), RACK_OK);
    } else {
        // 生产缺陷：CreateWittyDir 使用 std::filesystem 抛异常重载，非 root 下
        // 创建 /var/witty-ub 失败时不返回 RACK_FAIL 而是抛出 filesystem_error
        // （异常未被捕获）。已报告勿修；这里断言现状，修复后应改为 EXPECT_EQ(..., RACK_FAIL)。
        EXPECT_THROW(ctx.CreateWittyDir(), std::filesystem::filesystem_error);
    }
}

// ---------------------------------------------------------------------------
// ParseTopoToolsArgs
// ---------------------------------------------------------------------------

TEST(UbseParseTopoToolsArgs, PodModeOnFullArgs)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    std::vector<std::string> storage;
    auto argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh", "--pod-mode", "on",
                                   "--umq-log-path", "pod1:/tmp/a.log,pod2:/tmp/b.log",
                                   "--pod-id", "pod1"});
    ASSERT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_OK);
    const auto args = ctx.GetTopoToolsArgs();
    EXPECT_EQ(args.networkMode, "fullmesh");
    EXPECT_EQ(args.podMode, "on");
    ASSERT_EQ(args.umq_log_path_map.size(), 2u);
    EXPECT_EQ(args.umq_log_path_map.at("pod1"), "/tmp/a.log");
    EXPECT_EQ(args.umq_log_path_map.at("pod2"), "/tmp/b.log");
    ASSERT_EQ(args.pod_id_list.size(), 1u);
    EXPECT_EQ(args.pod_id_list[0], "pod1");
}

TEST(UbseParseTopoToolsArgs, PodModeOnEmptyPodIdListCoversAllPods)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    std::vector<std::string> storage;
    auto argv = MakeArgv(storage, {"prog", "--network-mode", "clos", "--pod-mode", "on",
                                   "--umq-log-path", "pod1:/tmp/a.log,pod2:/tmp/b.log"});
    ASSERT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_OK);
    const auto args = ctx.GetTopoToolsArgs();
    EXPECT_EQ(args.networkMode, "clos");
    EXPECT_TRUE(args.pod_id_list.empty());
    EXPECT_EQ(args.umq_log_path_map.size(), 2u);
}

TEST(UbseParseTopoToolsArgs, PodModeOffDefaultsMessagesPath)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    std::vector<std::string> storage;
    auto argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh", "--pod-mode", "off"});
    ASSERT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_OK);
    const auto args = ctx.GetTopoToolsArgs();
    EXPECT_EQ(args.podMode, "off");
    // 未提供日志路径时默认 /var/log/messages，键为 normal
    ASSERT_EQ(args.umq_log_path_map.size(), 1u);
    EXPECT_EQ(args.umq_log_path_map.at("normal"), "/var/log/messages");
    EXPECT_TRUE(args.pod_id_list.empty());
}

TEST(UbseParseTopoToolsArgs, PodModeOffCustomPath)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    std::vector<std::string> storage;
    auto argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh", "--pod-mode", "off",
                                   "--umq-log-path", "/var/log/custom.log"});
    ASSERT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_OK);
    const auto args = ctx.GetTopoToolsArgs();
    EXPECT_EQ(args.umq_log_path_map.at("normal"), "/var/log/custom.log");
}

TEST(UbseParseTopoToolsArgs, RejectsInvalidInputs)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    std::vector<std::string> storage;
    // 缺 network-mode
    auto argv = MakeArgv(storage, {"prog", "--pod-mode", "on", "--umq-log-path", "p:/tmp/a.log"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // 缺 pod-mode
    argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // 非法 network-mode
    argv = MakeArgv(storage, {"prog", "--network-mode", "bogus", "--pod-mode", "off"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // 非法 pod-mode
    argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh", "--pod-mode", "bogus"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // 参数末尾缺值
    argv = MakeArgv(storage, {"prog", "--network-mode"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // 未知参数
    argv = MakeArgv(storage, {"prog", "--bogus", "x"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
}

TEST(UbseParseTopoToolsArgs, PodModeOnRequiresLogPath)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    std::vector<std::string> storage;
    auto argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh", "--pod-mode", "on"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
}

TEST(UbseParseTopoToolsArgs, RejectsBadPathEntries)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    std::vector<std::string> storage;
    // 条目缺冒号
    auto argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh", "--pod-mode", "on",
                                   "--umq-log-path", "pod1"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // 路径非绝对
    argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh", "--pod-mode", "on",
                              "--umq-log-path", "pod1:relative.log"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // pod id 重复
    argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh", "--pod-mode", "on",
                              "--umq-log-path", "pod1:/tmp/a.log,pod1:/tmp/b.log"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
}

TEST(UbseParseTopoToolsArgs, RejectsBadPodIdList)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    std::vector<std::string> storage;
    // pod-id 不在日志路径中
    auto argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh", "--pod-mode", "on",
                                   "--umq-log-path", "pod1:/tmp/a.log", "--pod-id", "ghost"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // 仅逗号：split 产生空 token，命中"空 pod id"分支
    argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh", "--pod-mode", "on",
                              "--umq-log-path", "pod1:/tmp/a.log", "--pod-id", ","});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_FAIL);
    // 现状记录：尾随逗号的空 token 会被 split 丢弃，列表仍合法（通过）
    argv = MakeArgv(storage, {"prog", "--network-mode", "fullmesh", "--pod-mode", "on",
                              "--umq-log-path", "pod1:/tmp/a.log", "--pod-id", "pod1,"});
    EXPECT_EQ(ctx.ParseTopoToolsArgs(static_cast<int>(argv.size() - 1), argv.data()), RACK_OK);
}

// ---------------------------------------------------------------------------
// 模块注册/排序/运行（状态累积，按声明顺序执行）
// ---------------------------------------------------------------------------

TEST(UbseModule, RegisterWithoutDependenciesFails)
{
    // 未先 AddModuleDependencies 的模块无法注册
    EXPECT_EQ(ubse::context::UbseContext::GetInstance().RegisterModule<ModFlaky>(), RACK_FAIL);
}

TEST(UbseModule, RegisterSortsAndRunsByDependency)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    ctx.AddModuleDependencies<ModA>();
    ctx.AddModuleDependencies<ModB>();
    ctx.AddModuleDependencies<ModC>();
    // 只注册 C：依赖闭包 A、B 一并入初始化集合
    ASSERT_EQ(ctx.RegisterModule<ModC>(), RACK_OK);

    auto a = std::make_shared<ModA>();
    auto b = std::make_shared<ModB>();
    auto c = std::make_shared<ModC>();
    ctx.InitModule<ModA>(a);
    ctx.InitModule<ModB>(b);
    ctx.InitModule<ModC>(c);

    const auto sorted = ctx.GetSortedModules();
    ASSERT_EQ(sorted.size(), 3u);
    // 依赖序：A 在 B 之前，B 在 C 之前
    const auto posA = std::find(sorted.begin(), sorted.end(), std::type_index(typeid(ModA)));
    const auto posB = std::find(sorted.begin(), sorted.end(), std::type_index(typeid(ModB)));
    const auto posC = std::find(sorted.begin(), sorted.end(), std::type_index(typeid(ModC)));
    ASSERT_NE(posA, sorted.end());
    ASSERT_NE(posB, sorted.end());
    ASSERT_NE(posC, sorted.end());
    EXPECT_TRUE(posA < posB);
    EXPECT_TRUE(posB < posC);

    // 初始化并启动全部模块成功；Run 复用同一流程
    EXPECT_EQ(ctx.InitAndStartModules(), RACK_OK);
    EXPECT_EQ(ctx.Run(0, nullptr), RACK_OK);
}

TEST(UbseModule, GetModuleReturnsRegisteredInstance)
{
    // 自包含：不依赖其他用例注册过的模块（ctest 会按用例独立进程运行）
    auto &ctx = ubse::context::UbseContext::GetInstance();
    auto a = std::make_shared<ModA>();
    auto b = std::make_shared<ModB>();
    ctx.InitModule<ModA>(a);
    ctx.InitModule<ModB>(b);
    EXPECT_EQ(ctx.GetModule<ModA>(), a);
    EXPECT_EQ(ctx.GetModule<ModB>(), b);
    // 未注册实例的类型返回空指针
    EXPECT_EQ(ctx.GetModule<ModFlaky>(), nullptr);
    // 重复 InitModule 覆盖旧实例
    auto a2 = std::make_shared<ModA>();
    ctx.InitModule<ModA>(a2);
    EXPECT_EQ(ctx.GetModule<ModA>(), a2);
    // 模块映射包含本用例初始化的模块
    EXPECT_GE(ctx.GetModuleMap().size(), 2u);
}

TEST(UbseModule, InitAndStartFailurePropagates)
{
    auto &ctx = ubse::context::UbseContext::GetInstance();
    ctx.AddModuleDependencies<ModFlaky>();
    ASSERT_EQ(ctx.RegisterModule<ModFlaky>(), RACK_OK);
    auto flaky = std::make_shared<ModFlaky>();
    ctx.InitModule<ModFlaky>(flaky);
    ctx.GetSortedModules(); // 重新排序，纳入 Flaky

    // Initialize 失败：InitAndStartModules 返回失败
    flaky->failInit = true;
    EXPECT_EQ(ctx.InitAndStartModules(), RACK_FAIL);

    // Start 失败：同样返回失败
    flaky->failInit = false;
    flaky->failStart = true;
    EXPECT_EQ(ctx.InitAndStartModules(), RACK_FAIL);
    EXPECT_EQ(ctx.Run(0, nullptr), RACK_FAIL);
}

TEST(UbseModule, CircularDependencyIsDetected)
{
    // 必须是最后一个模块用例：X/Y 进入初始化集合后排序永远失败。
    // 自包含：先注册无循环的 ModA，再引入 X/Y 循环（ctest 按用例独立进程运行）。
    auto &ctx = ubse::context::UbseContext::GetInstance();
    ctx.AddModuleDependencies<ModA>();
    ASSERT_EQ(ctx.RegisterModule<ModA>(), RACK_OK);
    ctx.AddModuleDependencies<ModX>();
    ctx.AddModuleDependencies<ModY>();
    ASSERT_EQ(ctx.RegisterModule<ModX>(), RACK_OK);

    const auto sorted = ctx.GetSortedModules();
    // 循环依赖的模块无法完成排序
    EXPECT_EQ(std::find(sorted.begin(), sorted.end(), std::type_index(typeid(ModX))), sorted.end());
    EXPECT_EQ(std::find(sorted.begin(), sorted.end(), std::type_index(typeid(ModY))), sorted.end());
    // 无依赖冲突的模块仍被正常排序
    EXPECT_NE(std::find(sorted.begin(), sorted.end(), std::type_index(typeid(ModA))), sorted.end());
}
