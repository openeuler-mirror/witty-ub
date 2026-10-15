/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * 测试目标：src/diagnosis_tool/diagnosis_tool_module.cpp（370 行，0%）
 */

#include <gtest/gtest.h>

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

// 访问私有成员便于直测；必须用带目录的路径，避免解析到 brpc_diag_tool 的同名头。
#define private public
#include "diagnosis_tool/diagnosis_tool_module.h"
#undef private

#include "logger.h"
#include "temp_dir.h"
#include "ubse_context.h"

namespace {

// 被测实现打日志走 log4cplus，必须先初始化，否则崩溃。
struct LoggerInit {
    LoggerInit() noexcept { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// RAII 临时目录（公共实现见 temp_dir.h）

// ---- 合法规则集（与引擎测试同构；BuildIndices 要求含条件 access 规则）----
const char *KVCACHE_JSON = R"([
    {"故障编号":"kvcache_root", "故障名称":"root", "文件名":"kvc_root.cpp", "故障现象":"向下级匹配",
     "故障原因":"c1", "解决办法":"s1", "函数名":"RootFunc", "节点类型":"access_log_entry", "错误码":1001},
    {"故障编号":"kvcache_cond", "故障名称":"cond", "文件名":"kvc_cond.cpp", "故障现象":"向下级匹配",
     "故障原因":"c2", "解决办法":"s2", "函数名":"CondFunc", "节点类型":"access_log_entry",
     "匹配条件":{"status_code":1002, "resp_msg_nonempty":true}},
    {"故障编号":"kvcache_runtime", "故障名称":"rt", "文件名":"kvc_rt.cpp", "故障现象":"依次匹配`err`、`timeout`",
     "故障原因":"c3", "解决办法":"s3", "函数名":"RtFunc", "节点类型":"runtime_log"}
])";

const char *URMA_JSON = R"([
    {"故障编号":"urma_iface", "故障名称":"iface", "文件名":"u_iface.cpp", "故障现象":"向下级匹配",
     "故障原因":"c4", "解决办法":"s4", "函数名":"IfaceFunc"},
    {"故障编号":"urma_fail", "故障名称":"ufail", "文件名":"u_fail.cpp", "故障现象":"依次匹配`urma err`",
     "故障原因":"c5", "解决办法":"s5", "函数名":"UfailFunc"}
])";

const char *TREE_JSON = R"({
    "kvcache": {
        "kvcache_root": ["kvcache_runtime"]
    },
    "urma": {
        "urma_iface": ["urma_fail"]
    }
})";

// 在临时目录内布置一套合法规则
void WriteRules(TempDir &wittyDir)
{
    wittyDir.Write("data/kvcache/kvcache_failure_mode.json", KVCACHE_JSON);
    wittyDir.Write("data/urma/urma_failure_mode.json", URMA_JSON);
    wittyDir.Write("data/failure_mode_tree.json", TREE_JSON);
}

void SetWittyDir(const std::filesystem::path &path)
{
    ::setenv("WITTY_DIR", path.string().c_str(), 1);
}

// 时间格式说明：模块的时间窗过滤只识别 "dddd-dd-ddTdd:dd:dd"（T 分隔），
// 而 --start-time/--end-time 参数是空格格式（正则校验 + ToTimestampTBound 转换）。
const char *ACCESS_HIT =
    "2024-01-15T10:30:00 | I | kvc_root.cpp:RootFunc:42 | pod1 | 123:456 | trace1 | cluster1 | "
    "1001 | action1 | 10 | 100 | req | ";
const char *ACCESS_EARLY =
    "2024-01-15T09:30:00 | I | kvc_root.cpp:RootFunc:42 | pod1 | 123:456 | trace1 | cluster1 | "
    "1001 | action1 | 10 | 100 | req | ";
const char *RUNTIME_HIT =
    "2024-01-15T10:30:05 | E | kvc_rt.cpp:RtFunc:42 | pod1 | 123:456 | trace1 | cluster1 | err and timeout";
const char *RUNTIME_LATE =
    "2024-01-15T12:30:00 | E | kvc_rt.cpp:RtFunc:42 | pod1 | 123:456 | trace1 | cluster1 | err and timeout";

// 通过 UbseContext::ParseArgs 覆盖式设置模块参数（单例 argMap 无法清空，必须全量覆盖）。
void SetModuleArgs(const std::vector<std::pair<std::string, std::string>> &args)
{
    std::vector<std::string> tokens{"test"};
    for (const auto &arg : args) {
        tokens.push_back("--" + arg.first);
        tokens.push_back(arg.second);
    }
    // C 接口边界：ParseArgs 只接受 char *argv[]，string 数组在此集中转换。
    std::vector<char *> argv;
    for (std::string &token : tokens) {
        argv.push_back(token.data());
    }
    ASSERT_EQ(ubse::context::UbseContext::GetInstance().ParseArgs(static_cast<int>(argv.size()), argv.data()),
              RACK_OK);
}

// 全量参数模板：全部 8 个 key 都覆盖，避免单例 argMap 残留（字段带默认值，按需覆盖）。
struct FullModuleArgs {
    std::string dsLogPath;
    std::string clientAccess = "client_access.log";
    std::string clientInfo = "client_info.log";
    std::string randomStr = "r1";
    std::string startTime = "2024-01-15 10:00:00";
    std::string endTime = "2024-01-15 11:00:00";
    std::string resource;
};

void SetFullModuleArgs(const FullModuleArgs &a)
{
    SetModuleArgs({
        {"ds-log-path", a.dsLogPath},
        {"ds-client-access-log-file", a.clientAccess},
        {"ds-client-info-log-file", a.clientInfo},
        {"ds-worker-access-log-file", ""},
        {"ds-worker-info-log-file", ""},
        {"resource-log-file", a.resource},
        {"start-time", a.startTime},
        {"end-time", a.endTime},
        {"random-str", a.randomStr},
    });
}

bool FileContains(const std::filesystem::path &path, const std::string &needle)
{
    std::ifstream in(path);
    std::stringstream buffer;
    buffer << in.rdbuf();
    return buffer.str().find(needle) != std::string::npos;
}

} // namespace

// ===========================================================================
// ParseDiagArgs：错误路径。MissingRequiredTimeArgsFail 必须最先运行——
// 它依赖单例 argMap 中尚无 start-time/end-time（其余用例会全量覆盖）。
// ===========================================================================

TEST(DiagnosisToolModuleArgs, MissingRequiredTimeArgsFail)
{
    TempDir ds("diagmod_args_ds");
    SetModuleArgs({{"ds-log-path", ds.Path().string()}});

    diag::DiagnosisToolModule module;
    EXPECT_NE(module.ParseDiagArgs(), RACK_OK);
}

TEST(DiagnosisToolModuleArgs, BadDsLogPathFails)
{
    TempDir ds("diagmod_args_ds");
    SetFullModuleArgs({"/nonexistent/ds/log/dir"});

    diag::DiagnosisToolModule module;
    EXPECT_NE(module.ParseDiagArgs(), RACK_OK);
}

TEST(DiagnosisToolModuleArgs, DsLogPathNotDirectoryFails)
{
    TempDir ds("diagmod_args_ds");
    ds.Write("afile.log", "x");
    SetFullModuleArgs({std::filesystem::path(ds.Path()).append("afile.log").string()});

    diag::DiagnosisToolModule module;
    EXPECT_NE(module.ParseDiagArgs(), RACK_OK);
}

TEST(DiagnosisToolModuleArgs, BadTimeFormatFails)
{
    TempDir ds("diagmod_args_ds");
    SetFullModuleArgs({ds.Path().string(), "client_access.log", "client_info.log", "r1",
                      "20240115 100000"});

    diag::DiagnosisToolModule module;
    EXPECT_NE(module.ParseDiagArgs(), RACK_OK);
}

TEST(DiagnosisToolModuleArgs, StartTimeNotBeforeEndFails)
{
    TempDir ds("diagmod_args_ds");
    SetFullModuleArgs({ds.Path().string(), "client_access.log", "client_info.log", "r1",
                      "2024-01-15 12:00:00", "2024-01-15 10:00:00"});

    diag::DiagnosisToolModule module;
    EXPECT_NE(module.ParseDiagArgs(), RACK_OK);
}

TEST(DiagnosisToolModuleArgs, FullArgsParseSuccessfully)
{
    TempDir ds("diagmod_args_ds");
    SetFullModuleArgs({ds.Path().string(), "ca.log", "ci.log", "rnd1"});

    diag::DiagnosisToolModule module;
    EXPECT_EQ(module.ParseDiagArgs(), RACK_OK);
    EXPECT_EQ(module.dsLogPath_, ds.Path().string());
    EXPECT_EQ(module.dsClientAccessLogFile_, "ca.log");
    EXPECT_EQ(module.dsClientInfoLogFile_, "ci.log");
    // 可选参数显式传空 → 值为空字符串
    EXPECT_TRUE(module.dsWorkerAccessLogFile_.empty());
    EXPECT_TRUE(module.resourceLogFile_.empty());
    EXPECT_EQ(module.startTimeStr_, "2024-01-15 10:00:00");
    EXPECT_EQ(module.endTimeStr_, "2024-01-15 11:00:00");
    EXPECT_EQ(module.randomStr_, "rnd1");
}

// ===========================================================================
// MappedReadFile
// ===========================================================================

TEST(DiagnosisToolModuleMappedFile, OpensAndReadsExistingFile)
{
    TempDir dir("diagmod_mmap");
    dir.Write("data.log", "hello mmap");

    diag::MappedReadFile file((dir.Path() / "data.log").string());
    EXPECT_TRUE(file.IsOpen());
    EXPECT_EQ(file.Content(), std::string_view("hello mmap"));
}

TEST(DiagnosisToolModuleMappedFile, HandlesEmptyFile)
{
    TempDir dir("diagmod_mmap");
    dir.Write("empty.log", "");

    diag::MappedReadFile file((dir.Path() / "empty.log").string());
    EXPECT_TRUE(file.IsOpen());
    EXPECT_TRUE(file.Content().empty());
}

TEST(DiagnosisToolModuleMappedFile, MissingFileIsNotOpen)
{
    diag::MappedReadFile file("/nonexistent/mapped/file.log");
    EXPECT_FALSE(file.IsOpen());
    EXPECT_TRUE(file.Content().empty());
}

// ===========================================================================
// ConfigureMergedPath
// ===========================================================================

TEST(DiagnosisToolModulePaths, CreatesAndClearsMergedDir)
{
    TempDir witty("diagmod_path_witty");
    witty.Write("log/stale.log", "old content");

    SetWittyDir(witty.Path());
    diag::DiagnosisToolModule module;
    module.randomStr_.clear();
    EXPECT_EQ(module.ConfigureMergedPath(), RACK_OK);
    EXPECT_EQ(module.mergedLogDir_, (witty.Path() / "log").string());
    EXPECT_TRUE(std::filesystem::is_directory(module.mergedLogDir_));
    // 旧文件被清空
    EXPECT_FALSE(std::filesystem::exists(witty.Path() / "log/stale.log"));
}

TEST(DiagnosisToolModulePaths, UsesRandomStrPrefix)
{
    TempDir witty("diagmod_path_witty");

    SetWittyDir(witty.Path());
    diag::DiagnosisToolModule module;
    module.randomStr_ = "abc42";
    EXPECT_EQ(module.ConfigureMergedPath(), RACK_OK);
    EXPECT_EQ(module.mergedLogDir_, (witty.Path() / "log_abc42").string());
    EXPECT_TRUE(std::filesystem::is_directory(module.mergedLogDir_));
}

TEST(DiagnosisToolModulePaths, FailsWhenWittyDirIsFile)
{
    TempDir witty("diagmod_path_witty");
    witty.Write("blocker", "x");

    SetWittyDir(witty.Path() / "blocker");
    diag::DiagnosisToolModule module;
    module.randomStr_.clear();
    // wittyDir 是文件，其下的 log 目录无法创建
    EXPECT_NE(module.ConfigureMergedPath(), RACK_OK);
}

// ===========================================================================
// 生命周期：RegArgs / Start（未初始化）/ Stop / UnInitialize
// ===========================================================================

TEST(DiagnosisToolModuleLifecycle, RegArgsIsNoop)
{
    diag::DiagnosisToolModule module;
    module.RegArgs();
    SUCCEED();
}

TEST(DiagnosisToolModuleLifecycle, StartWithoutInitializeFails)
{
    diag::DiagnosisToolModule module;
    EXPECT_NE(module.Start(), RACK_OK);
}

TEST(DiagnosisToolModuleLifecycle, StopAndUnInitializeAreSafeWithoutInit)
{
    diag::DiagnosisToolModule module;
    module.Stop();
    module.UnInitialize();
    SUCCEED();
}

TEST(DiagnosisToolModuleLifecycle, UnInitializeClearsEngineForRestart)
{
    TempDir witty("diagmod_life_witty");
    WriteRules(witty);
    TempDir ds("diagmod_life_ds");
    SetWittyDir(witty.Path());
    SetFullModuleArgs({ds.Path().string()});

    diag::DiagnosisToolModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);
    EXPECT_EQ(module.Start(), RACK_OK);
    module.UnInitialize();
    // 引擎被清空后 Start 失败
    EXPECT_NE(module.Start(), RACK_OK);
    module.Stop();
}

// ===========================================================================
// Initialize / Start 集成路径
// ===========================================================================

TEST(DiagnosisToolModuleRun, InitializeExtractsLogsAndStartWritesTrace)
{
    TempDir witty("diagmod_run_witty");
    WriteRules(witty);
    TempDir ds("diagmod_run_ds");
    // 早于窗的行被跳过；晚于窗的行触发提前停止
    ds.Write("client_access.log", std::string(ACCESS_EARLY) + "\n" + ACCESS_HIT + "\n");
    ds.Write("client_info.log", std::string(RUNTIME_HIT) + "\n" + RUNTIME_LATE + "\n");
    ds.Write("resource.log", "2024-01-15T10:40:00 | I | unrelated\n");

    SetWittyDir(witty.Path());
    SetFullModuleArgs({ds.Path().string(), "client_access.log", "client_info.log", "r1",
                      "2024-01-15 10:00:00", "2024-01-15 11:00:00", "resource.log"});

    diag::DiagnosisToolModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);

    const auto merged = witty.Path() / "log_r1";
    // 时间窗过滤后只剩窗内行
    ASSERT_TRUE(std::filesystem::exists(merged / "client_access.log"));
    {
        std::ifstream in(merged / "client_access.log");
        std::string firstLine;
        std::getline(in, firstLine);
        EXPECT_EQ(firstLine, std::string(ACCESS_HIT));
        std::string secondLine;
        EXPECT_FALSE(std::getline(in, secondLine)); // 只有一行
    }
    {
        std::ifstream in(merged / "client_info.log");
        std::string firstLine;
        std::getline(in, firstLine);
        EXPECT_EQ(firstLine, std::string(RUNTIME_HIT));
    }
    // other 分类（resource）只提取不参与分类映射
    EXPECT_TRUE(std::filesystem::exists(merged / "resource.log"));
    ASSERT_EQ(module.logTypeToPath_.count("access"), 1u);
    EXPECT_EQ(module.logTypeToPath_.at("access").size(), 1u);
    ASSERT_EQ(module.logTypeToPath_.count("runtime"), 1u);
    EXPECT_EQ(module.logTypeToPath_.at("runtime").size(), 1u);

    EXPECT_EQ(module.Start(), RACK_OK);
    const auto tracePath = merged / "failure_trace.log";
    ASSERT_TRUE(std::filesystem::exists(tracePath));
    EXPECT_TRUE(FileContains(tracePath, "kvcache_root"));
    EXPECT_TRUE(FileContains(tracePath, "kvcache_runtime"));

    module.Stop();
    module.UnInitialize();
}

TEST(DiagnosisToolModuleRun, DualClassifiedLogFeedsRuntimeThroughExtractedFile)
{
    TempDir witty("diagmod_dual_witty");
    WriteRules(witty);
    TempDir ds("diagmod_dual_ds");
    // 同一文件同时匹配 access 与 info 模式：先按 access 提取，再对已提取文件补喂 runtime
    ds.Write("dual.log", std::string(ACCESS_HIT) + "\n" + RUNTIME_HIT + "\n");

    SetWittyDir(witty.Path());
    SetFullModuleArgs({ds.Path().string(), "dual.log", "dual.log", "rd"});

    diag::DiagnosisToolModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);

    const auto merged = witty.Path() / "log_rd";
    ASSERT_TRUE(std::filesystem::exists(merged / "dual.log"));

    EXPECT_EQ(module.Start(), RACK_OK);
    const auto tracePath = merged / "failure_trace.log";
    ASSERT_TRUE(std::filesystem::exists(tracePath));
    EXPECT_TRUE(FileContains(tracePath, "kvcache_root"));
    EXPECT_TRUE(FileContains(tracePath, "kvcache_runtime"));

    module.UnInitialize();
}

TEST(DiagnosisToolModuleRun, EmptyWindowProducesEmptyTrace)
{
    TempDir witty("diagmod_empty_witty");
    WriteRules(witty);
    TempDir ds("diagmod_empty_ds");
    ds.Write("client_access.log", std::string(ACCESS_HIT) + "\n");

    SetWittyDir(witty.Path());
    // 时间窗在日志之后：所有行早于窗，提取结果为空
    SetFullModuleArgs({ds.Path().string(), "client_access.log", "client_info.log", "r2",
                      "2024-01-15 12:00:00", "2024-01-15 13:00:00"});

    diag::DiagnosisToolModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);
    const auto merged = witty.Path() / "log_r2";
    ASSERT_TRUE(std::filesystem::exists(merged / "client_access.log"));
    EXPECT_TRUE(module.engine_->GetTraceLogs().empty());

    EXPECT_EQ(module.Start(), RACK_OK);
    const auto tracePath = merged / "failure_trace.log";
    ASSERT_TRUE(std::filesystem::exists(tracePath));
    {
        std::ifstream in(tracePath);
        std::string content;
        std::getline(in, content);
        EXPECT_TRUE(content.empty());
    }
    module.UnInitialize();
}

TEST(DiagnosisToolModuleRun, InitializeFailsWithoutRules)
{
    TempDir witty("diagmod_norule_witty"); // 无规则文件
    TempDir ds("diagmod_norule_ds");

    SetWittyDir(witty.Path());
    SetFullModuleArgs({ds.Path().string()});

    diag::DiagnosisToolModule module;
    EXPECT_NE(module.Initialize(), RACK_OK);
}

TEST(DiagnosisToolModuleRun, InitializeFailsWithBadArgs)
{
    TempDir witty("diagmod_badargs_witty");
    WriteRules(witty);

    SetWittyDir(witty.Path());
    SetFullModuleArgs({"/nonexistent/ds/log/dir"});

    diag::DiagnosisToolModule module;
    // ParseDiagArgs 失败分支
    EXPECT_NE(module.Initialize(), RACK_OK);
}

// ===========================================================================
// 私有方法直测
// ===========================================================================

TEST(DiagnosisToolModuleInternals, FindMatchingFilesMatchesRecursively)
{
    TempDir dir("diagmod_find");
    dir.Write("client_access.log", "x");
    dir.Write("sub/deep/client_access.log", "x");
    dir.Write(".hidden.log", "x");
    dir.Write("other.txt", "x");

    diag::DiagnosisToolModule module;
    const auto exact = module.FindMatchingFiles(dir.Path().string(), "client_access.log");
    ASSERT_EQ(exact.size(), 2u); // 递归匹配子目录
    const auto wildcard = module.FindMatchingFiles(dir.Path().string(), "*.log");
    EXPECT_EQ(wildcard.size(), 2u); // 隐藏文件被跳过
    const auto txt = module.FindMatchingFiles(dir.Path().string(), "*.txt");
    EXPECT_EQ(txt.size(), 1u);
    EXPECT_TRUE(module.FindMatchingFiles(dir.Path().string(), "missing.log").empty());
    EXPECT_TRUE(module.FindMatchingFiles("/nonexistent/search/dir", "*").empty());
}

TEST(DiagnosisToolModuleInternals, CollectLogSourcesDeduplicates)
{
    TempDir ds("diagmod_collect");
    ds.Write("a.log", "x");
    ds.Write("b.log", "x");

    diag::DiagnosisToolModule module;
    module.dsLogPath_ = ds.Path().string();
    // 两个模式命中同一文件 → 去重；第三个模式无匹配仅告警
    module.dsClientAccessLogFile_ = "a.log";
    module.dsWorkerAccessLogFile_ = "a.log";
    module.dsClientInfoLogFile_ = "ghost.log";
    module.dsWorkerInfoLogFile_.clear();
    module.resourceLogFile_.clear();
    module.mergedLogDir_ = (ds.Path() / "merged").string();

    std::unordered_map<std::string, std::vector<std::string>> outputToSources;
    module.CollectLogSources(outputToSources);

    ASSERT_EQ(outputToSources.size(), 1u);
    const auto &sources = outputToSources.begin()->second;
    ASSERT_EQ(sources.size(), 1u);
    EXPECT_EQ(sources.front(), (ds.Path() / "a.log").string());
}

TEST(DiagnosisToolModuleInternals, ClassifyLogOutputsSplitsKinds)
{
    TempDir merged("diagmod_classify");
    const std::string a = (merged.Path() / "a.log").string();
    const std::string w = (merged.Path() / "w.log").string();
    const std::string x = (merged.Path() / "x.log").string();
    std::unordered_map<std::string, std::vector<std::string>> outputToSources{
        {a, {a}},
        {w, {w}},
        {x, {x}},
    };

    diag::DiagnosisToolModule module;
    module.dsClientAccessLogFile_ = "a.log";
    module.dsWorkerAccessLogFile_ = "w.log";
    module.dsClientInfoLogFile_ = "i.log";
    // w.log 同时命中 access 与 info 模式 → 双归属
    module.dsWorkerInfoLogFile_ = "w.log";

    std::vector<std::string> accessOutputs;
    std::vector<std::string> runtimeOutputs;
    std::vector<std::string> otherOutputs;
    module.ClassifyLogOutputs(outputToSources, accessOutputs, runtimeOutputs, otherOutputs);

    ASSERT_EQ(accessOutputs.size(), 2u);
    EXPECT_EQ(accessOutputs[0], a);
    EXPECT_EQ(accessOutputs[1], w);
    ASSERT_EQ(runtimeOutputs.size(), 1u);
    EXPECT_EQ(runtimeOutputs[0], w);
    ASSERT_EQ(otherOutputs.size(), 1u);
    EXPECT_EQ(otherOutputs[0], x);
}

TEST(DiagnosisToolModuleInternals, ProcessExtractedLineFiltersByWindow)
{
    TempDir witty("diagmod_pext_witty");
    WriteRules(witty);
    auto engine = diag::DiagnosisEngine::Create(witty.Path());
    ASSERT_NE(engine, nullptr);

    diag::DiagnosisToolModule module;
    module.engine_ = std::move(engine);

    const std::string startTime = "2024-01-15T10:00:00";
    const std::string endTime = "2024-01-15T11:00:00";
    bool inRange = false;
    std::ostringstream output;
    std::vector<std::string_view> runtimeLines;
    diag::DiagnosisToolModule::LineProcessContext ctx{startTime, endTime, inRange, output,
                                                      diag::DiagnosisToolModule::LogKind::ACCESS, false,
                                                      runtimeLines};

    // 早于窗：跳过，继续读
    EXPECT_TRUE(module.ProcessExtractedLine(ACCESS_EARLY, ctx));
    EXPECT_FALSE(inRange);
    EXPECT_TRUE(output.str().empty());

    // 窗内：写入并喂引擎（行尾 \r 被去除）
    const std::string withCr = std::string(ACCESS_HIT) + "\r";
    EXPECT_TRUE(module.ProcessExtractedLine(withCr, ctx));
    EXPECT_TRUE(inRange);
    EXPECT_EQ(output.str(), std::string(ACCESS_HIT) + "\n");
    EXPECT_FALSE(module.engine_->GetHitRoots().empty());

    // 无时间戳且 inRange：作为上下文行写入
    EXPECT_TRUE(module.ProcessExtractedLine("continuation line without timestamp", ctx));
    EXPECT_NE(output.str().find("continuation line without timestamp"), std::string::npos);

    // 晚于窗：停止读取
    EXPECT_FALSE(module.ProcessExtractedLine("2024-01-15T12:30:00 | I | too late", ctx));

    // 无时间戳且不在窗内：丢弃
    inRange = false;
    output.str("");
    EXPECT_TRUE(module.ProcessExtractedLine("dropped continuation", ctx));
    EXPECT_TRUE(output.str().empty());
}

TEST(DiagnosisToolModuleInternals, WriteExtractedLineDispatchesByKind)
{
    TempDir witty("diagmod_wline_witty");
    WriteRules(witty);
    auto engine = diag::DiagnosisEngine::Create(witty.Path());
    ASSERT_NE(engine, nullptr);

    diag::DiagnosisToolModule module;
    module.engine_ = std::move(engine);
    module.engine_->BeginDiagnosis();

    std::ostringstream output;
    std::vector<std::string_view> runtimeLines;
    module.WriteExtractedLine(output, ACCESS_HIT, diag::DiagnosisToolModule::LogKind::ACCESS, false, runtimeLines);
    module.WriteExtractedLine(output, RUNTIME_HIT, diag::DiagnosisToolModule::LogKind::RUNTIME, false, runtimeLines);
    module.WriteExtractedLine(output, RUNTIME_HIT, diag::DiagnosisToolModule::LogKind::RUNTIME, true, runtimeLines);
    module.WriteExtractedLine(output, "plain line", diag::DiagnosisToolModule::LogKind::NONE, false, runtimeLines);

    // 4 行全部落盘；mapped runtime 进入批量缓冲；access/runtime 已喂引擎
    EXPECT_NE(output.str().find(ACCESS_HIT), std::string::npos);
    EXPECT_NE(output.str().find("plain line"), std::string::npos);
    ASSERT_EQ(runtimeLines.size(), 1u);
    EXPECT_EQ(runtimeLines.front(), std::string_view(RUNTIME_HIT));
    EXPECT_FALSE(module.engine_->GetHitRoots().empty());
}

TEST(DiagnosisToolModuleInternals, ExtractLogLinesFailsOnBadPaths)
{
    TempDir dir("diagmod_extract");
    dir.Write("input.log", std::string(ACCESS_HIT) + "\n");

    diag::DiagnosisToolModule module;
    module.startTimeStr_ = "2024-01-15 10:00:00";
    module.endTimeStr_ = "2024-01-15 11:00:00";

    // 输入文件不存在
    EXPECT_FALSE(module.ExtractLogLinesByTimeWindow("/nonexistent/input.log", (dir.Path() / "out.log").string(),
                                                    false, diag::DiagnosisToolModule::LogKind::ACCESS));
    // 输出路径是目录 → 打不开
    EXPECT_FALSE(module.ExtractLogLinesByTimeWindow((dir.Path() / "input.log").string(), dir.Path().string(), false,
                                                    diag::DiagnosisToolModule::LogKind::ACCESS));
}

TEST(DiagnosisToolModuleInternals, ExtractLogLinesDirectoryInputFallsBackToStream)
{
    TempDir dir("diagmod_extract_dir");
    // 目录无法 mmap（也无法按行读取）→ 走 ifstream 兜底后失败
    diag::DiagnosisToolModule module;
    module.startTimeStr_ = "2024-01-15 10:00:00";
    module.endTimeStr_ = "2024-01-15 11:00:00";
    EXPECT_FALSE(module.ExtractLogLinesByTimeWindow(dir.Path().string(), (dir.Path() / "out.log").string(), false,
                                                    diag::DiagnosisToolModule::LogKind::ACCESS));
}

TEST(DiagnosisToolModuleInternals, FeedExtractedLogAccessAndMissingFile)
{
    TempDir dir("diagmod_feed");
    dir.Write("feed.log", std::string(ACCESS_HIT) + "\n");
    TempDir witty("diagmod_feed_witty");
    WriteRules(witty);
    auto engine = diag::DiagnosisEngine::Create(witty.Path());
    ASSERT_NE(engine, nullptr);

    diag::DiagnosisToolModule module;
    module.engine_ = std::move(engine);
    module.engine_->BeginDiagnosis();

    // mmap 路径 + ACCESS 逐行喂数
    EXPECT_TRUE(module.FeedExtractedLog((dir.Path() / "feed.log").string(),
                                        diag::DiagnosisToolModule::LogKind::ACCESS));
    EXPECT_NE(module.engine_->GetHitRoots().find("kvcache_root"), module.engine_->GetHitRoots().end());

    // 文件不存在 → 失败
    EXPECT_FALSE(module.FeedExtractedLog("/nonexistent/feed.log", diag::DiagnosisToolModule::LogKind::RUNTIME));
}

TEST(DiagnosisToolModuleInternals, StoreFailureTracesFailsOnBadOutputDir)
{
    TempDir witty("diagmod_store_witty");
    WriteRules(witty);
    auto engine = diag::DiagnosisEngine::Create(witty.Path());
    ASSERT_NE(engine, nullptr);

    diag::DiagnosisToolModule module;
    module.engine_ = std::move(engine);
    // 输出目录不存在 → 打开失败（用 /tmp 下不存在的子目录，避免触碰沙箱限制路径）
    module.mergedLogDir_ = (std::filesystem::temp_directory_path() / "diagmod_no_such_merged_dir").string();
    EXPECT_NE(module.StoreFailureTraces(), RACK_OK);
}
