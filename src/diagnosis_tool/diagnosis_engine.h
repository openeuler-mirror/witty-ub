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

#ifndef DIAGNOSIS_ENGINE_H
#define DIAGNOSIS_ENGINE_H

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <iosfwd>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "failure_log_info.h"
#include "failure_mode_controller.h"

#include <json/json.h>

namespace diag {

class DiagnosisEngine final {
public:
    using ControllerMap = std::unordered_map<std::string, FailureModeController>;
    using TraceLogMap = std::unordered_map<std::string, std::vector<std::shared_ptr<FailureLogInfo>>>;

    static std::unique_ptr<DiagnosisEngine> Create(const std::filesystem::path &wittyDir);

    bool RunDiagnosis(const std::vector<std::string> &accessLogPaths, const std::vector<std::string> &runtimeLogPaths);
    void BeginDiagnosis();
    void AnalyzeAccessLine(std::string_view line);
    void AnalyzeRuntimeLine(std::string_view line);
    void AnalyzeRuntimeLines(const std::vector<std::string_view> &lines);
    void FinishDiagnosis(std::size_t accessFileCount, std::size_t runtimeFileCount);

    const ControllerMap &GetControllers() const;
    const TraceLogMap &GetTraceLogs() const;
    const std::unordered_set<std::string> &GetHitRoots() const;

private:
    struct AccessMatchCondition {
        int statusCode;
        bool respMsgNonempty;
    };

    struct Rule {
        std::shared_ptr<FailureMode> failureMode;
        std::string filenameBasename;
        std::vector<std::string> keywords;
        std::vector<std::size_t> childIndices;
        std::vector<std::size_t> parentIndices;
        std::optional<int> accessStatusCode;
        std::optional<AccessMatchCondition> accessMatchCondition;
        bool logMatchEnabled = true;
    };

    struct RuntimeRecord {
        std::shared_ptr<FailureLogInfoRuntime> log;
        std::string matchFunctionName;
        std::string matchMessage;
        bool urma = false;
    };

    struct RuntimeMatchView {
        std::string_view filenameBasename;
        std::string_view functionName;
        std::string_view traceId;
        std::string_view message;
        std::optional<LevelOption> level;
    };

    struct KvcacheMatchRecord {
        std::shared_ptr<FailureLogInfoRuntime> log;
        std::vector<std::size_t> matchedIndices;
    };

    struct RuntimeMatchBatch {
        std::vector<KvcacheMatchRecord> kvcacheRecords;
        std::vector<std::string> urmaLines;
    };

    struct TraceContext {
        std::unordered_set<std::size_t> rootIndices;
        std::unordered_set<std::size_t> kvcacheRuntimeIndices;
    };

    using RuleIndices = std::vector<std::size_t>;
    using RuleIndexSet = std::unordered_set<std::size_t>;
    using FilenameToRuleIndices = std::unordered_map<std::string_view, RuleIndices>;
    using FunctionViewToRuleIndices = std::unordered_map<std::string_view, RuleIndices>;
    using FilenameFunctionToRuleIndices = std::unordered_map<std::string_view, FunctionViewToRuleIndices>;
    using FunctionToRuleIndices = std::unordered_map<std::string, RuleIndices>;
    using InterfaceToAnchors = std::unordered_map<std::size_t, RuleIndices>;

    bool LoadRules(const std::filesystem::path &wittyDir);
    bool LoadRuleCache(const std::filesystem::path &wittyDir);
    bool ValidateCacheStamps(std::istream &stream, const std::filesystem::path &wittyDir) const;
    bool LoadCacheRules(std::istream &stream, std::vector<Rule> &loadedRules, std::uint64_t ruleCount) const;
    bool LoadOneCacheRule(std::istream &stream, Rule &rule) const;
    bool LoadCacheRuleKeywords(std::istream &stream, Rule &rule) const;
    bool LoadCacheRuleConditions(std::istream &stream, Rule &rule) const;
    bool ValidateCacheIndices(const std::vector<Rule> &loadedRules, std::uint64_t ruleCount) const;
    void SaveRuleCache(const std::filesystem::path &wittyDir) const;
    bool WriteOneCacheRule(std::ostream &stream, const Rule &rule) const;
    bool LoadFailureModes(const std::filesystem::path &path, FailureModeComponent component,
                          std::unordered_map<std::string, std::size_t> &idToIndex);
    bool LoadFailureModeTree(const std::filesystem::path &path,
                             const std::unordered_map<std::string, std::size_t> &idToIndex);
    std::optional<FailureModeNodeType> ResolveNodeType(const Json::Value &item, FailureModeComponent component,
                                                       const std::string &phenomenon, const std::filesystem::path &path,
                                                       std::size_t index);
    bool ApplyLogMatchConfig(const Json::Value &item, FailureModeNodeType nodeType, Rule &rule,
                             const std::filesystem::path &path, std::size_t index);
    bool ApplyMatchCondition(const Json::Value &item, FailureModeNodeType nodeType, Rule &rule,
                             const std::filesystem::path &path, std::size_t index);
    bool BuildIndices();
    bool RegisterRuleIndex(std::size_t index, std::size_t &disabledRuntimeRuleCount);
    void ResetResult();

    bool AnalyzeAccessLogs(const std::vector<std::string> &paths);
    std::optional<std::size_t> ResolveAccessRule(const FailureLogInfoAccess &log) const;
    bool IsAccessLocationMismatch(std::size_t ruleIndex, const FailureLogInfoAccess &log) const;
    bool AnalyzeRuntimeLogs(const std::vector<std::string> &paths);
    void MatchRuntimeLine(std::string_view line, RuntimeMatchBatch &batch) const;
    RuleIndices MatchKvcacheRuntime(const RuntimeMatchView &view) const;
    void RecordKvcacheMatches(std::vector<KvcacheMatchRecord> &records,
                              std::unordered_map<std::string, TraceContext> &traces);
    void ActivateKvcachePaths(const std::unordered_map<std::string, TraceContext> &traces);
    void AnalyzeUrmaRuntime(const std::vector<std::string> &candidateLines,
                            const std::unordered_map<std::string, TraceContext> &traces);
    InterfaceToAnchors CollectUrmaInterfaces(const TraceContext &trace) const;
    RuleIndexSet CollectUrmaFailureRules(const InterfaceToAnchors &interfaceToAnchors) const;
    void ActivateUrmaPath(std::size_t failureIndex, const InterfaceToAnchors &interfaceToAnchors);

    std::optional<std::size_t> SelectBestRule(const RuleIndices &candidates,
                                              const std::unordered_set<std::size_t> &allowed,
                                              const FailureLogInfoRuntime &log, const std::string &message) const;
    RuleIndices SelectMatchingRules(const RuleIndices &candidates, const RuleIndexSet *allowed,
                                    const FailureLogInfoRuntime &log, const std::string &message) const;
    RuleIndices SelectMatchingRules(const RuleIndices &candidates, const RuntimeMatchView &view) const;
    bool RuleMatches(const Rule &rule, const FailureLogInfoRuntime &log, const std::string &message,
                     std::size_t &specificity) const;
    bool RuleMatches(const Rule &rule, const RuntimeMatchView &view, std::size_t &specificity) const;
    void RecordHit(std::size_t ruleIndex, const std::shared_ptr<FailureLogInfo> &log);
    void ActivateEdge(std::size_t parentIndex, std::size_t childIndex);

    static std::vector<std::string> ParseKeywords(const std::string &phenomenon);
    static std::optional<int> ParseNumericErrorCode(const std::optional<std::string> &errorCode);
    static bool ParseRuntimeRecord(const std::string &line, RuntimeRecord &record);
    static bool ParseRuntimeMatchView(std::string_view line, RuntimeMatchView &view);
    static bool ParseAccessLog(const std::string &line, std::shared_ptr<FailureLogInfoAccess> &log);
    static std::string Basename(const std::string &path);
    static std::string_view BasenameView(std::string_view path);

    std::vector<Rule> rules_;
    std::unordered_map<int, std::size_t> accessStatusToRuleIndex_;
    RuleIndices conditionalAccessRuleIndices_;
    std::optional<std::size_t> unknownAccessRuleIndex_;
    FilenameToRuleIndices kvcacheFilenameToRuleIndices_;
    FilenameFunctionToRuleIndices kvcacheLocationToRuleIndices_;
    FunctionToRuleIndices urmaFunctionToRuleIndices_;

    ControllerMap controllers_;
    TraceLogMap traceLogs_;
    std::unordered_set<std::string> hitRoots_;
    std::unordered_map<std::string, TraceContext> diagnosisTraces_;
    // Views reference diagnosisTraces_ keys and must be cleared before that map.
    std::unordered_set<std::string_view> accessTraceIds_;
    std::vector<KvcacheMatchRecord> pendingKvcacheRecords_;
    std::vector<std::string> pendingUrmaLines_;
};

} // namespace diag

#endif // DIAGNOSIS_ENGINE_H
