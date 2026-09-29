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

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

// Access private members for testing
#define private public
#include "diagnosis_engine.h"
#undef private

#include "diagnosis_model.h"
#include "logger.h"
#include "temp_witty_dir.h"

namespace {

// 诊断引擎加载规则时会打日志，log4cplus 必须先初始化，否则崩溃。
struct LoggerInit {
    LoggerInit() noexcept { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// 每个用例独立的临时 witty 目录，析构时清理（公共实现见 temp_witty_dir.h）。
// 预建 data/ubsocket、data/umq、data/urma 业务子目录。
constexpr const char *WITTY_DIR_PREFIX = "witty_diag_test";
constexpr const char *DATA_SUBDIRS[] = {"ubsocket", "umq", "urma"};

const char *UBSOCKET_JSON = R"([
    {"故障编号":"ubsocket_root", "故障名称":"root mode", "文件名":"root.cpp", "故障现象":"向下级匹配",
     "故障原因":"c1", "解决办法":"s1", "函数名":"RootFunc", "错误码":1001},
    {"故障编号":"ubsocket_err", "故障名称":"err mode", "文件名":"err.cpp", "故障现象":"依次匹配`error`、`timeout`",
     "故障原因":"c2", "解决办法":"s2", "函数名":"ErrFunc", "错误码":"E002"}
])";

const char *UMQ_JSON = R"([
    {"故障编号":"umq_err", "故障名称":"umq err", "文件名":"umq.cpp", "故障现象":"依次匹配`umq fail`",
     "故障原因":"c3", "解决办法":"s3", "函数名":"UmqFunc"}
])";

const char *URMA_JSON = R"([
    {"故障编号":"urma_err", "故障名称":"urma err", "文件名":"urma.cpp", "故障现象":"依次匹配`urma fail`",
     "故障原因":"c4", "解决办法":"s4", "函数名":"UrmaFunc"}
])";

const char *TREE_JSON = R"({
    "ubsocket": {"ubsocket_root": ["ubsocket_err", "umq_err"]}
})";

// 写入一套完整、合法的规则文件；传 nullptr 表示该文件保留默认内容。
std::filesystem::path MakeRuleDir(const char *ubsocketJson = nullptr, const char *umqJson = nullptr,
                                  const char *urmaJson = nullptr, const char *treeJson = nullptr)
{
    static TempWittyDir dir(WITTY_DIR_PREFIX, std::vector<std::string>(DATA_SUBDIRS, DATA_SUBDIRS + 3));
    dir.Write("data/ubsocket/ubsocket_failure_mode.json", ubsocketJson ? ubsocketJson : UBSOCKET_JSON);
    dir.Write("data/umq/umq_failure_mode.json", umqJson ? umqJson : UMQ_JSON);
    dir.Write("data/urma/urma_failure_mode.json", urmaJson ? urmaJson : URMA_JSON);
    dir.Write("data/failure_mode_tree.json", treeJson ? treeJson : TREE_JSON);
    return dir.Path();
}

} // namespace

TEST(ParseKeywords, ExtractsBacktickContent) {
    std::string phenomenon = "依次匹配`error1`、`error2`";
    auto keywords = brpc::DiagnosisEngine::ParseKeywords(phenomenon);
    ASSERT_EQ(keywords.size(), 2u);
    EXPECT_EQ(keywords[0], "error1");
    EXPECT_EQ(keywords[1], "error2");
}

TEST(ParseKeywords, ReturnsEmptyForDownMatch) {
    std::string phenomenon = "向下级匹配";
    auto keywords = brpc::DiagnosisEngine::ParseKeywords(phenomenon);
    EXPECT_TRUE(keywords.empty());
}

TEST(ParseKeywords, NoBackticks) {
    std::string phenomenon = "some text without keywords";
    auto keywords = brpc::DiagnosisEngine::ParseKeywords(phenomenon);
    EXPECT_TRUE(keywords.empty());
}

TEST(ParseKeywords, SingleBacktick) {
    std::string phenomenon = "test `only";
    auto keywords = brpc::DiagnosisEngine::ParseKeywords(phenomenon);
    EXPECT_TRUE(keywords.empty());
}

TEST(ParseKeywords, MultipleKeywords) {
    std::string phenomenon = "依次匹配`a`、`b`、`c`、`d`";
    auto keywords = brpc::DiagnosisEngine::ParseKeywords(phenomenon);
    ASSERT_EQ(keywords.size(), 4u);
    EXPECT_EQ(keywords[0], "a");
    EXPECT_EQ(keywords[1], "b");
    EXPECT_EQ(keywords[2], "c");
    EXPECT_EQ(keywords[3], "d");
}

TEST(MatchKeywords, AllPresent) {
    brpc::DiagnosisRule rule;
    rule.keywords = {"error", "code"};
    auto result = brpc::DiagnosisEngine::MatchKeywords(rule, "found error and code here");
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(*result, 9u); // "error" (5) + "code" (4) = 9
}

TEST(MatchKeywords, MissingKeyword) {
    brpc::DiagnosisRule rule;
    rule.keywords = {"error", "missing"};
    auto result = brpc::DiagnosisEngine::MatchKeywords(rule, "found error here");
    EXPECT_FALSE(result.has_value());
}

TEST(MatchKeywords, EmptyKeywords) {
    brpc::DiagnosisRule rule;
    rule.keywords = {};
    auto result = brpc::DiagnosisEngine::MatchKeywords(rule, "any text");
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(*result, 0u);
}

TEST(MatchKeywords, OrderMatters) {
    brpc::DiagnosisRule rule;
    rule.keywords = {"world", "hello"};
    auto result = brpc::DiagnosisEngine::MatchKeywords(rule, "hello world");
    EXPECT_FALSE(result.has_value());
}

TEST(MatchKeywords, OverlappingKeywords) {
    // 顺序匹配语义：offset 只前进不回溯，"ab" 命中后 offset=2，
    // "bc"（位置 1）无法再次命中，整体返回 nullopt。
    brpc::DiagnosisRule rule;
    rule.keywords = {"ab", "bc"};
    auto result = brpc::DiagnosisEngine::MatchKeywords(rule, "abc");
    EXPECT_FALSE(result.has_value());
}

TEST(GetDiagnosisComponent, Prefixes) {
    EXPECT_EQ(brpc::GetDiagnosisComponent("ubsocket_test"), brpc::DiagnosisComponent::UBSOCKET);
    EXPECT_EQ(brpc::GetDiagnosisComponent("umq_test"), brpc::DiagnosisComponent::UMQ);
    EXPECT_EQ(brpc::GetDiagnosisComponent("urma_test"), brpc::DiagnosisComponent::URMA);
    EXPECT_EQ(brpc::GetDiagnosisComponent("unknown_test"), brpc::DiagnosisComponent::UNKNOWN);
}

TEST(IsSupportedCrossComponentEdge, ValidEdges) {
    EXPECT_TRUE(brpc::IsSupportedCrossComponentEdge(brpc::DiagnosisComponent::UBSOCKET, brpc::DiagnosisComponent::UMQ));
    EXPECT_TRUE(brpc::IsSupportedCrossComponentEdge(brpc::DiagnosisComponent::UMQ, brpc::DiagnosisComponent::URMA));
    EXPECT_FALSE(
        brpc::IsSupportedCrossComponentEdge(brpc::DiagnosisComponent::UBSOCKET, brpc::DiagnosisComponent::URMA));
    EXPECT_FALSE(brpc::IsSupportedCrossComponentEdge(brpc::DiagnosisComponent::URMA, brpc::DiagnosisComponent::UMQ));
}

// ---------------------------------------------------------------------------
// 规则加载（Create / LoadRulesFromJson）
// ---------------------------------------------------------------------------

TEST(DiagnosisEngineCreate, LoadsRulesAndBuildsIndices) {
    auto engine = brpc::DiagnosisEngine::Create(MakeRuleDir());
    ASSERT_NE(engine, nullptr);

    // 三个组件文件共 4 条规则
    ASSERT_EQ(engine->rules_.size(), 4u);

    // 根节点：publicApi、无关键字、错误码为整数
    const auto &root = engine->rules_[0];
    EXPECT_EQ(root.failureMode.id, "ubsocket_root");
    EXPECT_TRUE(root.failureMode.publicApi);
    EXPECT_TRUE(root.keywords.empty());
    ASSERT_TRUE(root.failureMode.errorCode.has_value());
    EXPECT_TRUE(std::holds_alternative<std::int64_t>(*root.failureMode.errorCode));
    EXPECT_EQ(std::get<std::int64_t>(*root.failureMode.errorCode), 1001);
    EXPECT_EQ(root.failureMode.component, brpc::DiagnosisComponent::UBSOCKET);

    // 普通节点：非 publicApi、解析出关键字、错误码为字符串
    const auto &err = engine->rules_[1];
    EXPECT_EQ(err.failureMode.id, "ubsocket_err");
    EXPECT_FALSE(err.failureMode.publicApi);
    ASSERT_EQ(err.keywords.size(), 2u);
    EXPECT_EQ(err.keywords[0], "error");
    EXPECT_EQ(err.keywords[1], "timeout");
    ASSERT_TRUE(err.failureMode.errorCode.has_value());
    EXPECT_EQ(std::get<std::string>(*err.failureMode.errorCode), "E002");

    // 树文件：ubsocket_root -> ubsocket_err 为 local 边，-> umq_err 为 cross 边
    ASSERT_EQ(root.localChildIndices.size(), 1u);
    EXPECT_EQ(root.localChildIndices[0], 1u);
    ASSERT_EQ(root.crossChildIndices.size(), 1u);
    EXPECT_EQ(root.crossChildIndices[0], 2u);

    // 索引：非 public 规则按 filename/functionName 进入 brpc 或 urma 索引
    const auto &brpcIndex = engine->brpcfilenameToFunctionNameToRuleIndices_;
    ASSERT_EQ(brpcIndex.at("err.cpp").at("ErrFunc").size(), 1u);
    EXPECT_EQ(brpcIndex.at("err.cpp").at("ErrFunc")[0], 1u);
    ASSERT_EQ(brpcIndex.at("umq.cpp").at("UmqFunc").size(), 1u);
    EXPECT_EQ(brpcIndex.at("umq.cpp").at("UmqFunc")[0], 2u);
    // publicApi 根节点不进入索引
    EXPECT_EQ(brpcIndex.count("root.cpp"), 0u);

    const auto &urmaIndex = engine->urmaFilenameToFunctionNameToRuleIndices_;
    ASSERT_EQ(urmaIndex.at("urma.cpp").at("UrmaFunc").size(), 1u);
    EXPECT_EQ(urmaIndex.at("urma.cpp").at("UrmaFunc")[0], 3u);
}

TEST(DiagnosisEngineCreate, FailsWhenWittyDirMissing) {
    auto engine = brpc::DiagnosisEngine::Create("/nonexistent/witty/diag/dir");
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisEngineCreate, FailsOnMalformedJson) {
    auto engine = brpc::DiagnosisEngine::Create(MakeRuleDir("{ not a valid json"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisEngineCreate, FailsOnNonArrayFailureModeJson) {
    auto engine = brpc::DiagnosisEngine::Create(MakeRuleDir("{\"a\": 1}"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisEngineCreate, FailsOnInvalidEntry) {
    // 函数名为空 → IsValidRule 拒绝
    auto engine = brpc::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"ubsocket_x", "故障名称":"n", "文件名":"f.cpp", "故障现象":"依次匹配`k`",
             "故障原因":"c", "解决办法":"s", "函数名":""}])"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisEngineCreate, FailsOnUnknownComponentPrefix) {
    // id 无已知组件前缀 → component UNKNOWN → IsValidRule 拒绝
    auto engine = brpc::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"foo_x", "故障名称":"n", "文件名":"f.cpp", "故障现象":"依次匹配`k`",
             "故障原因":"c", "解决办法":"s", "函数名":"F"}])"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisEngineCreate, FailsOnDuplicateId) {
    auto engine = brpc::DiagnosisEngine::Create(MakeRuleDir(
        R"([{"故障编号":"ubsocket_a", "故障名称":"n", "文件名":"f.cpp", "故障现象":"依次匹配`k`",
             "故障原因":"c", "解决办法":"s", "函数名":"F"},
            {"故障编号":"ubsocket_a", "故障名称":"n2", "文件名":"g.cpp", "故障现象":"依次匹配`m`",
             "故障原因":"c", "解决办法":"s", "函数名":"G"}])"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisEngineCreate, FailsOnUnknownChildInTree) {
    auto engine = brpc::DiagnosisEngine::Create(MakeRuleDir(nullptr, nullptr, nullptr,
        R"({"m": {"ubsocket_root": ["ubsocket_err", "ghost_id"]}})"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisEngineCreate, FailsOnUnsupportedCrossComponentEdge) {
    // ubsocket -> urma 不在支持列表
    auto engine = brpc::DiagnosisEngine::Create(MakeRuleDir(nullptr, nullptr, nullptr,
        R"({"m": {"ubsocket_root": ["urma_err"]}})"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisEngineCreate, FailsOnNonStringChildId) {
    auto engine = brpc::DiagnosisEngine::Create(MakeRuleDir(nullptr, nullptr, nullptr,
        R"({"m": {"ubsocket_root": [123]}})"));
    EXPECT_EQ(engine, nullptr);
}

TEST(DiagnosisEngineCreate, TreeSkipsInvalidNodes) {
    // 模块非 object / children 非 array / 父节点不在规则中 → 各分支 continue，仅保留合法边
    auto engine = brpc::DiagnosisEngine::Create(MakeRuleDir(nullptr, nullptr, nullptr,
        R"({
            "scalarModule": "not an object",
            "mod1": {"ubsocket_err": "children not array"},
            "mod2": {"ghost_parent": ["ubsocket_err"]},
            "ubsocket": {"ubsocket_root": ["ubsocket_err"]}
        })"));
    ASSERT_NE(engine, nullptr);
    ASSERT_EQ(engine->rules_.size(), 4u);
    const auto &root = engine->rules_[0];
    ASSERT_EQ(root.localChildIndices.size(), 1u);
    EXPECT_EQ(root.localChildIndices[0], 1u);
    EXPECT_TRUE(root.crossChildIndices.empty());
}

// ---------------------------------------------------------------------------
// 日志处理（ProcessLog / SelectBestHit）
// ---------------------------------------------------------------------------

namespace {

// 构造带两条规则（brpc + urma）并已建好索引的引擎，便于直接驱动私有方法。
brpc::DiagnosisEngine MakeEngineWithRules()
{
    brpc::DiagnosisEngine engine;
    brpc::DiagnosisRule brpcRule;
    brpcRule.failureMode.id = "ubsocket_a";
    brpcRule.failureMode.filename = "a.cpp";
    brpcRule.failureMode.functionName = "FuncA";
    brpcRule.failureMode.component = brpc::DiagnosisComponent::UBSOCKET;
    brpcRule.keywords = {"error"};
    engine.rules_.push_back(brpcRule);

    brpc::DiagnosisRule urmaRule;
    urmaRule.failureMode.id = "urma_u";
    urmaRule.failureMode.filename = "u.cpp";
    urmaRule.failureMode.functionName = "FuncU";
    urmaRule.failureMode.component = brpc::DiagnosisComponent::URMA;
    urmaRule.keywords = {"urma fail"};
    engine.rules_.push_back(urmaRule);

    engine.BuildRuleIndices();
    return engine;
}

} // namespace

TEST(ProcessLog, EmptyFilenameOrFunctionIgnored) {
    auto engine = MakeEngineWithRules();
    brpc::DiagnosisEngine::MatchState state;
    brpc::BrpcLog log;
    log.functionName = "FuncA";
    log.message = "an error occurred";
    engine.ProcessLog(std::move(log), state);
    EXPECT_TRUE(state.ruleIndexToLogs.empty());

    brpc::BrpcLog log2;
    log2.filename = "a.cpp";
    log2.message = "an error occurred";
    engine.ProcessLog(std::move(log2), state);
    EXPECT_TRUE(state.ruleIndexToLogs.empty());
}

TEST(ProcessLog, UnknownFilenameOrFunctionIgnored) {
    auto engine = MakeEngineWithRules();
    brpc::DiagnosisEngine::MatchState state;

    brpc::BrpcLog wrongFile;
    wrongFile.filename = "unknown.cpp";
    wrongFile.functionName = "FuncA";
    wrongFile.message = "an error occurred";
    engine.ProcessLog(std::move(wrongFile), state);
    EXPECT_TRUE(state.ruleIndexToLogs.empty());

    brpc::BrpcLog wrongFunc;
    wrongFunc.filename = "a.cpp";
    wrongFunc.functionName = "FuncB";
    wrongFunc.message = "an error occurred";
    engine.ProcessLog(std::move(wrongFunc), state);
    EXPECT_TRUE(state.ruleIndexToLogs.empty());
}

TEST(ProcessLog, MatchingLogRecorded) {
    auto engine = MakeEngineWithRules();
    brpc::DiagnosisEngine::MatchState state;
    brpc::BrpcLog log;
    log.filename = "a.cpp";
    log.functionName = "FuncA";
    log.message = "an error occurred";
    engine.ProcessLog(std::move(log), state);
    ASSERT_EQ(state.ruleIndexToLogs.size(), 1u);
    ASSERT_NE(state.ruleIndexToLogs.find(0), state.ruleIndexToLogs.end());
    ASSERT_EQ(state.ruleIndexToLogs[0].size(), 1u);
    EXPECT_EQ(state.ruleIndexToLogs[0][0].message, "an error occurred");
}

TEST(ProcessLog, NoKeywordMatchNotRecorded) {
    auto engine = MakeEngineWithRules();
    brpc::DiagnosisEngine::MatchState state;
    brpc::BrpcLog log;
    log.filename = "a.cpp";
    log.functionName = "FuncA";
    log.message = "everything is fine";
    engine.ProcessLog(std::move(log), state);
    EXPECT_TRUE(state.ruleIndexToLogs.empty());
}

TEST(ProcessLog, UrmaLogUsesUrmaIndex) {
    auto engine = MakeEngineWithRules();
    brpc::DiagnosisEngine::MatchState state;

    // URMA 日志即使带 brpc 索引中的文件名也不走 brpc 索引
    brpc::BrpcLog wrongIndex;
    wrongIndex.component = "URMA";
    wrongIndex.filename = "a.cpp";
    wrongIndex.functionName = "FuncA";
    wrongIndex.message = "an error occurred";
    engine.ProcessLog(std::move(wrongIndex), state);
    EXPECT_TRUE(state.ruleIndexToLogs.empty());

    brpc::BrpcLog urmaLog;
    urmaLog.component = "URMA";
    urmaLog.filename = "u.cpp";
    urmaLog.functionName = "FuncU";
    urmaLog.message = "urma fail detected";
    engine.ProcessLog(std::move(urmaLog), state);
    ASSERT_EQ(state.ruleIndexToLogs.size(), 1u);
    EXPECT_NE(state.ruleIndexToLogs.find(1), state.ruleIndexToLogs.end());
}

TEST(SelectBestHit, NoMatchLeavesStateEmpty) {
    brpc::DiagnosisEngine engine;
    brpc::DiagnosisRule rule;
    rule.keywords = {"missing"};
    engine.rules_ = {rule};
    brpc::DiagnosisEngine::MatchState state;
    brpc::BrpcLog log;
    log.message = "totally different";
    engine.SelectBestHit(std::move(log), {0}, state);
    EXPECT_TRUE(state.ruleIndexToLogs.empty());
}

TEST(SelectBestHit, PrefersLongestMatch) {
    brpc::DiagnosisEngine engine;
    brpc::DiagnosisRule longRule;
    longRule.keywords = {"error"};
    brpc::DiagnosisRule shortRule;
    shortRule.keywords = {"err"};
    engine.rules_ = {longRule, shortRule};

    brpc::DiagnosisEngine::MatchState state;
    brpc::BrpcLog log;
    log.message = "error happened";
    engine.SelectBestHit(std::move(log), {0, 1}, state);
    ASSERT_EQ(state.ruleIndexToLogs.size(), 1u);
    EXPECT_NE(state.ruleIndexToLogs.find(0), state.ruleIndexToLogs.end());
}

TEST(SelectBestHit, SameLengthPrefersEarlierIndex) {
    brpc::DiagnosisEngine engine;
    brpc::DiagnosisRule first;
    first.keywords = {"error"};
    brpc::DiagnosisRule second;
    second.keywords = {"error"};
    engine.rules_ = {first, second};

    brpc::DiagnosisEngine::MatchState state;
    brpc::BrpcLog log;
    log.message = "error happened";
    // 候选乱序传入，同长度时仍应选择规则数组中靠前的一条
    engine.SelectBestHit(std::move(log), {1, 0}, state);
    ASSERT_EQ(state.ruleIndexToLogs.size(), 1u);
    EXPECT_NE(state.ruleIndexToLogs.find(0), state.ruleIndexToLogs.end());
}

TEST(RunDiagnosis, InvalidLogPathReturnsNullopt) {
    brpc::DiagnosisEngine engine;
    brpc::LogCollector collector("/nonexistent/witty/brpc/log/path");
    auto result = engine.RunDiagnosis(collector, 0, 1000);
    EXPECT_FALSE(result.has_value());
}
