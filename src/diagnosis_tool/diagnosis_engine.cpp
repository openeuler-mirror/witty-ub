/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of the Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#define MODULE_NAME "DIAGNOSIS"

#include "diagnosis_engine.h"

#include <algorithm>
#include <array>
#include <fstream>
#include <string_view>
#include <tuple>
#include <utility>

#include "failure_log_helper.h"
#include "logger.h"

namespace diag {
namespace {

constexpr const char *KVCACHE_FAILURE_MODE_PATH = "data/kvcache/kvcache_failure_mode.json";
constexpr const char *URMA_FAILURE_MODE_PATH = "data/urma/urma_failure_mode.json";
constexpr const char *FAILURE_MODE_TREE_PATH = "data/failure_mode_tree.json";
constexpr const char *JSON_KEY_ERROR_CODE = "错误码";
constexpr const char *JSON_KEY_FAILURE_ID = "故障编号";
constexpr const char *JSON_KEY_FAILURE_NAME = "故障名称";
constexpr const char *JSON_KEY_PHENOMENON = "故障现象";
constexpr const char *JSON_KEY_FILENAME = "文件名";
constexpr const char *JSON_KEY_FUNCTION_NAME = "函数名";
constexpr const char *JSON_KEY_NODE_TYPE = "节点类型";
constexpr const char *JSON_KEY_MATCH_CONDITION = "匹配条件";
constexpr const char *JSON_KEY_LOG_MATCH = "日志匹配";
constexpr const char *JSON_KEY_ENABLED = "enabled";
constexpr const char *JSON_KEY_REASON = "reason";
constexpr const char *JSON_KEY_STATUS_CODE = "status_code";
constexpr const char *JSON_KEY_RESP_MSG_NONEMPTY = "resp_msg_nonempty";
constexpr const char *JSON_KEY_CAUSE = "故障原因";
constexpr const char *JSON_KEY_SOLUTION = "解决办法";
constexpr const char *KVCACHE_TREE_MODULE = "kvcache";
constexpr const char *URMA_TREE_MODULE = "urma";
constexpr const char *ACCESS_LOG_ENTRY_TYPE = "access_log_entry";
constexpr const char *RUNTIME_LOG_TYPE = "runtime_log";
constexpr std::array FAILURE_MODE_TREE_MODULES = {KVCACHE_TREE_MODULE, URMA_TREE_MODULE};
constexpr std::string_view URMA_LOG_KEYWORD = "liburma";
constexpr std::string_view URMA_LOG_MARKER = "URMA";
constexpr std::string_view DOWNSTREAM_MATCH_MARKER = "向下级匹配";
constexpr std::string_view FATAL_LEVEL_MARKER = "FATAL";
constexpr std::string_view UNKNOWN_ACCESS_FAILURE_MODE_ID = "kvcache_failure_unknown";
constexpr std::string_view UNKNOWN_STATUS_HINT = "识别到未知状态码，请联系管理员更新知识库";
constexpr const char *UNKNOWN_FAILURE_NAME = "未知故障";
constexpr const char *UNKNOWN_FAILURE_PHENOMENON = "状态码非0且未匹配其他已知故障模式";
constexpr const char *UNKNOWN_PLACEHOLDER = "-";
constexpr char URMA_FIELD_DELIMITER = '|';
constexpr char FUNCTION_OPEN_BRACKET = '[';
constexpr char FUNCTION_CLOSE_BRACKET = ']';
constexpr char KEYWORD_DELIMITER = '`';
constexpr std::size_t URMA_HEADER_FIELD_COUNT = 5;
constexpr std::size_t URMA_MARKER_FIELD_INDEX = 0;
constexpr std::size_t URMA_LIBRARY_FIELD_INDEX = 1;
constexpr std::size_t URMA_FUNCTION_FIELD_INDEX = 4;
constexpr int SUCCESS_STATUS_CODE = 0;

bool ParseJsonFile(const std::filesystem::path &path, Json::Value &root)
{
    std::ifstream stream(path);
    if (!stream.is_open()) {
        LOG_ERROR << "failed to open failure mode data: " << path;
        return false;
    }
    Json::CharReaderBuilder builder;
    std::string errors;
    if (!Json::parseFromStream(builder, stream, &root, &errors)) {
        LOG_ERROR << "failed to parse failure mode data: " << path << ", error: " << errors;
        return false;
    }
    return true;
}

std::optional<std::string> ReadErrorCode(const Json::Value &item)
{
    const Json::Value &value = item[JSON_KEY_ERROR_CODE];
    if (value.isString()) {
        return value.asString();
    }
    if (value.isIntegral()) {
        return std::to_string(value.asInt64());
    }
    return std::nullopt;
}

bool ContainsIndex(const std::vector<std::size_t> &indices, std::size_t index)
{
    return std::find(indices.begin(), indices.end(), index) != indices.end();
}

bool IsErrorLevel(LevelOption level)
{
    return level == LevelOption::ERROR || level == LevelOption::FATAL;
}

bool ParseUrmaFunctionLocation(std::string_view location, std::string &functionName, int &lineNo)
{
    location = log_helper::TrimView(location);
    const std::size_t openBracket = location.rfind(FUNCTION_OPEN_BRACKET);
    const std::size_t closeBracket = location.rfind(FUNCTION_CLOSE_BRACKET);
    if (openBracket == std::string_view::npos || closeBracket != location.size() - 1 || openBracket == 0 ||
        openBracket + 1 >= closeBracket) {
        return false;
    }
    functionName = std::string(location.substr(0, openBracket));
    return log_helper::ParseInt(location.substr(openBracket + 1, closeBracket - openBracket - 1), lineNo);
}

bool ParseUrmaPipeMessage(std::string_view message, std::string &functionName, int &lineNo)
{
    // 一线嵌入日志格式：URMA|liburma|thread_id|thread_tag|function[line]|message
    std::array<std::string_view, URMA_HEADER_FIELD_COUNT> fields;
    std::size_t offset = 0;
    for (std::string_view &field : fields) {
        const std::size_t delimiter = message.find(URMA_FIELD_DELIMITER, offset);
        if (delimiter == std::string_view::npos) {
            return false;
        }
        field = log_helper::TrimView(message.substr(offset, delimiter - offset));
        offset = delimiter + 1;
    }
    return fields[URMA_MARKER_FIELD_INDEX] == URMA_LOG_MARKER && fields[URMA_LIBRARY_FIELD_INDEX] == URMA_LOG_KEYWORD &&
           ParseUrmaFunctionLocation(fields[URMA_FUNCTION_FIELD_INDEX], functionName, lineNo);
}

} // namespace

std::unique_ptr<DiagnosisEngine> DiagnosisEngine::Create(const std::filesystem::path &wittyDir)
{
    auto engine = std::make_unique<DiagnosisEngine>();
    if (!engine->LoadRules(wittyDir)) {
        return nullptr;
    }
    LOG_INFO << "loaded " << engine->rules_.size() << " data-driven KVCache/URMA failure mode rules";
    return engine;
}

bool DiagnosisEngine::LoadRules(const std::filesystem::path &wittyDir)
{
    rules_.clear();
    std::unordered_map<std::string, std::size_t> idToIndex;
    if (!LoadFailureModes(wittyDir / KVCACHE_FAILURE_MODE_PATH, FailureModeComponent::KVCACHE, idToIndex) ||
        !LoadFailureModes(wittyDir / URMA_FAILURE_MODE_PATH, FailureModeComponent::URMA, idToIndex)) {
        return false;
    }

    // 新知识库只描述已知状态码。保留旧实现的非零未知状态码兜底 ID，避免
    // 诊断结果静默丢失；兜底本身不参与 failure mode tree 的下探匹配。
    FailureModeDescriptor unknownDesc;
    unknownDesc.id = UNKNOWN_ACCESS_FAILURE_MODE_ID;
    unknownDesc.name = UNKNOWN_FAILURE_NAME;
    unknownDesc.phenomenon = UNKNOWN_FAILURE_PHENOMENON + std::string(UNKNOWN_STATUS_HINT);
    unknownDesc.cause = UNKNOWN_STATUS_HINT;
    unknownDesc.suggestion = UNKNOWN_STATUS_HINT;
    unknownDesc.filename = UNKNOWN_PLACEHOLDER;
    unknownDesc.functionName = UNKNOWN_PLACEHOLDER;
    unknownDesc.nodeType = FailureModeNodeType::ACCESS_LOG_ENTRY;
    Rule unknownRule;
    unknownRule.failureMode = std::make_shared<FailureMode>(std::move(unknownDesc));
    if (!idToIndex.emplace(unknownRule.failureMode->GetId(), rules_.size()).second) {
        LOG_ERROR << "reserved fallback failure mode id is duplicated: " << UNKNOWN_ACCESS_FAILURE_MODE_ID;
        return false;
    }
    rules_.push_back(std::move(unknownRule));

    if (!LoadFailureModeTree(wittyDir / FAILURE_MODE_TREE_PATH, idToIndex)) {
        return false;
    }
    return BuildIndices();
}

bool DiagnosisEngine::LoadFailureModes(const std::filesystem::path &path, FailureModeComponent component,
                                       std::unordered_map<std::string, std::size_t> &idToIndex)
{
    Json::Value root;
    if (!ParseJsonFile(path, root) || !root.isArray()) {
        LOG_ERROR << "failure mode data must be an array: " << path;
        return false;
    }
    for (Json::ArrayIndex index = 0; index < root.size(); ++index) {
        const Json::Value &item = root[index];
        const std::string id = item.get(JSON_KEY_FAILURE_ID, "").asString();
        const std::string name = item.get(JSON_KEY_FAILURE_NAME, "").asString();
        const std::string phenomenon = item.get(JSON_KEY_PHENOMENON, "").asString();
        const std::string filename = item.get(JSON_KEY_FILENAME, "").asString();
        const std::string functionName = item.get(JSON_KEY_FUNCTION_NAME, "").asString();
        if (id.empty() || name.empty() || phenomenon.empty() || filename.empty() || functionName.empty()) {
            LOG_ERROR << "invalid failure mode entry at " << path << ':' << index;
            return false;
        }
        if (idToIndex.count(id) != 0) {
            LOG_ERROR << "duplicate failure mode id: " << id;
            return false;
        }
        const auto nodeType = ResolveNodeType(item, component, phenomenon, path, index);
        if (!nodeType.has_value()) {
            return false;
        }
        FailureModeDescriptor desc;
        desc.id = id;
        desc.name = name;
        desc.phenomenon = phenomenon;
        desc.cause = item.get(JSON_KEY_CAUSE, "").asString();
        desc.suggestion = item.get(JSON_KEY_SOLUTION, "").asString();
        desc.filename = filename;
        desc.functionName = functionName;
        desc.errorCode = ReadErrorCode(item);
        desc.nodeType = *nodeType;
        Rule rule;
        rule.failureMode = std::make_shared<FailureMode>(std::move(desc));
        rule.keywords = ParseKeywords(phenomenon);
        rule.accessStatusCode = ParseNumericErrorCode(rule.failureMode->GetErrorCode());
        // Runtime rules without parsed keywords are never safe to match by
        // filename/function/level alone. This also protects historical data
        // that predates the structured log-match configuration.
        rule.logMatchEnabled = *nodeType != FailureModeNodeType::RUNTIME_LOG || !rule.keywords.empty();
        if (!ApplyLogMatchConfig(item, *nodeType, rule, path, index) ||
            !ApplyMatchCondition(item, *nodeType, rule, path, index)) {
            return false;
        }
        idToIndex.emplace(id, rules_.size());
        rules_.push_back(std::move(rule));
    }
    return true;
}

std::optional<FailureModeNodeType> DiagnosisEngine::ResolveNodeType(const Json::Value &item,
                                                                    FailureModeComponent component,
                                                                    const std::string &phenomenon,
                                                                    const std::filesystem::path &path,
                                                                    std::size_t index)
{
    if (component == FailureModeComponent::URMA) {
        return phenomenon.find(DOWNSTREAM_MATCH_MARKER) != std::string::npos ?
                   std::optional<FailureModeNodeType>(FailureModeNodeType::URMA_INTERFACE) :
                   std::optional<FailureModeNodeType>(FailureModeNodeType::URMA_FAILURE);
    }
    const std::string type = item.get(JSON_KEY_NODE_TYPE, "").asString();
    if (type == ACCESS_LOG_ENTRY_TYPE) {
        return FailureModeNodeType::ACCESS_LOG_ENTRY;
    }
    if (type == RUNTIME_LOG_TYPE) {
        return FailureModeNodeType::RUNTIME_LOG;
    }
    LOG_ERROR << "unknown KVCache failure mode node type at " << path << ':' << index << ": " << type;
    return std::nullopt;
}

bool DiagnosisEngine::ApplyLogMatchConfig(const Json::Value &item, FailureModeNodeType nodeType, Rule &rule,
                                          const std::filesystem::path &path, std::size_t index)
{
    const Json::Value &logMatch = item[JSON_KEY_LOG_MATCH];
    if (logMatch.isNull()) {
        return true;
    }
    if (nodeType != FailureModeNodeType::RUNTIME_LOG || !logMatch.isObject() || !logMatch[JSON_KEY_ENABLED].isBool()) {
        LOG_ERROR << "invalid runtime log match config at " << path << ':' << index;
        return false;
    }
    rule.logMatchEnabled = logMatch[JSON_KEY_ENABLED].asBool();
    if (!rule.logMatchEnabled &&
        (!logMatch[JSON_KEY_REASON].isString() || logMatch[JSON_KEY_REASON].asString().empty())) {
        LOG_ERROR << "disabled runtime log match config is missing reason at " << path << ':' << index;
        return false;
    }
    if (rule.keywords.empty() && rule.logMatchEnabled) {
        LOG_ERROR << "runtime rule without stable keywords cannot enable matching at " << path << ':' << index;
        return false;
    }
    return true;
}

bool DiagnosisEngine::ApplyMatchCondition(const Json::Value &item, FailureModeNodeType nodeType, Rule &rule,
                                          const std::filesystem::path &path, std::size_t index)
{
    const Json::Value &matchCondition = item[JSON_KEY_MATCH_CONDITION];
    if (matchCondition.isNull()) {
        return true;
    }
    if (nodeType != FailureModeNodeType::ACCESS_LOG_ENTRY || !matchCondition.isObject() ||
        !matchCondition[JSON_KEY_STATUS_CODE].isIntegral() || !matchCondition[JSON_KEY_RESP_MSG_NONEMPTY].isBool()) {
        LOG_ERROR << "invalid access match condition at " << path << ':' << index;
        return false;
    }
    rule.accessMatchCondition = AccessMatchCondition{
        matchCondition[JSON_KEY_STATUS_CODE].asInt(),
        matchCondition[JSON_KEY_RESP_MSG_NONEMPTY].asBool(),
    };
    return true;
}

bool DiagnosisEngine::LoadFailureModeTree(const std::filesystem::path &path,
                                          const std::unordered_map<std::string, std::size_t> &idToIndex)
{
    Json::Value root;
    if (!ParseJsonFile(path, root) || !root.isObject()) {
        LOG_ERROR << "failure mode tree must be an object: " << path;
        return false;
    }

    for (const char *moduleName : FAILURE_MODE_TREE_MODULES) {
        const Json::Value &module = root[moduleName];
        if (!module.isObject()) {
            LOG_ERROR << "failure mode tree is missing module: " << moduleName;
            return false;
        }
        for (const std::string &parentId : module.getMemberNames()) {
            auto parentIterator = idToIndex.find(parentId);
            if (parentIterator == idToIndex.end()) {
                LOG_ERROR << "failure mode tree references unknown parent: " << parentId;
                return false;
            }
            const Json::Value &children = module[parentId];
            if (!children.isArray()) {
                LOG_ERROR << "failure mode tree children must be an array: " << parentId;
                return false;
            }
            Rule &parent = rules_[parentIterator->second];
            for (const Json::Value &childValue : children) {
                if (!childValue.isString()) {
                    LOG_ERROR << "failure mode tree contains a non-string child under: " << parentId;
                    return false;
                }
                const std::string childId = childValue.asString();
                auto childIterator = idToIndex.find(childId);
                if (childIterator == idToIndex.end()) {
                    LOG_ERROR << "failure mode tree references unknown child: " << childId;
                    return false;
                }
                const std::size_t childIndex = childIterator->second;
                if (!ContainsIndex(parent.childIndices, childIndex)) {
                    parent.childIndices.push_back(childIndex);
                    rules_[childIndex].parentIndices.push_back(parentIterator->second);
                }
            }
        }
    }
    return true;
}

bool DiagnosisEngine::BuildIndices()
{
    accessStatusToRuleIndex_.clear();
    conditionalAccessRuleIndices_.clear();
    unknownAccessRuleIndex_.reset();
    runtimeRootIndices_.clear();
    kvcacheFilenameToRuleIndices_.clear();
    urmaFunctionToRuleIndices_.clear();
    std::size_t disabledRuntimeRuleCount = 0;

    for (std::size_t index = 0; index < rules_.size(); ++index) {
        if (!RegisterRuleIndex(index, disabledRuntimeRuleCount)) {
            return false;
        }
    }
    if (accessStatusToRuleIndex_.empty() || conditionalAccessRuleIndices_.empty() ||
        !unknownAccessRuleIndex_.has_value() || kvcacheFilenameToRuleIndices_.empty() ||
        urmaFunctionToRuleIndices_.empty()) {
        LOG_ERROR << "failure mode data did not produce all required KVCache/URMA rule indices";
        return false;
    }
    if (disabledRuntimeRuleCount > 0) {
        LOG_WARN << "ignored " << disabledRuntimeRuleCount << " runtime failure modes without stable log keywords";
    }
    ResetResult();
    return true;
}

bool DiagnosisEngine::RegisterRuleIndex(std::size_t index, std::size_t &disabledRuntimeRuleCount)
{
    Rule &rule = rules_[index];
    const auto &mode = rule.failureMode;
    const FailureModeNodeType nodeType = mode->GetNodeType();
    const bool unreachable = rule.parentIndices.empty() && (nodeType == FailureModeNodeType::RUNTIME_LOG ||
                                                            nodeType == FailureModeNodeType::URMA_FAILURE);
    if (unreachable) {
        LOG_ERROR << "directly matchable failure mode is unreachable in failure_mode_tree: " << mode->GetId();
        return false;
    }
    if (nodeType == FailureModeNodeType::ACCESS_LOG_ENTRY) {
        if (mode->GetId() == UNKNOWN_ACCESS_FAILURE_MODE_ID) {
            unknownAccessRuleIndex_ = index;
        } else if (rule.accessMatchCondition.has_value()) {
            conditionalAccessRuleIndices_.push_back(index);
        } else if (rule.accessStatusCode.has_value()) {
            if (!accessStatusToRuleIndex_.emplace(*rule.accessStatusCode, index).second) {
                LOG_ERROR << "duplicate KVCache access status code: " << *rule.accessStatusCode;
                return false;
            }
        } else {
            runtimeRootIndices_.push_back(index);
        }
    } else if (nodeType == FailureModeNodeType::RUNTIME_LOG) {
        if (rule.logMatchEnabled) {
            kvcacheFilenameToRuleIndices_[Basename(mode->GetFilename())].push_back(index);
        } else {
            ++disabledRuntimeRuleCount;
        }
    } else if (nodeType == FailureModeNodeType::URMA_FAILURE) {
        urmaFunctionToRuleIndices_[mode->GetFunctionName()].push_back(index);
    }
    return true;
}

void DiagnosisEngine::ResetResult()
{
    controllers_.clear();
    traceLogs_.clear();
    hitRoots_.clear();
    for (const Rule &rule : rules_) {
        const std::string &id = rule.failureMode->GetId();
        controllers_.emplace(id, FailureModeController(rule.failureMode));
    }
}

bool DiagnosisEngine::RunDiagnosis(const std::vector<std::string> &accessLogPaths,
                                   const std::vector<std::string> &runtimeLogPaths)
{
    ResetResult();
    std::unordered_map<std::string, TraceContext> traces;
    if (!AnalyzeAccessLogs(accessLogPaths, traces)) {
        return false;
    }

    std::vector<RuntimeRecord> runtimeRecords;
    if (!ReadRuntimeLogs(runtimeLogPaths, runtimeRecords)) {
        return false;
    }
    SeedRuntimeRoots(runtimeRecords, traces);
    AnalyzeKvcacheRuntime(runtimeRecords, traces);
    AnalyzeUrmaRuntime(runtimeRecords, traces);

    for (auto &[traceId, logs] : traceLogs_) {
        std::stable_sort(logs.begin(), logs.end(), [](const auto &left, const auto &right) {
            return std::tie(left->timestamp, left->rawLog) < std::tie(right->timestamp, right->rawLog);
        });
    }
    LOG_INFO << "diagnosed " << traceLogs_.size() << " failure traces from " << accessLogPaths.size()
             << " access log files and " << runtimeLogPaths.size() << " runtime/URMA log files";
    return true;
}

bool DiagnosisEngine::AnalyzeAccessLogs(const std::vector<std::string> &paths,
                                        std::unordered_map<std::string, TraceContext> &traces)
{
    std::vector<std::string> sortedPaths = paths;
    std::sort(sortedPaths.begin(), sortedPaths.end());
    for (const std::string &path : sortedPaths) {
        std::ifstream stream(path);
        if (!stream.is_open()) {
            LOG_ERROR << "failed to open access log: " << path;
            return false;
        }
        std::string line;
        while (std::getline(stream, line)) {
            std::shared_ptr<FailureLogInfoAccess> log;
            if (!ParseAccessLog(line, log) || log->traceId.empty()) {
                continue;
            }
            const std::optional<std::size_t> ruleIndex = ResolveAccessRule(*log);
            if (!ruleIndex.has_value() || IsAccessLocationMismatch(*ruleIndex, *log)) {
                continue;
            }
            traces[log->traceId].rootIndices.insert(*ruleIndex);
            hitRoots_.insert(rules_[*ruleIndex].failureMode->GetId());
            RecordHit(*ruleIndex, log);
        }
        if (stream.bad()) {
            LOG_ERROR << "failed while reading access log: " << path;
            return false;
        }
    }
    return true;
}

std::optional<std::size_t> DiagnosisEngine::ResolveAccessRule(const FailureLogInfoAccess &log) const
{
    for (std::size_t index : conditionalAccessRuleIndices_) {
        const AccessMatchCondition &condition = *rules_[index].accessMatchCondition;
        if (log.statusCode == condition.statusCode && (!condition.respMsgNonempty || !log.respMsg.empty())) {
            return index;
        }
    }
    auto statusIterator = accessStatusToRuleIndex_.find(log.statusCode);
    if (statusIterator != accessStatusToRuleIndex_.end()) {
        return statusIterator->second;
    }
    if (log.statusCode != SUCCESS_STATUS_CODE) {
        LOG_WARN << UNKNOWN_STATUS_HINT << ", status_code=" << log.statusCode;
        return unknownAccessRuleIndex_;
    }
    return std::nullopt;
}

bool DiagnosisEngine::IsAccessLocationMismatch(std::size_t ruleIndex, const FailureLogInfoAccess &log) const
{
    if (ruleIndex == unknownAccessRuleIndex_) {
        return false;
    }
    const FailureMode &mode = *rules_[ruleIndex].failureMode;
    if (Basename(log.filename) != Basename(mode.GetFilename())) {
        return true;
    }
    return !log.functionName.empty() && log.functionName != mode.GetFunctionName();
}

bool DiagnosisEngine::ReadRuntimeLogs(const std::vector<std::string> &paths, std::vector<RuntimeRecord> &records) const
{
    std::vector<std::string> sortedPaths = paths;
    std::sort(sortedPaths.begin(), sortedPaths.end());
    for (const std::string &path : sortedPaths) {
        std::ifstream stream(path);
        if (!stream.is_open()) {
            LOG_ERROR << "failed to open runtime log: " << path;
            return false;
        }
        std::string line;
        while (std::getline(stream, line)) {
            RuntimeRecord record;
            if (ParseRuntimeRecord(line, record)) {
                records.push_back(std::move(record));
            }
        }
        if (stream.bad()) {
            LOG_ERROR << "failed while reading runtime log: " << path;
            return false;
        }
    }
    std::stable_sort(records.begin(), records.end(), [](const RuntimeRecord &left, const RuntimeRecord &right) {
        return std::tie(left.log->timestamp, left.log->rawLog) < std::tie(right.log->timestamp, right.log->rawLog);
    });
    return true;
}

void DiagnosisEngine::SeedRuntimeRoots(const std::vector<RuntimeRecord> &records,
                                       std::unordered_map<std::string, TraceContext> &traces)
{
    for (const RuntimeRecord &record : records) {
        if (record.urma || record.log->traceId.empty()) {
            continue;
        }
        std::optional<std::size_t> bestIndex;
        std::size_t bestSpecificity = 0;
        for (std::size_t index : runtimeRootIndices_) {
            const Rule &rule = rules_[index];
            if (Basename(record.log->filename) != Basename(rule.failureMode->GetFilename())) {
                continue;
            }
            std::size_t specificity = 0;
            if (!RuleMatches(rule, *record.log, record.log->message, specificity)) {
                continue;
            }
            if (!bestIndex.has_value() || specificity > bestSpecificity ||
                (specificity == bestSpecificity && index < *bestIndex)) {
                bestIndex = index;
                bestSpecificity = specificity;
            }
        }
        if (!bestIndex.has_value()) {
            continue;
        }
        traces[record.log->traceId].rootIndices.insert(*bestIndex);
        hitRoots_.insert(rules_[*bestIndex].failureMode->GetId());
        RecordHit(*bestIndex, record.log);
    }
}

void DiagnosisEngine::AnalyzeKvcacheRuntime(const std::vector<RuntimeRecord> &records,
                                            std::unordered_map<std::string, TraceContext> &traces)
{
    // KVCache runtime 日志必带 trace_id：每条 ERROR 日志都应绑定命中的全部故障
    // 模式，不要求 trace 先被 access 根种下，也不按根的子节点集合过滤。
    for (const RuntimeRecord &record : records) {
        if (record.urma) {
            continue;
        }
        auto candidatesIterator = kvcacheFilenameToRuleIndices_.find(Basename(record.log->filename));
        if (candidatesIterator == kvcacheFilenameToRuleIndices_.end()) {
            continue;
        }

        // message 可能拼接多个日志的内容：命中几条规则就记录几条，同一物理日志
        // 可绑定多个 runtime 故障模式。
        const RuleIndices matched =
            SelectMatchingRules(candidatesIterator->second, nullptr, *record.log, record.log->message);
        if (matched.empty()) {
            continue;
        }
        TraceContext *trace = nullptr;
        if (!record.log->traceId.empty()) {
            trace = &traces[record.log->traceId];
        }
        for (std::size_t matchedIndex : matched) {
            if (trace != nullptr) {
                trace->kvcacheRuntimeIndices.insert(matchedIndex);
            }
            RecordHit(matchedIndex, record.log);
        }
    }
    ActivateKvcachePaths(traces);
}

void DiagnosisEngine::ActivateKvcachePaths(const std::unordered_map<std::string, TraceContext> &traces)
{
    // 在同一 trace 的全部 runtime 日志完成匹配后再激活边，避免结果依赖父子日志
    // 的输出顺序。逐一激活命中节点之间的相邻 DAG 边，视图层即可递归展示任意深度。
    for (const auto &entry : traces) {
        const TraceContext &trace = entry.second;
        auto activateMatchedChildren = [&](std::size_t parentIndex) {
            for (std::size_t childIndex : rules_[parentIndex].childIndices) {
                if (trace.kvcacheRuntimeIndices.find(childIndex) != trace.kvcacheRuntimeIndices.end()) {
                    ActivateEdge(parentIndex, childIndex);
                }
            }
        };
        for (std::size_t rootIndex : trace.rootIndices) {
            activateMatchedChildren(rootIndex);
        }
        for (std::size_t runtimeIndex : trace.kvcacheRuntimeIndices) {
            activateMatchedChildren(runtimeIndex);
        }
    }
}

void DiagnosisEngine::AnalyzeUrmaRuntime(const std::vector<RuntimeRecord> &records,
                                         const std::unordered_map<std::string, TraceContext> &traces)
{
    for (const RuntimeRecord &record : records) {
        if (!record.urma || record.log->traceId.empty()) {
            continue;
        }
        auto traceIterator = traces.find(record.log->traceId);
        if (traceIterator == traces.end()) {
            continue;
        }
        auto functionIterator = urmaFunctionToRuleIndices_.find(record.matchFunctionName);
        if (functionIterator == urmaFunctionToRuleIndices_.end()) {
            continue;
        }

        const InterfaceToAnchors interfaceToAnchors = CollectUrmaInterfaces(traceIterator->second);
        const RuleIndexSet allowed = CollectUrmaFailureRules(interfaceToAnchors);
        auto urmaLog = std::make_shared<FailureLogInfoRuntime>(*record.log);
        urmaLog->failureModeIds.clear();
        urmaLog->functionName = record.matchFunctionName;
        urmaLog->message = record.matchMessage;
        const auto matched = SelectBestRule(functionIterator->second, allowed, *urmaLog, record.matchMessage);
        if (!matched.has_value()) {
            continue;
        }
        ActivateUrmaPath(*matched, interfaceToAnchors);
        RecordHit(*matched, urmaLog);
    }
}

DiagnosisEngine::InterfaceToAnchors DiagnosisEngine::CollectUrmaInterfaces(const TraceContext &trace) const
{
    InterfaceToAnchors interfaceToAnchors;
    auto collect = [&interfaceToAnchors, this](std::size_t anchorIndex) {
        for (std::size_t childIndex : rules_[anchorIndex].childIndices) {
            if (rules_[childIndex].failureMode->GetNodeType() == FailureModeNodeType::URMA_INTERFACE) {
                interfaceToAnchors[childIndex].push_back(anchorIndex);
            }
        }
    };
    for (std::size_t rootIndex : trace.rootIndices) {
        collect(rootIndex);
    }
    for (std::size_t runtimeIndex : trace.kvcacheRuntimeIndices) {
        collect(runtimeIndex);
    }
    return interfaceToAnchors;
}

DiagnosisEngine::RuleIndexSet DiagnosisEngine::CollectUrmaFailureRules(
    const InterfaceToAnchors &interfaceToAnchors) const
{
    RuleIndexSet failureRules;
    for (const auto &entry : interfaceToAnchors) {
        const std::size_t interfaceIndex = entry.first;
        for (std::size_t childIndex : rules_[interfaceIndex].childIndices) {
            if (rules_[childIndex].failureMode->GetNodeType() == FailureModeNodeType::URMA_FAILURE) {
                failureRules.insert(childIndex);
            }
        }
    }
    return failureRules;
}

void DiagnosisEngine::ActivateUrmaPath(std::size_t failureIndex, const InterfaceToAnchors &interfaceToAnchors)
{
    for (const auto &[interfaceIndex, anchors] : interfaceToAnchors) {
        if (!ContainsIndex(rules_[interfaceIndex].childIndices, failureIndex)) {
            continue;
        }
        for (std::size_t anchorIndex : anchors) {
            ActivateEdge(anchorIndex, interfaceIndex);
        }
        ActivateEdge(interfaceIndex, failureIndex);
    }
}

std::optional<std::size_t> DiagnosisEngine::SelectBestRule(const RuleIndices &candidates,
                                                           const std::unordered_set<std::size_t> &allowed,
                                                           const FailureLogInfoRuntime &log,
                                                           const std::string &message) const
{
    const RuleIndices matched = SelectMatchingRules(candidates, &allowed, log, message);
    return matched.empty() ? std::nullopt : std::optional<std::size_t>(matched.front());
}

DiagnosisEngine::RuleIndices DiagnosisEngine::SelectMatchingRules(const RuleIndices &candidates,
                                                                  const RuleIndexSet *allowed,
                                                                  const FailureLogInfoRuntime &log,
                                                                  const std::string &message) const
{
    // KVCache 单行日志的 message 可能拼接多个日志的内容，一条物理日志允许命中多个
    // 故障模式。返回全部命中规则，按（特异度降序，规则序号升序）排序，最具体者在首。
    // allowed 为空指针时不限制候选（runtime 层无条件全量匹配）。
    std::vector<std::pair<std::size_t, std::size_t>> matched; // (specificity, index)
    for (std::size_t index : candidates) {
        if (allowed != nullptr && allowed->find(index) == allowed->end()) {
            continue;
        }
        std::size_t specificity = 0;
        if (!RuleMatches(rules_[index], log, message, specificity)) {
            continue;
        }
        matched.emplace_back(specificity, index);
    }
    std::sort(matched.begin(), matched.end(), [](const auto &left, const auto &right) {
        if (left.first != right.first) {
            return left.first > right.first;
        }
        return left.second < right.second;
    });
    RuleIndices result;
    result.reserve(matched.size());
    for (const auto &entry : matched) {
        result.push_back(entry.second);
    }
    return result;
}

bool DiagnosisEngine::RuleMatches(const Rule &rule, const FailureLogInfoRuntime &log, const std::string &message,
                                  std::size_t &specificity) const
{
    if (!rule.logMatchEnabled) {
        return false;
    }
    const FailureMode &mode = *rule.failureMode;
    if (mode.GetNodeType() == FailureModeNodeType::URMA_FAILURE) {
        // 一线 URMA 嵌入日志只携带 function[line]，不携带源文件名。
        if (log.functionName != mode.GetFunctionName()) {
            return false;
        }
    } else {
        if (Basename(log.filename) != Basename(mode.GetFilename())) {
            return false;
        }
        if (!log.functionName.empty() && log.functionName != mode.GetFunctionName()) {
            return false;
        }
    }
    if (rule.keywords.empty()) {
        const bool fatalRuntimeEntry = mode.IsAccessEntry() &&
                                       mode.GetPhenomenon().find(FATAL_LEVEL_MARKER) != std::string::npos;
        if (mode.IsPublicInterface() || !IsErrorLevel(log.level) ||
            (fatalRuntimeEntry && log.level != LevelOption::FATAL)) {
            return false;
        }
        specificity = mode.GetFilename().size() + mode.GetFunctionName().size();
        return true;
    }

    std::size_t offset = 0;
    specificity = 0;
    for (const std::string &keyword : rule.keywords) {
        offset = message.find(keyword, offset);
        if (offset == std::string::npos) {
            return false;
        }
        offset += keyword.size();
        specificity += keyword.size();
    }
    return true;
}

void DiagnosisEngine::RecordHit(std::size_t ruleIndex, const std::shared_ptr<FailureLogInfo> &log)
{
    const std::string &failureModeId = rules_[ruleIndex].failureMode->GetId();
    if (std::find(log->failureModeIds.begin(), log->failureModeIds.end(), failureModeId) == log->failureModeIds.end()) {
        log->BindFailureMode(failureModeId);
    }
    controllers_.at(failureModeId).Hit(log->traceId, log);
    auto &trace = traceLogs_[log->traceId];
    if (std::find(trace.begin(), trace.end(), log) == trace.end()) {
        trace.push_back(log);
    }
}

void DiagnosisEngine::ActivateEdge(std::size_t parentIndex, std::size_t childIndex)
{
    controllers_.at(rules_[parentIndex].failureMode->GetId())
        .InsertSubValidFailureModeId(rules_[childIndex].failureMode->GetId());
}

std::vector<std::string> DiagnosisEngine::ParseKeywords(const std::string &phenomenon)
{
    std::vector<std::string> keywords;
    if (phenomenon.find(DOWNSTREAM_MATCH_MARKER) != std::string::npos) {
        return keywords;
    }
    std::size_t offset = 0;
    while (offset < phenomenon.size()) {
        const std::size_t begin = phenomenon.find(KEYWORD_DELIMITER, offset);
        if (begin == std::string::npos) {
            break;
        }
        const std::size_t end = phenomenon.find(KEYWORD_DELIMITER, begin + 1);
        if (end == std::string::npos) {
            break;
        }
        const std::string keyword = phenomenon.substr(begin + 1, end - begin - 1);
        if (!keyword.empty()) {
            keywords.push_back(keyword);
        }
        offset = end + 1;
    }
    return keywords;
}

std::optional<int> DiagnosisEngine::ParseNumericErrorCode(const std::optional<std::string> &errorCode)
{
    if (!errorCode.has_value()) {
        return std::nullopt;
    }
    std::string_view value(*errorCode);
    const std::size_t open = value.rfind('(');
    const std::size_t close = value.rfind(')');
    if (open != std::string_view::npos && close == value.size() - 1 && open + 1 < close) {
        value = value.substr(open + 1, close - open - 1);
    }
    int parsed = 0;
    if (!log_helper::ParseInt(value, parsed)) {
        return std::nullopt;
    }
    return parsed;
}

bool DiagnosisEngine::ParseAccessLog(const std::string &line, std::shared_ptr<FailureLogInfoAccess> &log)
{
    std::vector<std::string_view> views;
    log_helper::SplitView(views, line, log_helper::DELIM, true);
    if (views.size() != ACCESS_FIELDS_SIZE) {
        return false;
    }
    try {
        log = std::make_shared<FailureLogInfoAccess>(log_helper::ToStringFields(views), line);
        return true;
    } catch (const std::exception &exception) {
        LOG_WARN << "skipping invalid access log: " << exception.what();
        return false;
    }
}

bool DiagnosisEngine::ParseRuntimeRecord(const std::string &line, RuntimeRecord &record)
{
    std::vector<std::string_view> views;
    log_helper::SplitView(views, line, log_helper::DELIM, true);
    if (views.size() != RUNTIME_FIELDS_SIZE) {
        return false;
    }
    try {
        record.log = std::make_shared<FailureLogInfoRuntime>(log_helper::ToStringFields(views), line);
    } catch (const std::exception &exception) {
        LOG_WARN << "skipping invalid runtime log: " << exception.what();
        return false;
    }
    record.matchFunctionName = record.log->functionName;
    record.matchMessage = record.log->message;

    if (line.find(URMA_LOG_KEYWORD) == std::string::npos) {
        return true;
    }
    // 命中 liburma 后即锁定日志类型。即使内层字段损坏，也不能回退到
    // KVCache runtime 匹配而造成同一条物理日志跨类型命中。
    record.urma = true;
    int urmaLineNo = 0;
    if (!ParseUrmaPipeMessage(record.log->message, record.matchFunctionName, urmaLineNo)) {
        return true;
    }
    return true;
}

std::string DiagnosisEngine::Basename(const std::string &path)
{
    const std::size_t separator = path.find_last_of("/\\");
    return separator == std::string::npos ? path : path.substr(separator + 1);
}

const DiagnosisEngine::ControllerMap &DiagnosisEngine::GetControllers() const
{
    return controllers_;
}
const DiagnosisEngine::TraceLogMap &DiagnosisEngine::GetTraceLogs() const
{
    return traceLogs_;
}
const std::unordered_set<std::string> &DiagnosisEngine::GetHitRoots() const
{
    return hitRoots_;
}

} // namespace diag
