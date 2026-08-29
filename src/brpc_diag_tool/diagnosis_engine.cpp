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

#define MODULE_NAME "BRPC_DIAG"

#include "diagnosis_engine.h"
#include <json/json.h>
#include <fstream>
#include <memory>
#include <utility>
#include "logger.h"

namespace brpc {

namespace {
constexpr const char *FAILURE_MODE_TREE_PATH_REL = "data/failure_mode_tree.json";

// 三个组件的故障模式 JSON 文件
constexpr const char *COMPONENT_FILES[] = {
    "data/ubsocket/ubsocket_failure_mode.json",
    "data/umq/umq_failure_mode.json",
    "data/urma/urma_failure_mode.json",
};

bool ParseJsonFile(const std::string &path, const char *description, Json::Value &root)
{
    std::ifstream ifs(path);
    if (!ifs.is_open()) {
        LOG_ERROR << "failed to open " << description << ": " << path;
        return false;
    }
    Json::CharReaderBuilder builder;
    std::string errors;
    if (!Json::parseFromStream(builder, ifs, &root, &errors)) {
        LOG_ERROR << "failed to parse " << description << ": " << path << ", error: " << errors;
        return false;
    }
    return true;
}

void PopulateFailureMode(const Json::Value &item, FailureModeInfo &failureMode)
{
    failureMode.id = item.get("故障编号", "").asString();
    failureMode.name = item.get("故障名称", "").asString();
    failureMode.filename = item.get("文件名", "").asString();
    failureMode.phenomenon = item.get("故障现象", "").asString();
    failureMode.cause = item.get("故障原因", "").asString();
    failureMode.solution = item.get("解决办法", "").asString();
    failureMode.functionName = item.get("函数名", "").asString();
    const Json::Value &errorCode = item["错误码"];
    if (errorCode.isString()) {
        failureMode.errorCode = errorCode.asString();
    } else if (errorCode.isIntegral()) {
        failureMode.errorCode = static_cast<std::int64_t>(errorCode.asInt64());
    }
    failureMode.component = GetDiagnosisComponent(failureMode.id);
    failureMode.publicApi = failureMode.phenomenon.find("向下级匹配") != std::string::npos;
}

bool IsValidRule(const DiagnosisRule &rule)
{
    const FailureModeInfo &failureMode = rule.failureMode;
    return !failureMode.id.empty() && !failureMode.name.empty() && !failureMode.filename.empty() &&
           !failureMode.functionName.empty() && failureMode.component != DiagnosisComponent::UNKNOWN &&
           (failureMode.publicApi || !rule.keywords.empty());
}

bool AppendChildEdge(const Json::Value &childId, const std::string &failureModeId,
                     const std::unordered_map<std::string, std::size_t> &idToIndex, std::vector<DiagnosisRule> &rules,
                     DiagnosisRule &parent)
{
    if (!childId.isString()) {
        LOG_ERROR << "non-string child id under failure mode: " << failureModeId;
        return false;
    }
    auto childIt = idToIndex.find(childId.asString());
    if (childIt == idToIndex.end()) {
        LOG_ERROR << "unknown child failure mode: " << childId.asString() << ", parent: " << failureModeId;
        return false;
    }
    const DiagnosisComponent childComponent = rules[childIt->second].failureMode.component;
    if (parent.failureMode.component == childComponent) {
        parent.localChildIndices.push_back(childIt->second);
    } else if (IsSupportedCrossComponentEdge(parent.failureMode.component, childComponent)) {
        parent.crossChildIndices.push_back(childIt->second);
    } else {
        LOG_ERROR << "unsupported cross-component edge: " << failureModeId << " -> " << childId.asString();
        return false;
    }
    return true;
}

} // namespace

std::unique_ptr<DiagnosisEngine> DiagnosisEngine::Create(const std::filesystem::path &wittyDir)
{
    auto engine = std::make_unique<DiagnosisEngine>();
    if (!engine->LoadRulesFromJson(wittyDir)) {
        LOG_ERROR << "DiagnosisEngine: failed to load rules from json";
        return nullptr;
    }
    LOG_INFO << "DiagnosisEngine: loaded " << engine->rules_.size() << " rules from json";
    return engine;
}

std::vector<std::string> DiagnosisEngine::ParseKeywords(const std::string &phenomenon)
{
    std::vector<std::string> kws;
    if (phenomenon.find("向下级匹配") != std::string::npos) {
        return kws;
    }
    // "依次匹配`错误片段1`、`错误片段2`" 解析所有反引号内容作为关键字
    std::size_t i = 0;
    while (i < phenomenon.size()) {
        std::size_t start = phenomenon.find('`', i);
        if (start == std::string::npos) {
            break;
        }
        std::size_t end = phenomenon.find('`', start + 1);
        if (end == std::string::npos) {
            break;
        }
        kws.emplace_back(phenomenon.substr(start + 1, end - start - 1));
        i = end + 1;
    }
    return kws;
}

bool DiagnosisEngine::LoadComponentFailureModes(const std::string &path,
                                                std::unordered_map<std::string, std::size_t> &idToIndex)
{
    Json::Value root;
    if (!ParseJsonFile(path, "failure mode json", root)) {
        return false;
    }
    if (!root.isArray()) {
        LOG_ERROR << "failure mode json is not an array: " << path;
        return false;
    }
    for (Json::ArrayIndex i = 0; i < root.size(); ++i) {
        const auto &item = root[i];
        DiagnosisRule rule;
        PopulateFailureMode(item, rule.failureMode);
        rule.keywords = ParseKeywords(rule.failureMode.phenomenon);
        if (!IsValidRule(rule)) {
            LOG_ERROR << "invalid failure mode entry at " << path << ':' << i;
            return false;
        }
        if (idToIndex.count(rule.failureMode.id)) {
            LOG_ERROR << "duplicate failure mode id: " << rule.failureMode.id;
            return false;
        }
        idToIndex[rule.failureMode.id] = rules_.size();
        rules_.push_back(std::move(rule));
    }
    return true;
}

bool DiagnosisEngine::LoadFailureModeTree(const std::string &path,
                                          const std::unordered_map<std::string, std::size_t> &idToIndex)
{
    Json::Value root;
    if (!ParseJsonFile(path, "failure mode tree json", root)) {
        return false;
    }
    auto moduleNames = root.getMemberNames();
    for (const auto &moduleName : moduleNames) {
        const auto &moduleNode = root[moduleName];
        if (!moduleNode.isObject()) {
            continue;
        }
        auto failureModeIds = moduleNode.getMemberNames();
        for (const auto &failureModeId : failureModeIds) {
            const auto &children = moduleNode[failureModeId];
            if (!children.isArray()) {
                continue;
            }
            // 父节点必须在 rules_ 中（否则其下钻关系对匹配无意义）
            auto parentIt = idToIndex.find(failureModeId);
            if (parentIt == idToIndex.end()) {
                continue;
            }
            DiagnosisRule &parent = rules_[parentIt->second];
            for (const auto &childId : children) {
                if (!AppendChildEdge(childId, failureModeId, idToIndex, rules_, parent)) {
                    return false;
                }
            }
        }
    }
    return true;
}

bool DiagnosisEngine::LoadRulesFromJson(const std::filesystem::path &wittyDir)
{
    rules_.clear();
    std::unordered_map<std::string, std::size_t> idToIndex;

    for (const char *relPath : COMPONENT_FILES) {
        if (!LoadComponentFailureModes((wittyDir / relPath).string(), idToIndex)) {
            return false;
        }
    }
    if (!LoadFailureModeTree((wittyDir / FAILURE_MODE_TREE_PATH_REL).string(), idToIndex)) {
        return false;
    }
    BuildRuleIndices();
    return true;
}

void DiagnosisEngine::BuildRuleIndices()
{
    brpcfilenameToFunctionNameToRuleIndices_.clear();
    urmaFilenameToFunctionNameToRuleIndices_.clear();
    for (std::size_t i = 0; i < rules_.size(); ++i) {
        const DiagnosisRule &rule = rules_[i];
        if (rule.failureMode.publicApi) {
            continue;
        }
        // URMA 使用内层 urma 日志解析出的文件名、函数名建立独立索引。
        if (rule.failureMode.component == DiagnosisComponent::URMA) {
            urmaFilenameToFunctionNameToRuleIndices_[rule.failureMode.filename][rule.failureMode.functionName]
                .push_back(i);
        } else {
            brpcfilenameToFunctionNameToRuleIndices_[rule.failureMode.filename][rule.failureMode.functionName]
                .push_back(i);
        }
    }
}

std::optional<std::size_t> DiagnosisEngine::MatchKeywords(const DiagnosisRule &rule, const std::string &text)
{
    std::size_t offset = 0;
    std::size_t matchLength = 0;
    for (const auto &keyword : rule.keywords) {
        offset = text.find(keyword, offset);
        if (offset == std::string::npos) {
            return std::nullopt;
        }
        offset += keyword.size();
        matchLength += keyword.size();
    }
    return matchLength;
}

std::optional<DiagnosisResult> DiagnosisEngine::RunDiagnosis(const LogCollector &collector, std::int64_t startTimestamp,
                                                             std::int64_t endTimestamp) const
{
    MatchState state;
    if (!collector.ForEachBrpcLog(startTimestamp, endTimestamp,
                                  [this, &state](BrpcLog &&log) { ProcessLog(std::move(log), state); })) {
        return std::nullopt;
    }

    DiagnosisResult result;
    if (!result.Build(rules_, std::move(state.ruleIndexToLogs), startTimestamp, endTimestamp)) {
        return std::nullopt;
    }
    return result;
}

void DiagnosisEngine::ProcessLog(BrpcLog &&log, MatchState &state) const
{
    if (log.filename.empty() || log.functionName.empty()) {
        return;
    }
    // URMA 与外层 BRPC 使用各自的规则索引，但共享相同的两级精确查询逻辑。
    const FilenameToFunctionNameToRuleIndices &ruleIndex = log.component == URMA_COMPONENT ?
                                                               urmaFilenameToFunctionNameToRuleIndices_ :
                                                               brpcfilenameToFunctionNameToRuleIndices_;
    auto filenameIt = ruleIndex.find(log.filename);
    if (filenameIt == ruleIndex.end()) {
        return;
    }
    auto functionIt = filenameIt->second.find(log.functionName);
    if (functionIt == filenameIt->second.end()) {
        return;
    }
    SelectBestHit(std::move(log), functionIt->second, state);
}

void DiagnosisEngine::SelectBestHit(BrpcLog &&log, const std::vector<std::size_t> &candidateIndices,
                                    MatchState &state) const
{
    std::optional<std::size_t> matchedIndex;
    std::size_t longestMatchLength = 0;
    for (std::size_t idx : candidateIndices) {
        const DiagnosisRule &rule = rules_[idx];
        const auto matchLength = MatchKeywords(rule, log.message);
        if (!matchLength.has_value()) {
            continue;
        }
        if (!matchedIndex.has_value() || matchLength.value() > longestMatchLength ||
            (matchLength.value() == longestMatchLength && idx < matchedIndex.value())) {
            longestMatchLength = matchLength.value();
            matchedIndex = idx;
        }
    }
    if (!matchedIndex.has_value()) {
        return;
    }

    state.ruleIndexToLogs[matchedIndex.value()].emplace_back(std::move(log));
}

} // namespace brpc
