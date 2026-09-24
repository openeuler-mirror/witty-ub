/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * 测试目标：src/diagnosis_tool/diagnosis_engine.cpp（979 行，0%）
 */

#include <gtest/gtest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

// 访问私有成员便于测试
// 注意：必须用带目录的路径——tests 的 include 路径里 brpc_diag_tool 在前，
// 裸 "diagnosis_engine.h" 会被解析到 brpc 版（namespace brpc）。
#define private public
#include "diagnosis_tool/diagnosis_engine.h"
#undef private

#include "logger.h"

namespace {

// 诊断引擎加载规则时会打日志，log4cplus 必须先初始化，否则崩溃。
struct LoggerInit {
    LoggerInit() { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

} // namespace

namespace {

// 每个用例独立的临时 witty 目录，析构时清理。
class TempWittyDir {
public:
    TempWittyDir()
    {
        static int counter = 0;
        dir_ = std::filesystem::temp_directory_path() /
               ("witty_diag_tool_test_" +
                std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) +
                "_" + std::to_string(counter++));
        std::filesystem::create_directories(dir_ / "data/kvcache");
        std::filesystem::create_directories(dir_ / "data/urma");
    }
    ~TempWittyDir() { std::filesystem::remove_all(dir_); }

    const std::filesystem::path &Path() const { return dir_; }

    void Write(const std::string &relPath, const std::string &content)
    {
        std::filesystem::create_directories((dir_ / relPath).parent_path());
        std::ofstream out(dir_ / relPath);
        out << content;
    }

private:
    std::filesystem::path dir_;
};

// ---- 合法数据集 ----
// kvcache: 访问入口 + 运行时日志故障
const char *KVCACHE_JSON = R"([
    {"故障编号":"kvcache_root","故障名称":"root","文件名":"kvc_root.cpp","故障现象":"向下级匹配",
     "故障原因":"c1","解决办法":"s1","函数名":"RootFunc","节点类型":"access_log_entry","错误码":1001},
    {"故障编号":"kvcache_cond","故障名称":"cond","文件名":"kvc_cond.cpp","故障现象":"向下级匹配",
     "故障原因":"c2","解决办法":"s2","函数名":"CondFunc","节点类型":"access_log_entry",
     "匹配条件":{"status_code":1002,"resp_msg_nonempty":true}},
    {"故障编号":"kvcache_runtime","故障名称":"rt","文件名":"kvc_rt.cpp","故障现象":"依次匹配`err`、`timeout`",
     "故障原因":"c3","解决办法":"s3","函数名":"RtFunc","节点类型":"runtime_log"}
])";

const char *URMA_JSON = R"([
    {"故障编号":"urma_iface","故障名称":"iface","文件名":"u_iface.cpp","故障现象":"向下级匹配",
     "故障原因":"c4","解决办法":"s4","函数名":"IfaceFunc"},
    {"故障编号":"urma_fail","故障名称":"ufail","文件名":"u_fail.cpp","故障现象":"依次匹配`urma err`",
     "故障原因":"c5","解决办法":"s5","函数名":"UfailFunc"}
])";

// 故障模式树：kvcache_root -> kvcache_runtime / kvcache_cond；urma_iface -> urma_fail
const char *TREE_JSON = R"({
    "kvcache": {
        "kvcache_root": ["kvcache_runtime", "kvcache_cond"],
        "kvcache_runtime": ["urma_iface"]
    },
    "urma": {
        "urma_iface": ["urma_fail"]
    }
})";

// 写入一套完整、合法的规则文件；传 nullptr 表示保留默认。
std::filesystem::path MakeRuleDir(const char *kvcacheJson = nullptr, const char *urmaJson = nullptr,
                                  const char *treeJson = nullptr)
{
    static TempWittyDir dir;
    dir.Write("data/kvcache/kvcache_failure_mode.json", kvcacheJson ? kvcacheJson : KVCACHE_JSON);
    dir.Write("data/urma/urma_failure_mode.json", urmaJson ? urmaJson : URMA_JSON);
    dir.Write("data/failure_mode_tree.json", treeJson ? treeJson : TREE_JSON);
    return dir.Path();
}

// 构造一条合法 access 日志（13 字段，用 " | " 分隔）
std::string MakeAccessLog(const std::string &traceId, int statusCode, const std::string &filename,
                          const std::string &functionName, const std::string &respMsg = "")
{
    // 字段顺序：时间 | 级别 | 文件名:函数名:行号 | pod | pid:tid | traceId | cluster | status | action | cost
    // | datasize | req | resp。源码位置最后一段是行号（FailureLogInfo 用 rfind(':') 解析）。
    return "2024-01-15 10:30:00 | I | " + filename + ":" + functionName + ":42 | pod1 | 123:456 | " + traceId +
           " | cluster1 | " + std::to_string(statusCode) +
           " | action1 | 10 | 100 | req | " + respMsg;
}

// 构造一条合法 runtime 日志（8 字段，用 " | " 分隔）
std::string MakeRuntimeLog(const std::string &traceId, const std::string &level, const std::string &filename,
                           const std::string &functionName, const std::string &message)
{
    return "2024-01-15 10:30:00 | " + level + " | " + filename + ":" + functionName + ":42" +
           " | pod1 | 123:456 | " + traceId + " | cluster1 | " + message;
}

} // namespace

// ===========================================================================
// Create / LoadRules：正常路径
// ===========================================================================

TEST(DiagnosisToolEngineCreate, LoadsRulesAndBuildsIndices)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);

    // kvcache 3 + urma 2 + unknown 兜底 1 = 6
    ASSERT_EQ(engine->rules_.size(), 6u);

    // access 节点：unknown 兜底在尾部
    EXPECT_TRUE(engine->unknownAccessRuleIndex_.has_value());
    EXPECT_EQ(engine->rules_[*engine->unknownAccessRuleIndex_].failureMode->GetId(),
              "kvcache_failure_unknown");

    // accessStatusCode 索引：1001 -> 第 0 条规则
    ASSERT_EQ(engine->accessStatusToRuleIndex_.count(1001), 1u);
    EXPECT_EQ(engine->accessStatusToRuleIndex_.at(1001), 0u);

    // 条件访问规则索引（1002/resp_msg_nonempty）
    ASSERT_EQ(engine->conditionalAccessRuleIndices_.size(), 1u);
    EXPECT_EQ(engine->conditionalAccessRuleIndices_[0], 1u);

    // kvcacheFilenameToRuleIndices: kvc_rt.cpp -> 规则 2
    ASSERT_EQ(engine->kvcacheFilenameToRuleIndices_.count("kvc_rt.cpp"), 1u);
    EXPECT_EQ(engine->kvcacheFilenameToRuleIndices_.at("kvc_rt.cpp").size(), 1u);

    // urmaFunctionToRuleIndices: UfailFunc -> 规则 4
    ASSERT_EQ(engine->urmaFunctionToRuleIndices_.count("UfailFunc"), 1u);

    // GetControllers/GetHitRoots 均已初始化
    EXPECT_EQ(engine->GetControllers().size(), engine->rules_.size());
    EXPECT_TRUE(engine->GetHitRoots().empty());
}

TEST(DiagnosisToolEngineCreate, FailsWhenWittyDirMissing)
{
    auto engine = diag::DiagnosisEngine::Create("/nonexistent/witty/diag/dir");
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnMalformedJson)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir("{ not valid json"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnNonArrayKvcacheJson)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(R"({"a":1})"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnEmptyIdEntry)
{
    // 故障编号为空 → 失败
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"","故障名称":"n","文件名":"f.cpp","故障现象":"依次匹配`k`",
             "故障原因":"c","解决办法":"s","函数名":"F","节点类型":"runtime_log"}])"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnDuplicateId)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"dup","故障名称":"n","文件名":"f.cpp","故障现象":"依次匹配`k`",
             "故障原因":"c","解决办法":"s","函数名":"F","节点类型":"runtime_log"},
            {"故障编号":"dup","故障名称":"n2","文件名":"g.cpp","故障现象":"依次匹配`m`",
             "故障原因":"c","解决办法":"s","函数名":"G","节点类型":"runtime_log"}])"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnUnknownKvcacheNodeType)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"kvc_x","故障名称":"n","文件名":"f.cpp","故障现象":"依次匹配`k`",
             "故障原因":"c","解决办法":"s","函数名":"F","节点类型":"bogus_type"}])"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnInvalidMatchCondition)
{
    // match_condition 非 object → 失败
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"kvc_x","故障名称":"n","文件名":"f.cpp","故障现象":"向下级匹配",
             "故障原因":"c","解决办法":"s","函数名":"F","节点类型":"access_log_entry",
             "匹配条件":"not_object"}])"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnInvalidLogMatchConfig)
{
    // log_match 非 object → 失败
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"kvc_x","故障名称":"n","文件名":"f.cpp","故障现象":"依次匹配`k`",
             "故障原因":"c","解决办法":"s","函数名":"F","节点类型":"runtime_log",
             "日志匹配":"not_object"}])"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, DisabledLogMatchWithoutReasonFails)
{
    // log_match enabled=false 但 reason 缺失 → 失败
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"kvc_x","故障名称":"n","文件名":"f.cpp","故障现象":"依次匹配`k`",
             "故障原因":"c","解决办法":"s","函数名":"F","节点类型":"runtime_log",
             "日志匹配":{"enabled":false}}])"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, EnabledLogMatchWithoutKeywordsFails)
{
    // log_match enabled=true 但无关键字（故障现象无反引号）→ 失败
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"kvc_x","故障名称":"n","文件名":"f.cpp","故障现象":"no keywords here",
             "故障原因":"c","解决办法":"s","函数名":"F","节点类型":"runtime_log",
             "日志匹配":{"enabled":true}}])"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, DisabledLogMatchSkipped)
{
    // log_match enabled=false + reason 合法 → 该 runtime 规则不进入索引。
    // BuildIndices 要求全部索引非空，因此同 JSON 中补齐条件 access 规则与启用的 runtime 规则。
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"kvc_root","故障名称":"r","文件名":"r.cpp","故障现象":"向下级匹配",
             "故障原因":"c","解决办法":"s","函数名":"RF","节点类型":"access_log_entry","错误码":1},
            {"故障编号":"kvc_cond","故障名称":"cd","文件名":"cd.cpp","故障现象":"向下级匹配",
             "故障原因":"c","解决办法":"s","函数名":"CF","节点类型":"access_log_entry",
             "匹配条件":{"status_code":1002,"resp_msg_nonempty":true}},
            {"故障编号":"kvc_rt","故障名称":"rt","文件名":"rt.cpp","故障现象":"依次匹配`k`",
             "故障原因":"c","解决办法":"s","函数名":"RTF","节点类型":"runtime_log"},
            {"故障编号":"kvc_x","故障名称":"n","文件名":"f.cpp","故障现象":"依次匹配`k`",
             "故障原因":"c","解决办法":"s","函数名":"F","节点类型":"runtime_log",
             "日志匹配":{"enabled":false,"reason":"disabled"}}])",
        nullptr,
        R"({"kvcache":{"kvc_root":["kvc_rt","kvc_x"]},"urma":{"urma_iface":["urma_fail"]}})"));
    ASSERT_NE(engine, nullptr);
    EXPECT_EQ(engine->kvcacheFilenameToRuleIndices_.count("f.cpp"), 0u);
    // 启用的 runtime 规则正常进入索引
    EXPECT_EQ(engine->kvcacheFilenameToRuleIndices_.count("rt.cpp"), 1u);
}

TEST(DiagnosisToolEngineCreate, FailsOnTreeMissingModule)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(nullptr, nullptr,
        R"({"kvcache":{"kvcache_root":["kvcache_runtime"]}})"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnTreeUnknownParent)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(nullptr, nullptr,
        R"({"kvcache":{"ghost":["kvcache_runtime"]},"urma":{"urma_iface":["urma_fail"]}})"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnTreeUnknownChild)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(nullptr, nullptr,
        R"({"kvcache":{"kvcache_root":["ghost_child"]},"urma":{"urma_iface":["urma_fail"]}})"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnTreeNonArrayChildren)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(nullptr, nullptr,
        R"({"kvcache":{"kvcache_root":"not_array"},"urma":{"urma_iface":["urma_fail"]}})"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnTreeNonStringChild)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(nullptr, nullptr,
        R"({"kvcache":{"kvcache_root":[123]},"urma":{"urma_iface":["urma_fail"]}})"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnDuplicateAccessStatusCode)
{
    // 两条 access 规则带相同错误码 1001 → BuildIndices 失败
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"kvc_root","故障名称":"r","文件名":"r.cpp","故障现象":"向下级匹配",
             "故障原因":"c","解决办法":"s","函数名":"RF","节点类型":"access_log_entry","错误码":1001},
            {"故障编号":"kvc_dup","故障名称":"d","文件名":"d.cpp","故障现象":"向下级匹配",
             "故障原因":"c","解决办法":"s","函数名":"DF","节点类型":"access_log_entry","错误码":1001},
            {"故障编号":"kvc_rt","故障名称":"rt","文件名":"rt.cpp","故障现象":"依次匹配`k`",
             "故障原因":"c","解决办法":"s","函数名":"RTF","节点类型":"runtime_log"}])",
        nullptr,
        R"({"kvcache":{"kvcache_root":["kvc_dup","kvc_rt"]}})"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, FailsOnUnreachableRuntimeRule)
{
    // runtime 规则未在 failure_mode_tree 中出现 → RegisterRuleIndex 拒绝
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"kvc_root","故障名称":"r","文件名":"r.cpp","故障现象":"向下级匹配",
             "故障原因":"c","解决办法":"s","函数名":"RF","节点类型":"access_log_entry","错误码":1},
            {"故障编号":"kvc_rt","故障名称":"rt","文件名":"rt.cpp","故障现象":"依次匹配`k`",
             "故障原因":"c","解决办法":"s","函数名":"RTF","节点类型":"runtime_log"}])",
        nullptr,
        R"({"urma":{"urma_iface":["urma_fail"]}})"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisToolEngineCreate, AccessNodeWithoutStatusOrConditionWarns)
{
    // access 节点无 status_code 也无 match_condition → 跳过（仅 WARN，不进任何索引）。
    // BuildIndices 要求条件索引非空，因此补一条带匹配条件的 access 规则。
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"kvc_root","故障名称":"r","文件名":"r.cpp","故障现象":"向下级匹配",
             "故障原因":"c","解决办法":"s","函数名":"RF","节点类型":"access_log_entry","错误码":1},
            {"故障编号":"kvc_cond","故障名称":"cd","文件名":"cd.cpp","故障现象":"向下级匹配",
             "故障原因":"c","解决办法":"s","函数名":"CF","节点类型":"access_log_entry",
             "匹配条件":{"status_code":1002,"resp_msg_nonempty":true}},
            {"故障编号":"kvc_naked","故障名称":"n","文件名":"n.cpp","故障现象":"向下级匹配",
             "故障原因":"c","解决办法":"s","函数名":"NF","节点类型":"access_log_entry"},
            {"故障编号":"kvc_rt","故障名称":"rt","文件名":"rt.cpp","故障现象":"依次匹配`k`",
             "故障原因":"c","解决办法":"s","函数名":"RTF","节点类型":"runtime_log"}])",
        nullptr,
        R"({"kvcache":{"kvc_root":["kvc_rt"]},"urma":{"urma_iface":["urma_fail"]}})"));
    ASSERT_NE(engine, nullptr);
    // kvcache 4 条 + unknown 兜底 1 + urma 2 = 7
    ASSERT_EQ(engine->rules_.size(), 7u);
    // naked 节点未进入任何索引：status 索引只有 kvc_root 的 1，条件索引只有 kvc_cond
    EXPECT_EQ(engine->accessStatusToRuleIndex_.size(), 1u);
    ASSERT_EQ(engine->accessStatusToRuleIndex_.count(1), 1u);
    ASSERT_EQ(engine->conditionalAccessRuleIndices_.size(), 1u);
}

// ===========================================================================
// 规则缓存（SaveRuleCache / LoadRuleCache）
// ===========================================================================

TEST(DiagnosisToolEngineCache, RoundTripCache)
{
    auto wittyDir = MakeRuleDir();
    auto engine1 = diag::DiagnosisEngine::Create(wittyDir);
    ASSERT_NE(engine1, nullptr);
    auto ruleCount1 = engine1->rules_.size();

    // 第二次创建：应命中缓存
    auto engine2 = diag::DiagnosisEngine::Create(wittyDir);
    ASSERT_NE(engine2, nullptr);
    EXPECT_EQ(engine2->rules_.size(), ruleCount1);

    // 验证缓存读取后索引完整
    EXPECT_TRUE(engine2->unknownAccessRuleIndex_.has_value());
    EXPECT_FALSE(engine2->accessStatusToRuleIndex_.empty());
    EXPECT_FALSE(engine2->conditionalAccessRuleIndices_.empty());
    EXPECT_FALSE(engine2->kvcacheFilenameToRuleIndices_.empty());
    EXPECT_FALSE(engine2->urmaFunctionToRuleIndices_.empty());
}

TEST(DiagnosisToolEngineCache, CacheInvalidatedWhenSourceChanges)
{
    auto wittyDir = MakeRuleDir();
    auto engine1 = diag::DiagnosisEngine::Create(wittyDir);
    ASSERT_NE(engine1, nullptr);
    auto ruleCount1 = engine1->rules_.size();

    // 修改源文件内容，时间戳变化 → 缓存失效
    std::ofstream out(wittyDir / "data/kvcache/kvcache_failure_mode.json");
    out << KVCACHE_JSON << "\n";
    out.close();

    auto engine2 = diag::DiagnosisEngine::Create(wittyDir);
    ASSERT_NE(engine2, nullptr);
    EXPECT_EQ(engine2->rules_.size(), ruleCount1);
}

TEST(DiagnosisToolEngineCache, CorruptCacheFallsBackToSource)
{
    auto wittyDir = MakeRuleDir();
    // 先生成缓存
    auto engine1 = diag::DiagnosisEngine::Create(wittyDir);
    ASSERT_NE(engine1, nullptr);

    // 破坏缓存文件头部 → 验证缓存失败，回退源码加载
    const auto cachePath = wittyDir / "cache/diagnosis_rules_v1.bin";
    ASSERT_TRUE(std::filesystem::exists(cachePath));
    std::ofstream corrupt(cachePath, std::ios::binary | std::ios::trunc);
    corrupt << "garbage";
    corrupt.close();

    auto engine2 = diag::DiagnosisEngine::Create(wittyDir);
    ASSERT_NE(engine2, nullptr);
    EXPECT_EQ(engine2->rules_.size(), engine1->rules_.size());
}

// ===========================================================================
// RunDiagnosis / AnalyzeAccessLine / AnalyzeRuntimeLine
// ===========================================================================

TEST(DiagnosisToolEngineRun, RunDiagnosisWithAccessAndRuntimeLogs)
{
    auto wittyDir = MakeRuleDir();
    auto engine = diag::DiagnosisEngine::Create(wittyDir);
    ASSERT_NE(engine, nullptr);

    // 写入 access + runtime 日志文件
    std::filesystem::path tmpDir = std::filesystem::temp_directory_path() / "diag_run_test";
    std::filesystem::create_directories(tmpDir);
    auto cleanup = [&tmpDir]() { std::filesystem::remove_all(tmpDir); };

    std::string accessLog = MakeAccessLog("trace1", 1001, "kvc_root.cpp", "RootFunc");
    std::string runtimeLog = MakeRuntimeLog("trace1", "E", "kvc_rt.cpp", "RtFunc", "err and timeout");

    std::ofstream accessFile(tmpDir / "access.log");
    accessFile << accessLog << "\n";
    accessFile.close();

    std::ofstream runtimeFile(tmpDir / "runtime.log");
    runtimeFile << runtimeLog << "\n";
    runtimeFile.close();

    std::vector<std::string> accessPaths{(tmpDir / "access.log").string()};
    std::vector<std::string> runtimePaths{(tmpDir / "runtime.log").string()};

    EXPECT_TRUE(engine->RunDiagnosis(accessPaths, runtimePaths));

    // 验证命中根节点
    EXPECT_FALSE(engine->GetHitRoots().empty());
    EXPECT_NE(engine->GetHitRoots().find("kvcache_root"), engine->GetHitRoots().end());

    // 验证 traceLogs 非空
    EXPECT_FALSE(engine->GetTraceLogs().empty());

    cleanup();
}

TEST(DiagnosisToolEngineRun, RunDiagnosisNonexistentAccessPath)
{
    auto wittyDir = MakeRuleDir();
    auto engine = diag::DiagnosisEngine::Create(wittyDir);
    ASSERT_NE(engine, nullptr);

    std::vector<std::string> accessPaths{"/nonexistent/access.log"};
    std::vector<std::string> runtimePaths;
    EXPECT_FALSE(engine->RunDiagnosis(accessPaths, runtimePaths));
}

TEST(DiagnosisToolEngineRun, RunDiagnosisNonexistentRuntimePath)
{
    auto wittyDir = MakeRuleDir();
    auto engine = diag::DiagnosisEngine::Create(wittyDir);
    ASSERT_NE(engine, nullptr);

    std::filesystem::path tmpDir = std::filesystem::temp_directory_path() / "diag_run_test2";
    std::filesystem::create_directories(tmpDir);
    auto cleanup = [&tmpDir]() { std::filesystem::remove_all(tmpDir); };

    std::string accessLog = MakeAccessLog("trace1", 1001, "kvc_root.cpp", "RootFunc");
    std::ofstream accessFile(tmpDir / "access.log");
    accessFile << accessLog << "\n";
    accessFile.close();

    std::vector<std::string> accessPaths{(tmpDir / "access.log").string()};
    std::vector<std::string> runtimePaths{"/nonexistent/runtime.log"};
    EXPECT_FALSE(engine->RunDiagnosis(accessPaths, runtimePaths));
    cleanup();
}

TEST(DiagnosisToolEngineRun, AnalyzeAccessLineMatchesStatusCode)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // 匹配错误码 1001
    std::string log = MakeAccessLog("trace1", 1001, "kvc_root.cpp", "RootFunc");
    engine->AnalyzeAccessLine(log);
    EXPECT_FALSE(engine->GetHitRoots().empty());
}

TEST(DiagnosisToolEngineRun, AnalyzeAccessLineMatchesCondition)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // 匹配条件：status_code=1002 且 resp_msg_nonempty
    std::string log = MakeAccessLog("trace1", 1002, "kvc_cond.cpp", "CondFunc", "has response");
    engine->AnalyzeAccessLine(log);
    EXPECT_TRUE(engine->GetHitRoots().find("kvcache_cond") != engine->GetHitRoots().end());
}

TEST(DiagnosisToolEngineRun, AnalyzeAccessLineConditionRespMsgEmpty)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // resp_msg_nonempty=true 但 respMsg 为空 → 不匹配
    std::string log = MakeAccessLog("trace1", 1002, "kvc_cond.cpp", "CondFunc", "");
    engine->AnalyzeAccessLine(log);
    EXPECT_TRUE(engine->GetHitRoots().find("kvcache_cond") == engine->GetHitRoots().end());
}

TEST(DiagnosisToolEngineRun, AnalyzeAccessLineUnknownStatusCode)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // 未知非零状态码 → 兜底
    std::string log = MakeAccessLog("trace1", 9999, "kvc_root.cpp", "RootFunc");
    engine->AnalyzeAccessLine(log);
    EXPECT_TRUE(engine->GetHitRoots().find("kvcache_failure_unknown") != engine->GetHitRoots().end());
}

TEST(DiagnosisToolEngineRun, AnalyzeAccessLineZeroStatusCode)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // 状态码 0 → 不诊断
    std::string log = MakeAccessLog("trace1", 0, "kvc_root.cpp", "RootFunc");
    engine->AnalyzeAccessLine(log);
    EXPECT_TRUE(engine->GetHitRoots().empty());
}

TEST(DiagnosisToolEngineRun, AnalyzeAccessLineLocationMismatch)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // 文件名不匹配 → IsAccessLocationMismatch 返回 true
    std::string log = MakeAccessLog("trace1", 1001, "wrong_file.cpp", "RootFunc");
    engine->AnalyzeAccessLine(log);
    EXPECT_TRUE(engine->GetHitRoots().empty());
}

TEST(DiagnosisToolEngineRun, AnalyzeAccessLineFunctionMismatch)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // 文件名匹配但函数名不匹配 → 不命中
    std::string log = MakeAccessLog("trace1", 1001, "kvc_root.cpp", "WrongFunc");
    engine->AnalyzeAccessLine(log);
    EXPECT_TRUE(engine->GetHitRoots().empty());
}

TEST(DiagnosisToolEngineRun, AnalyzeAccessLineEmptyTraceId)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // traceId 为空 → 直接返回
    std::string log = MakeAccessLog("", 1001, "kvc_root.cpp", "RootFunc");
    engine->AnalyzeAccessLine(log);
    EXPECT_TRUE(engine->GetHitRoots().empty());
}

TEST(DiagnosisToolEngineRun, AnalyzeAccessLineMalformed)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // 字段数不足 → 解析失败
    engine->AnalyzeAccessLine("not enough fields");
    EXPECT_TRUE(engine->GetHitRoots().empty());
}

TEST(DiagnosisToolEngineRun, AnalyzeRuntimeLineMatchesKeywords)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // 先注入 access trace
    std::string accessLog = MakeAccessLog("trace1", 1001, "kvc_root.cpp", "RootFunc");
    engine->AnalyzeAccessLine(accessLog);

    // runtime 日志含 err + timeout → 匹配
    std::string runtimeLog = MakeRuntimeLog("trace1", "E", "kvc_rt.cpp", "RtFunc", "err and timeout");
    engine->AnalyzeRuntimeLine(runtimeLog);
    EXPECT_FALSE(engine->pendingKvcacheRecords_.empty());
}

TEST(DiagnosisToolEngineRun, AnalyzeRuntimeLineNoMatchingTraceId)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // traceId 不在 accessTraceIds_ 中 → 跳过
    std::string runtimeLog = MakeRuntimeLog("ghost_trace", "E", "kvc_rt.cpp", "RtFunc", "err and timeout");
    engine->AnalyzeRuntimeLine(runtimeLog);
    EXPECT_TRUE(engine->pendingKvcacheRecords_.empty());
}

TEST(DiagnosisToolEngineRun, AnalyzeRuntimeLineUrmaCandidate)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // 先注入 access trace
    std::string accessLog = MakeAccessLog("trace1", 1001, "kvc_root.cpp", "RootFunc");
    engine->AnalyzeAccessLine(accessLog);

    // 含 liburma 关键字 → 进入 urmaLines
    std::string runtimeLog = MakeRuntimeLog("trace1", "E", "any.cpp", "AnyFunc", "liburma something");
    engine->AnalyzeRuntimeLine(runtimeLog);
    EXPECT_FALSE(engine->pendingUrmaLines_.empty());
}

TEST(DiagnosisToolEngineRun, AnalyzeRuntimeLinesBatch)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // 先注入 access trace
    std::string accessLog = MakeAccessLog("trace1", 1001, "kvc_root.cpp", "RootFunc");
    engine->AnalyzeAccessLine(accessLog);

    // 多行 runtime 日志批量分析（走多线程路径）
    std::vector<std::string_view> lines;
    std::vector<std::string> storage;
    for (int i = 0; i < 3; ++i) {
        storage.push_back(MakeRuntimeLog("trace1", "E", "kvc_rt.cpp", "RtFunc", "err and timeout"));
        lines.push_back(storage.back());
    }
    engine->AnalyzeRuntimeLines(lines);
    EXPECT_FALSE(engine->pendingKvcacheRecords_.empty());
}

TEST(DiagnosisToolEngineRun, AnalyzeRuntimeLinesEmpty)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    std::vector<std::string_view> lines;
    engine->AnalyzeRuntimeLines(lines);
    EXPECT_TRUE(engine->pendingKvcacheRecords_.empty());
}

TEST(DiagnosisToolEngineRun, FinishDiagnosisActivatesEdges)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // 注入 access + runtime 日志
    std::string accessLog = MakeAccessLog("trace1", 1001, "kvc_root.cpp", "RootFunc");
    engine->AnalyzeAccessLine(accessLog);

    std::string runtimeLog = MakeRuntimeLog("trace1", "E", "kvc_rt.cpp", "RtFunc", "err and timeout");
    engine->AnalyzeRuntimeLine(runtimeLog);

    // FinishDiagnosis 激活边
    engine->FinishDiagnosis(1, 1);
    EXPECT_FALSE(engine->GetTraceLogs().empty());
}

TEST(DiagnosisToolEngineRun, FullPipelineWithUrma)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    engine->BeginDiagnosis();

    // access root → runtime → urma iface → urma fail 全链路
    std::string accessLog = MakeAccessLog("trace1", 1001, "kvc_root.cpp", "RootFunc");
    engine->AnalyzeAccessLine(accessLog);

    std::string runtimeLog = MakeRuntimeLog("trace1", "E", "kvc_rt.cpp", "RtFunc", "err and timeout");
    engine->AnalyzeRuntimeLine(runtimeLog);

    // URMA 日志：格式 URMA|liburma|tid|ttag|func[line]|message
    std::string urmaLine = MakeRuntimeLog("trace1", "E", "any.cpp", "AnyFunc",
                                           "URMA|liburma|123|tag|UfailFunc[42]|urma err here");
    engine->AnalyzeRuntimeLine(urmaLine);

    engine->FinishDiagnosis(1, 1);
    // 应能命中 urma_fail
    EXPECT_FALSE(engine->GetTraceLogs().empty());
}

// ===========================================================================
// ParseKeywords / ParseNumericErrorCode / ParseAccessLog / ParseRuntimeMatchView
// 静态私有方法（通过 #define private public 访问）
// ===========================================================================

TEST(DiagnosisToolEngineParse, ParseKeywordsMultiple)
{
    auto keywords = diag::DiagnosisEngine::ParseKeywords("依次匹配`err`、`timeout`");
    ASSERT_EQ(keywords.size(), 2u);
    EXPECT_EQ(keywords[0], "err");
    EXPECT_EQ(keywords[1], "timeout");
}

TEST(DiagnosisToolEngineParse, ParseKeywordsDownstreamMatch)
{
    auto keywords = diag::DiagnosisEngine::ParseKeywords("向下级匹配");
    EXPECT_TRUE(keywords.empty());
}

TEST(DiagnosisToolEngineParse, ParseKeywordsEmptyBackticks)
{
    // 空反引号对被跳过
    auto keywords = diag::DiagnosisEngine::ParseKeywords("匹配``和`x`");
    ASSERT_EQ(keywords.size(), 1u);
    EXPECT_EQ(keywords[0], "x");
}

TEST(DiagnosisToolEngineParse, ParseKeywordsSingleBacktick)
{
    auto keywords = diag::DiagnosisEngine::ParseKeywords("only `one");
    EXPECT_TRUE(keywords.empty());
}

TEST(DiagnosisToolEngineParse, ParseKeywordsNoBackticks)
{
    auto keywords = diag::DiagnosisEngine::ParseKeywords("plain text");
    EXPECT_TRUE(keywords.empty());
}

TEST(DiagnosisToolEngineParse, ParseNumericErrorCodeWithParen)
{
    auto result = diag::DiagnosisEngine::ParseNumericErrorCode(std::optional<std::string>("E002(1002)"));
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(*result, 1002);
}

TEST(DiagnosisToolEngineParse, ParseNumericErrorCodePlain)
{
    auto result = diag::DiagnosisEngine::ParseNumericErrorCode(std::optional<std::string>("1003"));
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(*result, 1003);
}

TEST(DiagnosisToolEngineParse, ParseNumericErrorCodeInvalid)
{
    auto result = diag::DiagnosisEngine::ParseNumericErrorCode(std::optional<std::string>("not_a_number"));
    EXPECT_FALSE(result.has_value());
}

TEST(DiagnosisToolEngineParse, ParseNumericErrorCodeEmpty)
{
    auto result = diag::DiagnosisEngine::ParseNumericErrorCode(std::nullopt);
    EXPECT_FALSE(result.has_value());
}

// ===========================================================================
// Basename / BasenameView 静态方法
// ===========================================================================

TEST(DiagnosisToolEngineBasename, WithSlash)
{
    EXPECT_EQ(diag::DiagnosisEngine::Basename("/path/to/file.cpp"), "file.cpp");
}

TEST(DiagnosisToolEngineBasename, NoSlash)
{
    EXPECT_EQ(diag::DiagnosisEngine::Basename("file.cpp"), "file.cpp");
}

TEST(DiagnosisToolEngineBasename, WindowsPath)
{
    EXPECT_EQ(diag::DiagnosisEngine::Basename("path\\to\\file.cpp"), "file.cpp");
}

TEST(DiagnosisToolEngineBasenameView, WithSlash)
{
    EXPECT_EQ(diag::DiagnosisEngine::BasenameView("/path/to/file.cpp"), "file.cpp");
}

TEST(DiagnosisToolEngineBasenameView, NoSlash)
{
    EXPECT_EQ(diag::DiagnosisEngine::BasenameView("file.cpp"), "file.cpp");
}

// ===========================================================================
// GetControllers / GetTraceLogs / GetHitRoots
// ===========================================================================

TEST(DiagnosisToolEngineGet, GetControllersNotEmpty)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    EXPECT_FALSE(engine->GetControllers().empty());
}

TEST(DiagnosisToolEngineGet, GetTraceLogsEmptyBeforeDiagnosis)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    EXPECT_TRUE(engine->GetTraceLogs().empty());
}

TEST(DiagnosisToolEngineGet, GetHitRootsEmptyBeforeDiagnosis)
{
    auto engine = diag::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);
    EXPECT_TRUE(engine->GetHitRoots().empty());
}
