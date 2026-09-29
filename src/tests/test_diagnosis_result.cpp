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
#include <json/json.h>

#include <cctype>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <memory>
#include <optional>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

#include "diagnosis_model.h"
#include "log_def.h"
#include "temp_dir.h"

// 访问私有成员便于直测
#define private public
#include "diagnosis_result.h"
#undef private

#include "logger.h"

namespace {

// 被测实现打日志走 log4cplus，必须先初始化，否则崩溃。
struct LoggerInit {
    LoggerInit() noexcept { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// "20260101 12:00:00.000000"（东八区）对应的 UTC 微秒时间戳
constexpr std::int64_t TS = 1767240000000000;
constexpr std::int64_t MICROSECONDS_PER_SECOND = 1000000;

// RAII 临时目录（公共实现见 temp_dir.h）

// MakeRule 的可选字段（避免函数参数过多）。
struct RuleExtras {
    std::vector<std::size_t> localChildren;
    std::vector<std::size_t> crossChildren;
    std::optional<brpc::DiagnosisErrorCode> errorCode = std::nullopt;
};

brpc::DiagnosisRule MakeRule(const std::string &id, brpc::DiagnosisComponent component, bool publicApi,
                             const RuleExtras &extras = {})
{
    brpc::DiagnosisRule rule;
    rule.failureMode.id = id;
    rule.failureMode.name = "name_" + id;
    rule.failureMode.filename = id + ".cpp";
    rule.failureMode.functionName = "Func_" + id;
    rule.failureMode.component = component;
    rule.failureMode.phenomenon = publicApi ? "向下级匹配" : "依次匹配`kw`";
    rule.failureMode.cause = "cause_" + id;
    rule.failureMode.solution = "solution_" + id;
    rule.failureMode.errorCode = extras.errorCode;
    rule.failureMode.publicApi = publicApi;
    rule.keywords = publicApi ? std::vector<std::string>{} : std::vector<std::string>{"kw"};
    rule.localChildIndices = extras.localChildren;
    rule.crossChildIndices = extras.crossChildren;
    return rule;
}

// MakeLog 的可选字段（避免函数参数过多）。
struct LogExtras {
    std::string podName = "pod-1";
    std::string podIp = "10.0.0.1";
    std::optional<int> threadId = std::nullopt;
    std::string traceId = "trace-1";
};

// 测试日志固定源码行号（f.cpp 的 F 函数）。
constexpr int TEST_LOG_LINE_NO = 42;

brpc::DiagnosisLog MakeLog(std::int64_t timestamp, const std::string &message, const LogExtras &extras = {})
{
    brpc::DiagnosisLog log;
    log.timestamp = timestamp;
    log.text = message;
    log.message = message;
    log.podName = extras.podName;
    log.podIp = extras.podIp;
    log.filename = "f.cpp";
    log.functionName = "F";
    log.lineNo = TEST_LOG_LINE_NO;
    log.threadId = extras.threadId;
    if (!extras.traceId.empty()) {
        log.traceId = extras.traceId;
    }
    return log;
}

// 0: ubsocket_root(publicApi) --local--> 1: ubsocket_err
std::vector<brpc::DiagnosisRule> MakeSimpleRules()
{
    return {
        MakeRule("ubsocket_root", brpc::DiagnosisComponent::UBSOCKET, true, {{1}, {}, std::int64_t(1001)}),
        MakeRule("ubsocket_err", brpc::DiagnosisComponent::UBSOCKET, false, {{}, {}, std::string("E002")}),
    };
}

// 0: ubsocket_root(publicApi) --local--> {1: ubsocket_err, 2: ubsocket_err2}
std::vector<brpc::DiagnosisRule> MakeTwoFailureRules()
{
    return {
        MakeRule("ubsocket_root", brpc::DiagnosisComponent::UBSOCKET, true, {{1, 2}, {}, std::int64_t(1001)}),
        MakeRule("ubsocket_err", brpc::DiagnosisComponent::UBSOCKET, false, {{}, {}, std::string("E002")}),
        MakeRule("ubsocket_err2", brpc::DiagnosisComponent::UBSOCKET, false),
    };
}

// errA 可达 api1/api2（双候选），errB 仅可达 api2（唯一候选）
std::vector<brpc::DiagnosisRule> MakeThreadChainRules()
{
    return {
        MakeRule("ubsocket_api1", brpc::DiagnosisComponent::UBSOCKET, true, {{2}}),
        MakeRule("ubsocket_api2", brpc::DiagnosisComponent::UBSOCKET, true, {{2, 3}}),
        MakeRule("ubsocket_errA", brpc::DiagnosisComponent::UBSOCKET, false),
        MakeRule("ubsocket_errB", brpc::DiagnosisComponent::UBSOCKET, false),
    };
}

// errA 仅可达 api1，errB 仅可达 api2 → 同请求共同候选为空
std::vector<brpc::DiagnosisRule> MakeDisjointCandidateRules()
{
    return {
        MakeRule("ubsocket_api1", brpc::DiagnosisComponent::UBSOCKET, true, {{2}}),
        MakeRule("ubsocket_api2", brpc::DiagnosisComponent::UBSOCKET, true, {{3}}),
        MakeRule("ubsocket_errA", brpc::DiagnosisComponent::UBSOCKET, false),
        MakeRule("ubsocket_errB", brpc::DiagnosisComponent::UBSOCKET, false),
    };
}

// ubsocket_err 有跨组件边：→umq_api1(public，可作 anchor)、→umq_err(非 public，不作 anchor)。
// umq_err 候选 {umq_api1, umq_api2}，被 anchor 收窄到 umq_api1。
std::vector<brpc::DiagnosisRule> MakeCrossComponentRules()
{
    return {
        MakeRule("ubsocket_root", brpc::DiagnosisComponent::UBSOCKET, true, {{1}}),
        MakeRule("ubsocket_err", brpc::DiagnosisComponent::UBSOCKET, false, {{}, {2, 3}}),
        MakeRule("umq_api1", brpc::DiagnosisComponent::UMQ, true, {{4}}),
        MakeRule("umq_err", brpc::DiagnosisComponent::UMQ, false),
        MakeRule("umq_api2", brpc::DiagnosisComponent::UMQ, true, {{3}}),
    };
}

// 跨组件 anchor(umq_apiX) 不在 umq_err 的候选集内 → 交集为空，保持未归因
std::vector<brpc::DiagnosisRule> MakeOffAnchorRules()
{
    return {
        MakeRule("ubsocket_root", brpc::DiagnosisComponent::UBSOCKET, true, {{1}}),
        MakeRule("ubsocket_err", brpc::DiagnosisComponent::UBSOCKET, false, {{}, {2}}),
        MakeRule("umq_apiX", brpc::DiagnosisComponent::UMQ, true),
        MakeRule("umq_api1", brpc::DiagnosisComponent::UMQ, true, {{5}}),
        MakeRule("umq_api2", brpc::DiagnosisComponent::UMQ, true, {{5}}),
        MakeRule("umq_err", brpc::DiagnosisComponent::UMQ, false),
    };
}

std::string ReadFile(const std::filesystem::path &path)
{
    std::ifstream in(path);
    std::stringstream buffer;
    buffer << in.rdbuf();
    return buffer.str();
}

std::vector<std::string> ReadLines(const std::filesystem::path &path)
{
    std::ifstream in(path);
    std::vector<std::string> lines;
    std::string line;
    while (std::getline(in, line)) {
        lines.push_back(line);
    }
    return lines;
}

Json::Value ParseJsonText(const std::string &text)
{
    Json::Value root;
    const std::unique_ptr<Json::CharReader> reader(Json::CharReaderBuilder().newCharReader());
    std::string errors;
    if (!reader->parse(text.data(), text.data() + text.size(), &root, &errors)) {
        ADD_FAILURE() << "failed to parse json: " << errors;
    }
    return root;
}

std::vector<std::string> ListFileNamesWithPrefix(const std::filesystem::path &directory, const std::string &prefix)
{
    std::vector<std::string> names;
    for (const auto &entry : std::filesystem::directory_iterator(directory)) {
        const std::string name = entry.path().filename().string();
        if (name.rfind(prefix, 0) == 0) {
            names.push_back(name);
        }
    }
    return names;
}

// UUID v7 文本格式的结构位置（8-4-4-4-12 十六进制段，段间连字符）。
constexpr std::size_t UUID_TEXT_LENGTH = 36;
constexpr std::size_t UUID_VERSION_NIBBLE = 14; // 第 3 段首字符：版本号
constexpr std::size_t UUID_VARIANT_NIBBLE = 19; // 第 4 段首字符：变体位
constexpr std::size_t UUID_HYPHEN_POSITIONS[] = {8, 13, 18, 23};

bool IsUuidV7(const std::string &value)
{
    if (value.size() != UUID_TEXT_LENGTH) {
        return false;
    }
    for (std::size_t i = 0; i < value.size(); ++i) {
        const char character = value[i];
        const bool atHyphen = (i == UUID_HYPHEN_POSITIONS[0] || i == UUID_HYPHEN_POSITIONS[1] ||
                               i == UUID_HYPHEN_POSITIONS[2] || i == UUID_HYPHEN_POSITIONS[3]);
        if (atHyphen) {
            if (character != '-') {
                return false;
            }
        } else if (!std::isxdigit(static_cast<unsigned char>(character))) {
            return false;
        }
    }
    return value[UUID_VERSION_NIBBLE] == '7' && (value[UUID_VARIANT_NIBBLE] == '8' || value[UUID_VARIANT_NIBBLE] == '9' ||
                                                 value[UUID_VARIANT_NIBBLE] == 'a' || value[UUID_VARIANT_NIBBLE] == 'b');
}

} // namespace

// ---------------------------------------------------------------------------
// 原有琐碎用例（diagnosis_model.h 默认值）
// ---------------------------------------------------------------------------

TEST(DiagnosisComponentToString, AllComponents) {
    EXPECT_STREQ(brpc::ToString(brpc::DiagnosisComponent::UBSOCKET), "ubsocket");
    EXPECT_STREQ(brpc::ToString(brpc::DiagnosisComponent::UMQ), "umq");
    EXPECT_STREQ(brpc::ToString(brpc::DiagnosisComponent::URMA), "urma");
    EXPECT_STREQ(brpc::ToString(brpc::DiagnosisComponent::UNKNOWN), "");
}

TEST(DiagnosisEdgeTypeToString, AllTypes) {
    EXPECT_STREQ(brpc::ToString(brpc::DiagnosisEdgeType::INTRA_COMPONENT), "intra_component");
    EXPECT_STREQ(brpc::ToString(brpc::DiagnosisEdgeType::CROSS_COMPONENT), "cross_component");
}

TEST(FailureModeInfo, DefaultValues) {
    brpc::FailureModeInfo info;
    EXPECT_TRUE(info.id.empty());
    EXPECT_TRUE(info.name.empty());
    EXPECT_EQ(info.component, brpc::DiagnosisComponent::UNKNOWN);
    EXPECT_FALSE(info.publicApi);
    EXPECT_FALSE(info.errorCode.has_value());
}

TEST(DiagnosisRule, DefaultValues) {
    brpc::DiagnosisRule rule;
    EXPECT_TRUE(rule.keywords.empty());
    EXPECT_TRUE(rule.localChildIndices.empty());
    EXPECT_TRUE(rule.crossChildIndices.empty());
}

// ---------------------------------------------------------------------------
// Build：区间校验 / 基础成功路径
// ---------------------------------------------------------------------------

TEST(DiagnosisResultBuild, RejectsInvalidInterval) {
    brpc::DiagnosisResult result;
    const auto rules = MakeSimpleRules();
    EXPECT_FALSE(result.Build(rules, {}, -1, 100));
    EXPECT_FALSE(result.Build(rules, {}, 200, 100));
    // 起止相等的空区间合法
    EXPECT_TRUE(result.Build(rules, {}, 100, 100));
}

TEST(DiagnosisResultBuild, BuildsSimpleScenario) {
    brpc::DiagnosisResult result;
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {1, {MakeLog(TS + 1500000, "hit message")}},
    };
    ASSERT_TRUE(result.Build(MakeSimpleRules(), directlyHitLogs, TS - 1000000, TS + 5000000));

    EXPECT_EQ(result.nodes_.size(), 2u);
    ASSERT_EQ(result.edges_.size(), 1u);
    EXPECT_EQ(result.edges_[0].sourceIndex, 0u);
    EXPECT_EQ(result.edges_[0].targetIndex, 1u);
    EXPECT_EQ(result.edges_[0].type, brpc::DiagnosisEdgeType::INTRA_COMPONENT);
    ASSERT_EQ(result.mappings_.size(), 1u);
    EXPECT_EQ(result.mappings_[0].failureModeIndex, 1u);
    ASSERT_EQ(result.mappings_[0].interfaceIndices.size(), 1u);
    EXPECT_EQ(result.mappings_[0].interfaceIndices[0], 0u);
    ASSERT_EQ(result.mappings_[0].subgraphEdgeIndices.size(), 1u);

    ASSERT_EQ(result.hits_.size(), 1u);
    EXPECT_EQ(result.hits_[0].failureModeIndex, 1u);
    EXPECT_EQ(result.hits_[0].log.message, "hit message");
}

TEST(DiagnosisResultBuild, SucceedsWithOnlyPublicInterfaces) {
    brpc::DiagnosisResult result;
    std::vector<brpc::DiagnosisRule> rules = {
        MakeRule("ubsocket_root", brpc::DiagnosisComponent::UBSOCKET, true),
    };
    EXPECT_TRUE(result.Build(rules, {}, 0, 1000));
    EXPECT_TRUE(result.mappings_.empty());
    EXPECT_TRUE(result.hits_.empty());
}

TEST(DiagnosisResultBuild, RejectsDuplicateNodeIds) {
    brpc::DiagnosisResult result;
    auto rules = MakeSimpleRules();
    rules[1].failureMode.id = "ubsocket_root"; // 与 rules[0] 重复
    EXPECT_FALSE(result.Build(rules, {}, 0, 1000));
}

TEST(DiagnosisResultBuild, RejectsInvalidLocalEdgeTarget) {
    brpc::DiagnosisResult result;
    auto rules = MakeSimpleRules();
    rules[0].localChildIndices = {77};
    EXPECT_FALSE(result.Build(rules, {}, 0, 1000));
}

TEST(DiagnosisResultBuild, RejectsInvalidCrossEdgeTarget) {
    brpc::DiagnosisResult result;
    auto rules = MakeSimpleRules();
    rules[0].crossChildIndices = {88};
    EXPECT_FALSE(result.Build(rules, {}, 0, 1000));
}

TEST(DiagnosisResultBuild, RejectsLocalEdgeAcrossComponents) {
    brpc::DiagnosisResult result;
    std::vector<brpc::DiagnosisRule> rules = {
        MakeRule("ubsocket_root", brpc::DiagnosisComponent::UBSOCKET, true, {{1}}),
        MakeRule("umq_err", brpc::DiagnosisComponent::UMQ, false),
    };
    EXPECT_FALSE(result.Build(rules, {}, 0, 1000));
}

TEST(DiagnosisResultBuild, RejectsFailureWithoutReachableInterface) {
    brpc::DiagnosisResult result;
    std::vector<brpc::DiagnosisRule> rules = {
        MakeRule("ubsocket_err", brpc::DiagnosisComponent::UBSOCKET, false),
    };
    EXPECT_FALSE(result.Build(rules, {}, 0, 1000));
}

TEST(DiagnosisResultBuild, HandlesLocalEdgeCycle) {
    brpc::DiagnosisResult result;
    std::vector<brpc::DiagnosisRule> rules = {
        MakeRule("ubsocket_root", brpc::DiagnosisComponent::UBSOCKET, true, {{1}}),
        MakeRule("ubsocket_err", brpc::DiagnosisComponent::UBSOCKET, false, {{0}}), // 回边成环
    };
    EXPECT_TRUE(result.Build(rules, {}, 0, 1000));
    EXPECT_EQ(result.mappings_.size(), 1u);
}

// ---------------------------------------------------------------------------
// BuildHits：非法命中与区间/排序
// ---------------------------------------------------------------------------

TEST(DiagnosisResultBuild, RejectsHitOnPublicInterfaceRule) {
    brpc::DiagnosisResult result;
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {0, {MakeLog(500, "hit on root")}},
    };
    EXPECT_FALSE(result.Build(MakeSimpleRules(), directlyHitLogs, 0, 1000));
}

TEST(DiagnosisResultBuild, RejectsOutOfRangeHitRuleIndex) {
    brpc::DiagnosisResult result;
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {42, {MakeLog(500, "ghost rule")}},
    };
    EXPECT_FALSE(result.Build(MakeSimpleRules(), directlyHitLogs, 0, 1000));
}

TEST(DiagnosisResultBuild, RejectsHitOutsideInterval) {
    brpc::DiagnosisResult result;
    const auto rules = MakeSimpleRules();
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {1, {MakeLog(TS - 2000000, "before window")}},
    };
    EXPECT_FALSE(result.Build(rules, directlyHitLogs, TS - 1000000, TS + 1000000));

    directlyHitLogs[1] = {MakeLog(TS + 1000000, "at window end")};
    EXPECT_FALSE(result.Build(rules, directlyHitLogs, TS - 1000000, TS + 1000000));
}

TEST(DiagnosisResultBuild, SortsHitsAndClampsInterval) {
    brpc::DiagnosisResult result;
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {1, {MakeLog(TS + 2000000, "m-b"), MakeLog(TS + 1000000, "m-c")}},
        {2, {MakeLog(TS + 3000000, "m-d"), MakeLog(TS + 2000000, "m-a")}},
    };
    ASSERT_TRUE(result.Build(MakeTwoFailureRules(), directlyHitLogs, TS - 5000000, TS + 5000000));

    ASSERT_EQ(result.hits_.size(), 4u);
    // 排序键：(timestamp, 故障模式 id, 日志文本)
    EXPECT_EQ(result.hits_[0].log.message, "m-c");
    EXPECT_EQ(result.hits_[0].failureModeIndex, 1u);
    EXPECT_EQ(result.hits_[1].log.message, "m-b"); // 同时刻同 id，按文本
    EXPECT_EQ(result.hits_[2].log.message, "m-a"); // 同时刻按 id：err < err2
    EXPECT_EQ(result.hits_[2].failureModeIndex, 2u);
    EXPECT_EQ(result.hits_[3].log.message, "m-d");

    // 区间收紧到实际命中数据
    EXPECT_EQ(result.startTimestamp_, TS + 1000000);
    EXPECT_EQ(result.endTimestamp_, (TS + 3000000) / MICROSECONDS_PER_SECOND * MICROSECONDS_PER_SECOND +
                                       MICROSECONDS_PER_SECOND);
}

// ---------------------------------------------------------------------------
// ResolveHitInterfaces：接口归因策略
// ---------------------------------------------------------------------------

TEST(DiagnosisResultResolution, StaticUniqueWhenSingleInterface) {
    brpc::DiagnosisResult result;
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {1, {MakeLog(TS + 1000000, "hit")}},
    };
    ASSERT_TRUE(result.Build(MakeSimpleRules(), directlyHitLogs, TS, TS + 5000000));
    ASSERT_EQ(result.hits_.size(), 1u);
    ASSERT_TRUE(result.hits_[0].interfaceIndex.has_value());
    EXPECT_EQ(*result.hits_[0].interfaceIndex, 0u);
    EXPECT_EQ(result.hits_[0].interfaceResolution, "static_unique");
}

TEST(DiagnosisResultResolution, ThreadChainNarrowsCommonInterface) {
    brpc::DiagnosisResult result;
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {2, {MakeLog(TS + 1000000, "hitA", {"pod-1", "10.0.0.1", 7})}},
        {3, {MakeLog(TS + 2000000, "hitB", {"pod-1", "10.0.0.1", 7})}},
    };
    ASSERT_TRUE(result.Build(MakeThreadChainRules(), directlyHitLogs, TS, TS + 5000000));
    ASSERT_EQ(result.hits_.size(), 2u);

    // errA 双候选，与 errB 的唯一候选取交集 → thread_chain
    EXPECT_EQ(result.hits_[0].failureModeIndex, 2u);
    ASSERT_TRUE(result.hits_[0].interfaceIndex.has_value());
    EXPECT_EQ(*result.hits_[0].interfaceIndex, 1u);
    EXPECT_EQ(result.hits_[0].interfaceResolution, "thread_chain");

    // errB 候选唯一 → 保持 static_unique，且不被重复赋值
    EXPECT_EQ(result.hits_[1].failureModeIndex, 3u);
    ASSERT_TRUE(result.hits_[1].interfaceIndex.has_value());
    EXPECT_EQ(*result.hits_[1].interfaceIndex, 1u);
    EXPECT_EQ(result.hits_[1].interfaceResolution, "static_unique");
}

TEST(DiagnosisResultResolution, SameRequestDisjointCandidatesStaysUnchanged) {
    brpc::DiagnosisResult result;
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {2, {MakeLog(TS + 1000000, "hitA", {"pod-1", "10.0.0.1", 9})}},
        {3, {MakeLog(TS + 2000000, "hitB", {"pod-1", "10.0.0.1", 9})}},
    };
    ASSERT_TRUE(result.Build(MakeDisjointCandidateRules(), directlyHitLogs, TS, TS + 5000000));
    ASSERT_EQ(result.hits_.size(), 2u);
    // 共同候选为空 → 提前返回，各自保持 static_unique
    ASSERT_TRUE(result.hits_[0].interfaceIndex.has_value());
    EXPECT_EQ(*result.hits_[0].interfaceIndex, 0u);
    EXPECT_EQ(result.hits_[0].interfaceResolution, "static_unique");
    ASSERT_TRUE(result.hits_[1].interfaceIndex.has_value());
    EXPECT_EQ(*result.hits_[1].interfaceIndex, 1u);
    EXPECT_EQ(result.hits_[1].interfaceResolution, "static_unique");
}

TEST(DiagnosisResultResolution, CrossComponentAnchorResolvesInterface) {
    brpc::DiagnosisResult result;
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {1, {MakeLog(TS + 1000000, "brpc hit", {"pod-1", "10.0.0.1", 5})}},
        {3, {MakeLog(TS + 2000000, "umq hit", {"pod-1", "10.0.0.1", 5})}},
    };
    ASSERT_TRUE(result.Build(MakeCrossComponentRules(), directlyHitLogs, TS, TS + 5000000));
    ASSERT_EQ(result.hits_.size(), 2u);

    // ubsocket_err 候选唯一 → static_unique
    EXPECT_EQ(result.hits_[0].failureModeIndex, 1u);
    ASSERT_TRUE(result.hits_[0].interfaceIndex.has_value());
    EXPECT_EQ(*result.hits_[0].interfaceIndex, 0u);
    EXPECT_EQ(result.hits_[0].interfaceResolution, "static_unique");

    // umq_err 双候选，被跨组件 anchor(umq_api1) 收窄 → cross_component
    EXPECT_EQ(result.hits_[1].failureModeIndex, 3u);
    ASSERT_TRUE(result.hits_[1].interfaceIndex.has_value());
    EXPECT_EQ(*result.hits_[1].interfaceIndex, 2u);
    EXPECT_EQ(result.hits_[1].interfaceResolution, "cross_component");
}

TEST(DiagnosisResultResolution, CrossAnchorOutsideCandidatesKeepsUnresolved) {
    brpc::DiagnosisResult result;
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {1, {MakeLog(TS + 1000000, "brpc hit", {"pod-1", "10.0.0.1", 3})}},
        {5, {MakeLog(TS + 2000000, "umq hit", {"pod-1", "10.0.0.1", 3})}},
    };
    ASSERT_TRUE(result.Build(MakeOffAnchorRules(), directlyHitLogs, TS, TS + 5000000));
    ASSERT_EQ(result.hits_.size(), 2u);
    // anchor 不在候选集内 → 交集为空，umq_err 保持未归因
    EXPECT_EQ(result.hits_[1].failureModeIndex, 5u);
    EXPECT_FALSE(result.hits_[1].interfaceIndex.has_value());
    EXPECT_EQ(result.hits_[1].interfaceResolution, "unresolved");
}

TEST(DiagnosisResultResolution, HitWithoutRequestIdentityStaysUnresolved) {
    brpc::DiagnosisResult result;
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {2,
         {MakeLog(TS + 1000000, "no thread", {"pod-1", "10.0.0.1", std::nullopt}),
          MakeLog(TS + 2000000, "no pod ip", {"pod-1", "", 9})}},
    };
    ASSERT_TRUE(result.Build(MakeThreadChainRules(), directlyHitLogs, TS, TS + 5000000));
    ASSERT_EQ(result.hits_.size(), 2u);
    // 缺 threadId 或 podIp 都无法组成请求 → 不参与共同候选归因
    EXPECT_FALSE(result.hits_[0].interfaceIndex.has_value());
    EXPECT_EQ(result.hits_[0].interfaceResolution, "unresolved");
    EXPECT_FALSE(result.hits_[1].interfaceIndex.has_value());
    EXPECT_EQ(result.hits_[1].interfaceResolution, "unresolved");
}

// ---------------------------------------------------------------------------
// 私有构建步骤直测：BuildEdges / BuildMappingSubgraphs
// ---------------------------------------------------------------------------

TEST(DiagnosisResultEdges, SortsAndDeduplicates) {
    brpc::DiagnosisResult result;
    auto rules = MakeSimpleRules();
    rules[0].localChildIndices = {1, 1}; // 重复 intra 边
    rules[0].crossChildIndices = {1};    // 同 source/target 不同 type，保留
    rules[1].localChildIndices = {0};    // 反向边
    ASSERT_TRUE(result.BuildEdges(rules));
    ASSERT_EQ(result.edges_.size(), 3u);
    EXPECT_EQ(result.edges_[0].sourceIndex, 0u);
    EXPECT_EQ(result.edges_[0].targetIndex, 1u);
    EXPECT_EQ(result.edges_[0].type, brpc::DiagnosisEdgeType::INTRA_COMPONENT);
    EXPECT_EQ(result.edges_[1].sourceIndex, 0u);
    EXPECT_EQ(result.edges_[1].targetIndex, 1u);
    EXPECT_EQ(result.edges_[1].type, brpc::DiagnosisEdgeType::CROSS_COMPONENT);
    EXPECT_EQ(result.edges_[2].sourceIndex, 1u);
    EXPECT_EQ(result.edges_[2].targetIndex, 0u);
    EXPECT_EQ(result.edges_[2].type, brpc::DiagnosisEdgeType::INTRA_COMPONENT);
}

TEST(DiagnosisResultEdges, RejectsInvalidTargets) {
    auto rules = MakeSimpleRules();
    rules[0].localChildIndices = {77};
    rules[0].crossChildIndices = {};
    brpc::DiagnosisResult localResult;
    EXPECT_FALSE(localResult.BuildEdges(rules));

    rules[0].localChildIndices = {};
    rules[0].crossChildIndices = {88};
    brpc::DiagnosisResult crossResult;
    EXPECT_FALSE(crossResult.BuildEdges(rules));
}

TEST(DiagnosisResultSubgraphs, RejectsInvalidChildIndex) {
    brpc::DiagnosisResult result;
    auto rules = MakeSimpleRules();
    rules[0].localChildIndices = {77};
    result.mappings_.push_back({1, {0}, {}});
    EXPECT_FALSE(result.BuildMappingSubgraphs(rules));
}

TEST(DiagnosisResultSubgraphs, RejectsEmptySubgraph) {
    brpc::DiagnosisResult result;
    auto rules = MakeSimpleRules();
    rules[0].localChildIndices = {}; // 接口到故障模式无边
    result.mappings_.push_back({1, {0}, {}});
    EXPECT_FALSE(result.BuildMappingSubgraphs(rules));
}

// ---------------------------------------------------------------------------
// Dump：schema 与 batch 输出
// ---------------------------------------------------------------------------

// batch_task_1.jsonl 首行（batch 记录）的字段断言。
void VerifyBatchRecord(const Json::Value &batch)
{
    EXPECT_EQ(batch["record_type"].asString(), "batch");
    EXPECT_EQ(batch["format_version"].asInt(), 2);
    EXPECT_EQ(batch["task_id"].asString(), "task_1");
    EXPECT_TRUE(IsUuidV7(batch["batch_id"].asString()));
    EXPECT_EQ(batch["hit_count"].asUInt64(), 2u);
    EXPECT_EQ(batch["start_timestamp"].asInt64(), TS + 1000000);
    EXPECT_EQ(batch["end_timestamp"].asInt64(), TS + 3000000);
}

// schema_*.json 文件的节点/边/映射断言。
void VerifySchemaFile(const std::filesystem::path &directory, const Json::Value &batch)
{
    const auto schemaFiles = ListFileNamesWithPrefix(directory, "schema_");
    EXPECT_EQ(schemaFiles.size(), 1u);
    const std::string schemaId = schemaFiles[0].substr(7, schemaFiles[0].size() - 7 - 5);
    EXPECT_EQ(schemaId.size(), 64u);
    EXPECT_EQ(batch["schema_id"].asString(), schemaId);

    const Json::Value schema = ParseJsonText(ReadFile(directory / schemaFiles[0]));
    EXPECT_EQ(schema["schema_id"].asString(), schemaId);
    EXPECT_EQ(schema["format_version"].asInt(), 1);

    // 节点按 id 排序，error_code 覆盖 int/string/null 三种
    const Json::Value &nodes = schema["nodes"];
    ASSERT_EQ(nodes.size(), 3u);
    EXPECT_EQ(nodes[0]["node_id"].asString(), "ubsocket_err");
    EXPECT_EQ(nodes[0]["node_type"].asString(), "failure_mode");
    EXPECT_EQ(nodes[0]["component"].asString(), "ubsocket");
    EXPECT_EQ(nodes[0]["name"].asString(), "name_ubsocket_err");
    EXPECT_EQ(nodes[0]["filename"].asString(), "ubsocket_err.cpp");
    EXPECT_EQ(nodes[0]["function_name"].asString(), "Func_ubsocket_err");
    EXPECT_EQ(nodes[0]["phenomenon"].asString(), "依次匹配`kw`");
    EXPECT_EQ(nodes[0]["cause"].asString(), "cause_ubsocket_err");
    EXPECT_EQ(nodes[0]["solution"].asString(), "solution_ubsocket_err");
    EXPECT_EQ(nodes[0]["error_code"].asString(), "E002");
    EXPECT_EQ(nodes[1]["node_id"].asString(), "ubsocket_err2");
    EXPECT_TRUE(nodes[1]["error_code"].isNull());
    EXPECT_EQ(nodes[2]["node_id"].asString(), "ubsocket_root");
    EXPECT_EQ(nodes[2]["node_type"].asString(), "interface");
    EXPECT_EQ(nodes[2]["error_code"].asInt64(), std::int64_t(1001));

    // 边按 (source id, target id, type) 排序
    const Json::Value &edges = schema["edges"];
    ASSERT_EQ(edges.size(), 2u);
    EXPECT_EQ(edges[0]["source_node_id"].asString(), "ubsocket_root");
    EXPECT_EQ(edges[0]["target_node_id"].asString(), "ubsocket_err");
    EXPECT_EQ(edges[0]["edge_type"].asString(), "intra_component");
    EXPECT_EQ(edges[1]["target_node_id"].asString(), "ubsocket_err2");

    // 映射按故障模式 id 排序，子图边引用 schema 全局边下标
    const Json::Value &mappings = schema["failure_interface_mappings"];
    ASSERT_EQ(mappings.size(), 2u);
    EXPECT_EQ(mappings[0]["failure_mode_id"].asString(), "ubsocket_err");
    ASSERT_EQ(mappings[0]["interface_ids"].size(), 1u);
    EXPECT_EQ(mappings[0]["interface_ids"][0].asString(), "ubsocket_root");
    ASSERT_EQ(mappings[0]["subgraph_edge_indexes"].size(), 1u);
    EXPECT_EQ(mappings[0]["subgraph_edge_indexes"][0].asUInt64(), 0u);
    EXPECT_EQ(mappings[1]["failure_mode_id"].asString(), "ubsocket_err2");
    EXPECT_EQ(mappings[1]["subgraph_edge_indexes"][0].asUInt64(), 1u);
}

// batch_task_1.jsonl 的两条 hit 记录断言。
void VerifyHitRecords(const std::vector<std::string> &lines, const Json::Value &batch)
{
    const Json::Value hit0 = ParseJsonText(lines[1]);
    EXPECT_EQ(hit0["record_type"].asString(), "hit");
    EXPECT_EQ(hit0["hit_id"].asString(), batch["batch_id"].asString() + ":hit:0");
    EXPECT_EQ(hit0["failure_mode_id"].asString(), "ubsocket_err");
    EXPECT_EQ(hit0["interface_id"].asString(), "ubsocket_root");
    EXPECT_EQ(hit0["interface_resolution"].asString(), "static_unique");
    EXPECT_EQ(hit0["timestamp"].asInt64(), TS + 1000000);
    EXPECT_EQ(hit0["thread_id"].asInt(), 7);
    EXPECT_EQ(hit0["trace_id"].asString(), "tr-1");
    EXPECT_EQ(hit0["message"].asString(), "m-err");
    EXPECT_EQ(hit0["pod_name"].asString(), "pod-1");
    EXPECT_EQ(hit0["pod_ip"].asString(), "10.0.0.1");
    EXPECT_EQ(hit0["component"].asString(), "ubsocket");
    EXPECT_EQ(hit0["filename"].asString(), "f.cpp");
    EXPECT_EQ(hit0["function_name"].asString(), "F");
    EXPECT_EQ(hit0["line_number"].asInt(), TEST_LOG_LINE_NO);

    // 可空字段：空串/"-"/缺省 → null
    const Json::Value hit1 = ParseJsonText(lines[2]);
    EXPECT_EQ(hit1["hit_id"].asString(), batch["batch_id"].asString() + ":hit:1");
    EXPECT_EQ(hit1["failure_mode_id"].asString(), "ubsocket_err2");
    EXPECT_TRUE(hit1["thread_id"].isNull());
    EXPECT_TRUE(hit1["trace_id"].isNull());
    EXPECT_TRUE(hit1["pod_name"].isNull());
    EXPECT_TRUE(hit1["pod_ip"].isNull());
    EXPECT_EQ(hit1["timestamp"].asInt64(), TS + 2000000);
}

TEST(DiagnosisResultDump, WritesSchemaAndBatch) {
    TempDir dir("diagres_dump");
    brpc::DiagnosisResult result;
    std::unordered_map<std::size_t, std::vector<brpc::DiagnosisLog>> directlyHitLogs{
        {1, {MakeLog(TS + 1000000, "m-err", {"pod-1", "10.0.0.1", 7, "tr-1"})}},
        {2, {MakeLog(TS + 2000000, "m-err2", {"", "-", std::nullopt, ""})}},
    };
    ASSERT_TRUE(result.Build(MakeTwoFailureRules(), directlyHitLogs, TS - 5000000, TS + 5000000));
    // master 版 Dump 拆为批次/schema 两个目录；此处同目录仍可覆盖全部断言
    ASSERT_TRUE(result.Dump(dir.Path(), dir.Path(), "task_1"));

    const auto lines = ReadLines(dir.Path() / "batch_task_1.jsonl");
    ASSERT_EQ(lines.size(), 3u); // 1 条 batch 记录 + 2 条 hit 记录
    const Json::Value batch = ParseJsonText(lines[0]);
    VerifyBatchRecord(batch);
    VerifySchemaFile(dir.Path(), batch);
    VerifyHitRecords(lines, batch);
}


TEST(DiagnosisResultDump, EmptyHitsUseCreationTimestamp) {
    TempDir dir("diagres_dump_empty");
    brpc::DiagnosisResult result;
    ASSERT_TRUE(result.Build(MakeSimpleRules(), {}, 0, 1000000));
    ASSERT_TRUE(result.Dump(dir.Path(), dir.Path(), "t_empty"));

    const auto lines = ReadLines(dir.Path() / "batch_t_empty.jsonl");
    ASSERT_EQ(lines.size(), 1u);
    const Json::Value batch = ParseJsonText(lines[0]);
    EXPECT_EQ(batch["hit_count"].asUInt64(), 0u);
    const std::int64_t createdAt = batch["created_at_timestamp"].asInt64();
    EXPECT_EQ(batch["start_timestamp"].asInt64(), createdAt);
    EXPECT_EQ(batch["end_timestamp"].asInt64(),
              (createdAt / MICROSECONDS_PER_SECOND + 1) * MICROSECONDS_PER_SECOND);
}

TEST(DiagnosisResultDump, OverwritesBatchAndReusesSchema) {
    TempDir dir("diagres_dump_retry");
    brpc::DiagnosisResult first;
    ASSERT_TRUE(first.Build(MakeSimpleRules(), {{1, {MakeLog(TS + 1000000, "first hit")}}}, TS, TS + 2000000));
    ASSERT_TRUE(first.Dump(dir.Path(), dir.Path(), "t_retry"));

    brpc::DiagnosisResult second;
    ASSERT_TRUE(second.Build(MakeSimpleRules(), {{1, {MakeLog(TS + 1000000, "second hit")}}}, TS, TS + 2000000));
    ASSERT_TRUE(second.Dump(dir.Path(), dir.Path(), "t_retry"));

    // 相同规则 → schema 复用，不重复落盘；batch 原子覆盖，不叠加
    EXPECT_EQ(ListFileNamesWithPrefix(dir.Path(), "schema_").size(), 1u);
    const auto lines = ReadLines(dir.Path() / "batch_t_retry.jsonl");
    ASSERT_EQ(lines.size(), 2u);
    EXPECT_NE(lines[1].find("second hit"), std::string::npos);
    EXPECT_EQ(lines[1].find("first hit"), std::string::npos);

    // 规则变化 → 新 schema
    auto otherRules = MakeSimpleRules();
    otherRules[1].failureMode.name = "changed";
    brpc::DiagnosisResult third;
    ASSERT_TRUE(third.Build(otherRules, {{1, {MakeLog(TS + 1000000, "third hit")}}}, TS, TS + 2000000));
    ASSERT_TRUE(third.Dump(dir.Path(), dir.Path(), "t_retry"));
    EXPECT_EQ(ListFileNamesWithPrefix(dir.Path(), "schema_").size(), 2u);
    EXPECT_EQ(ReadLines(dir.Path() / "batch_t_retry.jsonl").size(), 2u);
}

TEST(DiagnosisResultDump, FailsWhenDirectoryNotCreatable) {
    TempDir dir("diagres_dump_blocked");
    dir.Write("blocker", "x");
    brpc::DiagnosisResult result;
    ASSERT_TRUE(result.Build(MakeSimpleRules(), {}, 0, 1000));
    // 父路径是普通文件 → 目录创建失败
    EXPECT_FALSE(result.Dump(dir.Path() / "blocker" / "sub", dir.Path() / "blocker" / "sub", "t"));
}

TEST(DiagnosisResultDump, NullableFieldsForUnresolvedHit) {
    TempDir dir("diagres_dump_null");
    brpc::DiagnosisResult result;
    std::vector<brpc::DiagnosisRule> rules = {
        MakeRule("x_api1", brpc::DiagnosisComponent::UNKNOWN, true, {{2}}),
        MakeRule("x_api2", brpc::DiagnosisComponent::UNKNOWN, true, {{2}}),
        MakeRule("x_err", brpc::DiagnosisComponent::UNKNOWN, false),
    };
    ASSERT_TRUE(result.Build(rules, {{2, {MakeLog(TS + 1000000, "m")}}}, TS, TS + 2000000));
    ASSERT_TRUE(result.Dump(dir.Path(), dir.Path(), "t_null"));

    const auto lines = ReadLines(dir.Path() / "batch_t_null.jsonl");
    ASSERT_EQ(lines.size(), 2u);
    const Json::Value hit = ParseJsonText(lines[1]);
    EXPECT_TRUE(hit["interface_id"].isNull());
    EXPECT_EQ(hit["interface_resolution"].asString(), "unresolved");
    // UNKNOWN 组件序列化为空串 → 输出 null
    EXPECT_TRUE(hit["component"].isNull());
}
