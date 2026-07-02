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

#define MODULE_NAME "DIAGNOSIS"

#include "diagnosis_tool_module.h"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string_view>
#include <unordered_set>

#include <json/json.h>
#include <re2/re2.h>

#include "failure_def.h"
#include "failure_log_helper.h"
#include "failure_mode_factory.h"
#include "failure_mode_view.h"
#include "logger.h"
#include "ubse_context.h"

namespace diag {
using namespace ubse::context;
namespace fs = std::filesystem;

constexpr const char *LOG_TYPE_ACCESS = "access";
constexpr const char *LOG_TYPE_RUNTIME = "runtime";
constexpr const char *MODULE_KVCACHE = "kvcache_conn";
constexpr const char *MODULE_URMA = "urma";
constexpr const char *TIME_PATTERN = R"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})";
constexpr const char *DEFAULT_WITTY_DIR = "/var/witty-ub";
constexpr const char *FAILURE_MODE_TREE_JSON_PATH = "data/failure_mode_tree.json";
constexpr mode_t DIR_PERM_755 = 0755;
constexpr const char *URMA_LOG_KEYWORD = "liburma";
constexpr const char *OUTPUT_FILENAME_FAILURE_TRACE = "failure_trace.log";

// 此类故障模式，第一轮需要下探，第二轮需跳过（硬编码感觉不太好）
const std::unordered_set<int> KVCACHE_FAILURE_002_STATUSCODE = {2, 3, 8};

DiagnosisToolModule::DiagnosisToolModule() {}

RackResult DiagnosisToolModule::Initialize()
{
    if (ParseDiagArgs() != RACK_OK) {
        return RACK_FAIL;
    }
    if (ConfigureMergedPath() != RACK_OK) {
        return RACK_FAIL;
    }
    if (ExtractLogsByTimeWindow() != RACK_OK) {
        return RACK_FAIL;
    }
    if (SetEnvVars() != RACK_OK) {
        return RACK_FAIL;
    }
    if (BuildFailureModeTree() != RACK_OK) {
        return RACK_FAIL;
    }
    return RACK_OK;
}

void DiagnosisToolModule::UnInitialize()
{
    LOG_INFO << "DiagnosisToolModule uninitialized";
}

RackResult DiagnosisToolModule::Start()
{
    // 0. 预填写日志类型->文件路径表
    if (BuildLogTypeToPathMap() != RACK_OK) {
        return RACK_FAIL;
    }
    // 1. 对接口日志，筛选statusCode非0，或为0且respMsg不为空的行，建立索引并顺带解析以下故障模式：kvcache_0xy 和 kvcache_002_00x
    if (AnalyzeAccessLogs() != RACK_OK) {
        return RACK_FAIL;
    }
    // 2. 对运行日志，筛选被故障trace id命中的行（urma还会有别的关键字），识别剩下的kvcache故障和所有urma故障
    if (AnalyzeRuntimeLogs() != RACK_OK) {
        return RACK_FAIL;
    }
    /**
     *  3. 已得到完整的traceIdToFailureLogInfos_（一条trace对应的所有failure log info）
     *     有以下三种情况，"[·, ·]"表示属于同一个failure log info，"· -> ·"表示两个failure log info的关系
     *      a). [kvcache_002, kvcache_002_00x]
     *      b). kvcache_006 -> kvcache_006_00x
     *      c). kvcache_028 -> kvcache_028_00x -> urma_yyy -> ...
     *     基于step 1和step 2对故障模式遍历的方式，kvcache部分已天然有序，urma部分在上一步也手动排序
     *     这一步要得到一个trace id对应的一连串故障模式，以及将trace id命中的故障模式之间的父子关系补全到failureModeIdToController_
     */
    if (MergeFailureModeByTraceId() != RACK_OK) {
        return RACK_FAIL;
    }

    if (StoreFailureTraces() != RACK_OK) {
        return RACK_FAIL;
    }
    if (GenerateFailureModeView() != RACK_OK) {
        return RACK_FAIL;
    }
    return RACK_OK;
}

void DiagnosisToolModule::Stop()
{
    LOG_INFO << "DiagnosisToolModule stopped";
}

RackResult DiagnosisToolModule::ParseDiagArgs()
{
    const auto &argMap = UbseContext::GetInstance().GetArgMap();
    auto getRequired = [&](const std::string &key, std::string &value) -> RackResult {
        auto it = argMap.find(key);
        if (it == argMap.end()) {
            LOG_ERROR << "Missing required argument: --" << key;
            return RACK_FAIL;
        }
        value = it->second;
        return RACK_OK;
    };
    if (getRequired("ds-log-path", dsLogPath_) != RACK_OK) {
        LOG_ERROR << "--ds-log-path must not be empty";
        return RACK_FAIL;
    }
    if (dsLogPath_.empty() || !fs::exists(dsLogPath_) || !fs::is_directory(dsLogPath_)) {
        LOG_WARN << "--ds-log-path must be an existing directory: " << dsLogPath_;
        return RACK_FAIL;
    }

    if (getRequired("ds-client-access-log-file", dsClientAccessLogFile_) != RACK_OK || dsClientAccessLogFile_.empty()) {
        LOG_WARN << "--ds-client-access-log-file is empty";
    }
    if (getRequired("ds-client-info-log-file", dsClientInfoLogFile_) != RACK_OK || dsClientInfoLogFile_.empty()) {
        LOG_WARN << "--ds-client-info-log-file is empty";
    }
    if (getRequired("ds-worker-access-log-file", dsWorkerAccessLogFile_) != RACK_OK || dsWorkerAccessLogFile_.empty()) {
        LOG_WARN << "--ds-worker-access-log-file is empty";
    }
    if (getRequired("ds-worker-info-log-file", dsWorkerInfoLogFile_) != RACK_OK || dsWorkerInfoLogFile_.empty()) {
        LOG_WARN << "--ds-worker-info-log-file is empty";
    }
    if (getRequired("resource-log-file", resourceLogFile_) != RACK_OK || resourceLogFile_.empty()) {
        LOG_WARN << "--resource-log-file is empty";
    }

    if (getRequired("start-time", startTimeStr_) != RACK_OK)
        return RACK_FAIL;
    if (getRequired("end-time", endTimeStr_) != RACK_OK)
        return RACK_FAIL;
    re2::RE2 timeRegex(TIME_PATTERN);
    if (!re2::RE2::FullMatch(startTimeStr_, timeRegex)) {
        LOG_ERROR << "Invalid start-time format: " << startTimeStr_ << ", expected yyyy-mm-dd hh:mm:ss";
        return RACK_FAIL;
    }
    if (!re2::RE2::FullMatch(endTimeStr_, timeRegex)) {
        LOG_ERROR << "Invalid end-time format: " << endTimeStr_ << ", expected yyyy-mm-dd hh:mm:ss";
        return RACK_FAIL;
    }
    auto startTs = failure::DatetimeStrToTimestamp(startTimeStr_);
    auto endTs = failure::DatetimeStrToTimestamp(endTimeStr_);
    if (!startTs.has_value() || !endTs.has_value()) {
        LOG_ERROR << "Failed to parse start-time or end-time";
        return RACK_FAIL;
    }
    if (startTs >= endTs) {
        LOG_ERROR << "start-time must be less than end-time";
        return RACK_FAIL;
    }
    startTimestamp_ = *startTs;
    endTimestamp_ = *endTs;
    LOG_INFO << "Parsed diag args: start=" << startTimeStr_ << " end=" << endTimeStr_;

    auto it = argMap.find("random-str");
    if (it != argMap.end()) {
        randomStr_ = it->second;
    }
    return RACK_OK;
}

RackResult DiagnosisToolModule::ConfigureMergedPath()
{
    const char *wittyDirEnv = std::getenv("WITTY_DIR");
    std::string wittyDir = wittyDirEnv ? wittyDirEnv : DEFAULT_WITTY_DIR;
    std::string randomPath = randomStr_.empty() ? "log" : "log_" + randomStr_;
    mergedLogDir_ = wittyDir + '/' + randomPath;

    std::error_code ec;
    fs::create_directories(mergedLogDir_, ec);
    if (ec) {
        LOG_ERROR << "Failed to create extracted log dir: " << mergedLogDir_ << ", error: " << ec.message();
        return RACK_FAIL;
    }
    fs::permissions(mergedLogDir_, fs::perms(DIR_PERM_755), ec);
    for (const auto &entry : fs::directory_iterator(mergedLogDir_, ec)) {
        if (ec) {
            break;
        }
        fs::remove(entry.path(), ec);
    }
    return RACK_OK;
}

std::vector<std::string> DiagnosisToolModule::FindMatchingFiles(const std::string &dir, const std::string &pattern)
{
    std::vector<std::string> matchedFiles;
    std::vector<std::string_view> patternViews;
    log_helper::SplitView(patternViews, pattern, ",");
    const std::vector<std::string> patterns = log_helper::ToStringFields(patternViews);

    std::error_code ec;

    for (fs::recursive_directory_iterator it(dir, ec), end; it != end; it.increment(ec)) {
        if (ec) {
            LOG_WARN << "Failed to iterate log directory: " << dir << ", error: " << ec.message();
            break;
        }
        if (!it->is_regular_file()) {
            continue;
        }

        const std::string filename = it->path().filename().string();
        if (filename.empty() || filename.front() == '.') {
            continue;
        }
        const bool matched = std::any_of(patterns.begin(), patterns.end(), [&](const std::string &item) {
            const bool isWildcard = item.find('*') != std::string::npos;
            return (isWildcard && log_helper::WildcardMatch(item, filename)) || (!isWildcard && filename == item);
        });
        if (matched) {
            matchedFiles.push_back(it->path().string());
        }
    }

    return matchedFiles;
}

RackResult DiagnosisToolModule::ExtractLogsByTimeWindow()
{
    struct LogFilePattern {
        const std::string *pattern;
        const char *argName;
    };

    const std::array<LogFilePattern, 5> logFilePatterns = {{
        {&dsClientAccessLogFile_, "ds-client-access-log-file"},
        {&dsClientInfoLogFile_, "ds-client-info-log-file"},
        {&dsWorkerInfoLogFile_, "ds-worker-info-log-file"},
        {&dsWorkerAccessLogFile_, "ds-worker-access-log-file"},
        {&resourceLogFile_, "resource-log-file"},
    }};

    for (const auto &entry : logFilePatterns) {
        if (entry.pattern->empty()) {
            continue;
        }

        std::vector<std::string> matchedFiles = FindMatchingFiles(dsLogPath_, *entry.pattern);
        if (matchedFiles.empty()) {
            LOG_WARN << "No files matching --" << entry.argName << " '" << *entry.pattern << "' found under "
                     << dsLogPath_;
            continue;
        }

        LOG_INFO << "Found " << matchedFiles.size() << " file(s) matching --" << entry.argName << " '" << *entry.pattern
                 << "'";
        std::unordered_set<std::string> writtenPaths;
        for (const auto &srcPath : matchedFiles) {
            fs::path outputPath = fs::path(mergedLogDir_) / fs::path(srcPath).filename();
            bool append = writtenPaths.find(outputPath.string()) != writtenPaths.end();
            LOG_INFO << "Extracting logs: " << srcPath << " -> " << outputPath.string() << (append ? " (append)" : "");

            if (!ExtractLogLinesByTimeWindow(srcPath, outputPath.string(), append)) {
                LOG_WARN << "Failed to extract log lines from: " << srcPath;
                return RACK_FAIL;
            }
            writtenPaths.insert(outputPath.string());
        }
    }
    return RACK_OK;
}

bool DiagnosisToolModule::ExtractLogLinesByTimeWindow(const std::string &inputPath, const std::string &outputPath,
                                                      bool append)
{
    std::ifstream inFile(inputPath);
    if (!inFile.is_open()) {
        LOG_WARN << "Cannot open input file: " << inputPath;
        return false;
    }

    std::ios_base::openmode mode = std::ios::out | (append ? std::ios::app : std::ios::trunc);
    std::ofstream outFile(outputPath, mode);
    if (!outFile.is_open()) {
        LOG_WARN << "Cannot open output file: " << outputPath;
        return false;
    }

    std::string line;
    int totalLines = 0;
    int matchedLines = 0;
    bool inRange = false;
    const std::string startTimeT = log_helper::ToTimestampTBound(startTimeStr_);
    const std::string endTimeT = log_helper::ToTimestampTBound(endTimeStr_);

    while (std::getline(inFile, line)) {
        totalLines++;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }

        std::string_view timeStr = log_helper::FindTimestampT(line);
        if (timeStr.empty()) {
            if (inRange) {
                outFile << line << '\n';
            }
            continue;
        }

        if (timeStr > endTimeT) {
            break;
        }
        if (timeStr < startTimeT) {
            inRange = false;
            continue;
        }

        inRange = true;
        matchedLines++;
        outFile << line << '\n';
    }

    LOG_INFO << "Extracted " << matchedLines << " / " << totalLines << " timestamped lines from " << inputPath;
    return true;
}

RackResult DiagnosisToolModule::SetEnvVars()
{
    struct LogEnvVar {
        const std::string *logFile;
        const char *envName;
    };

    const std::array<LogEnvVar, 5> logEnvVars = {{
        {&dsClientAccessLogFile_, "WITTY_UB_CLIENT_ACCESS_LOG"},
        {&dsClientInfoLogFile_, "WITTY_UB_CLIENT_INFO_LOG"},
        {&dsWorkerInfoLogFile_, "WITTY_UB_WORKER_INFO_LOG"},
        {&dsWorkerAccessLogFile_, "WITTY_UB_WORKER_ACCESS_LOG"},
        {&resourceLogFile_, "WITTY_UB_RESOURCES_LOG"},
    }};

    for (const auto &entry : logEnvVars) {
        std::string envValue;
        if (!entry.logFile->empty()) {
            envValue = mergedLogDir_ + '/' + *entry.logFile;
        }
        if (setenv(entry.envName, envValue.c_str(), 1) != 0) {
            LOG_ERROR << "Failed to set " << entry.envName << " environment variable";
            return RACK_FAIL;
        }
        LOG_INFO << entry.envName << " set to: " << envValue;
    }
    return RACK_OK;
}

RackResult DiagnosisToolModule::BuildFailureModeTree()
{
    failureModeJson_.clear();
    failureModeIdToController_.clear();
    moduleToRootFailureModeIds_.clear();

    const char *wittyDirEnv = std::getenv("WITTY_DIR");
    std::string wittyDir = wittyDirEnv ? wittyDirEnv : DEFAULT_WITTY_DIR;
    std::string jsonPath = wittyDir + '/' + FAILURE_MODE_TREE_JSON_PATH;
    std::ifstream ifs(jsonPath);
    if (!ifs.is_open()) {
        LOG_ERROR << "Failed to open failure mode tree json file: " << jsonPath;
        return RACK_FAIL;
    }

    Json::Value root;
    Json::CharReaderBuilder builder;
    std::string errs;
    if (!Json::parseFromStream(builder, ifs, &root, &errs)) {
        LOG_ERROR << "Failed to parse failure mode tree json file: " << jsonPath << ", error: " << errs;
        return RACK_FAIL;
    }

    auto modules = root.getMemberNames();
    for (const auto &moduleName : modules) {
        const auto &moduleNode = root[moduleName];
        if (!moduleNode.isObject()) {
            continue;
        }
        std::unordered_map<std::string, std::vector<std::string>> failureModeTreesInModule;
        auto failureModeIds = moduleNode.getMemberNames();
        std::unordered_set<std::string> allFailureModeIds, leafFailureModeIds;
        for (const auto &failureModeId : failureModeIds) {
            allFailureModeIds.insert(failureModeId);
            auto failureMode = FailureModeFactory::Instance().Create(failureModeId);
            if (!failureMode) {
                continue;
            }
            auto &childFailureModeIds = moduleNode[failureModeId];
            std::vector<std::string> childFailureModeIdVec;
            if (childFailureModeIds.isArray()) {
                for (const auto &childFailureModeId : childFailureModeIds) {
                    if (!childFailureModeId.isString()) {
                        continue;
                    }
                    childFailureModeIdVec.push_back(childFailureModeId.asString());
                    leafFailureModeIds.insert(childFailureModeId.asString());
                    failureMode->AddSubFailureMode(childFailureModeId.asString());
                    childToParentFailureModeIds_[childFailureModeId.asString()].push_back(failureModeId);
                }
            }
            FailureModeController controller(failureMode);
            failureModeIdToController_.emplace(failureModeId, controller);
            failureModeTreesInModule[failureModeId] = childFailureModeIdVec;
        }
        std::vector<std::string> rootFailureModeIdVec;
        for (const std::string &failureModeId : allFailureModeIds) {
            if (leafFailureModeIds.find(failureModeId) == leafFailureModeIds.end()) {
                rootFailureModeIdVec.push_back(failureModeId);
            }
        }
        moduleToRootFailureModeIds_[moduleName] = rootFailureModeIdVec;
        failureModeJson_[moduleName] = failureModeTreesInModule;
    }

    LOG_INFO << "Built failure mode tree from: " << jsonPath << ", loaded " << failureModeJson_.size() << " modules";
    return RACK_OK;
}

RackResult DiagnosisToolModule::BuildLogTypeToPathMap()
{
    std::error_code ec;
    for (fs::recursive_directory_iterator it(mergedLogDir_, fs::directory_options::skip_permission_denied, ec);
         it != fs::recursive_directory_iterator(); it.increment(ec)) {
        if (ec) {
            LOG_ERROR << "Failed to iterate merged log directory: " << mergedLogDir_ << ", error: " << ec.message();
            return RACK_FAIL;
        }
        if (!it->is_regular_file()) {
            continue;
        }
        if (log_helper::WildcardMatch(dsClientAccessLogFile_, it->path().filename()) ||
            log_helper::WildcardMatch(dsWorkerAccessLogFile_, it->path().filename())) {
            logTypeToPath_[LOG_TYPE_ACCESS].push_back(it->path().string());
        }
        if (log_helper::WildcardMatch(dsClientInfoLogFile_, it->path().filename()) ||
            log_helper::WildcardMatch(dsWorkerInfoLogFile_, it->path().filename())) {
            logTypeToPath_[LOG_TYPE_RUNTIME].push_back(it->path().string());
        }
    }
    return RACK_OK;
}

RackResult DiagnosisToolModule::AnalyzeAccessLogs()
{
    for (const std::string &accessLogPath : logTypeToPath_[LOG_TYPE_ACCESS]) {
        std::string logLine;
        std::ifstream ifs(accessLogPath);
        while (std::getline(ifs, logLine)) {
            std::vector<std::string_view> fieldViews;
            log_helper::SplitView(fieldViews, logLine, log_helper::DELIM, true);
            if (fieldViews.size() != ACCESS_FIELDS_SIZE) {
                continue;
            }
            int statusCode = 0;
            if (!log_helper::ParseInt(fieldViews[STATUSCODE_IDX], statusCode)) {
                continue;
            }
            if (statusCode == 0 && fieldViews[RESPMSG_IDX].empty()) {
                continue;
            }
            std::vector<std::string> fields = log_helper::ToStringFields(fieldViews);
            for (const std::string &failureModeId : moduleToRootFailureModeIds_[MODULE_KVCACHE]) {
                FailureModeController &controller = failureModeIdToController_.at(failureModeId);
                auto failureMode = controller.GetFailureMode();
                if (!failureMode->IsValid(fields)) {
                    continue;
                }
                rootValidFailureModeIds_.insert(failureModeId);
                std::shared_ptr<FailureLogInfoAccess> failureLogInfoAccess = nullptr;
                try {
                    failureLogInfoAccess = std::make_shared<FailureLogInfoAccess>(fields, logLine);
                } catch (const std::exception &e) {
                    LOG_WARN << e.what();
                    LOG_WARN << "Failed to construct failure log info for access log: " << logLine << ", skip...";
                    continue;
                }
                failureLogInfoAccess->BindFailureMode(failureModeId);
                controller.Hit(failureLogInfoAccess->traceId, failureLogInfoAccess);
                if (KVCACHE_FAILURE_002_STATUSCODE.find(statusCode) != KVCACHE_FAILURE_002_STATUSCODE.end()) {
                    // kvcache_002的故障码为2/3/8时需要下探到其子节点
                    for (const std::string &subFailureModeId : failureMode->GetSubFailureModes()) {
                        FailureModeController &subController = failureModeIdToController_.at(subFailureModeId);
                        auto subFailureMode = subController.GetFailureMode();
                        if (!subFailureMode->IsValid(fields)) {
                            continue;
                        }
                        failureLogInfoAccess->BindFailureMode(subFailureModeId);
                        subController.Hit(failureLogInfoAccess->traceId, failureLogInfoAccess);
                        break;
                    }
                }
                statusCodeToFailureModeId_.emplace(failureLogInfoAccess->statusCode, failureModeId);
                traceIdToFailureLogInfos_[failureLogInfoAccess->traceId].push_back(failureLogInfoAccess);
                traceIdToStatusCode_.emplace(failureLogInfoAccess->traceId, failureLogInfoAccess->statusCode);
                break;
            }
        }
    }
    return RACK_OK;
}

RackResult DiagnosisToolModule::AnalyzeRuntimeLogs()
{
    for (const std::string &runtimeLogPath : logTypeToPath_[LOG_TYPE_RUNTIME]) {
        std::string logLine;
        std::ifstream ifs(runtimeLogPath);
        while (std::getline(ifs, logLine)) {
            std::string_view traceId;
            if (!log_helper::ExtractSingleField(traceId, logLine, log_helper::DELIM, TRACEID_IDX) || traceId.empty()) {
                continue;
            }
            auto traceIdToStatusCodeIt = traceIdToStatusCode_.find(std::string(traceId));
            if (traceIdToStatusCodeIt == traceIdToStatusCode_.end()) {
                continue;
            }
            int statusCode = traceIdToStatusCodeIt->second;
            if (KVCACHE_FAILURE_002_STATUSCODE.find(statusCode) != KVCACHE_FAILURE_002_STATUSCODE.end()) {
                continue; // kvcache_002中故障码为2/3/8的故障已识别过
            }
            auto statusCodeToFailureModeIdIt = statusCodeToFailureModeId_.find(statusCode);
            if (statusCodeToFailureModeIdIt == statusCodeToFailureModeId_.end()) {
                continue;
            }
            const std::string &failureModeId = statusCodeToFailureModeIdIt->second;
            auto failureModeIdToControllerIt = failureModeIdToController_.find(failureModeId);
            if (failureModeIdToControllerIt == failureModeIdToController_.end()) {
                continue;
            }
            const FailureModeController &controller = failureModeIdToControllerIt->second;
            auto failureMode = controller.GetFailureMode(); // kvcache_002、006等
            const auto &subFailureModeIds = failureMode->GetSubFailureModes();
            std::vector<std::string_view> fieldViews;
            log_helper::SplitView(fieldViews, logLine, log_helper::DELIM, true);
            if (fieldViews.size() != RUNTIME_FIELDS_SIZE) {
                continue;
            }
            std::vector<std::string> fields = log_helper::ToStringFields(fieldViews);
            for (const std::string &subFailureModeId : subFailureModeIds) {
                const auto subFailureModeIdToControllerIt = failureModeIdToController_.find(subFailureModeId);
                if (subFailureModeIdToControllerIt == failureModeIdToController_.end()) {
                    continue;
                }
                FailureModeController &subController = subFailureModeIdToControllerIt->second;
                auto subFailureMode = subController.GetFailureMode(); // kvcache_002_001、006_001等
                if (!subFailureMode->IsValid(fields)) {
                    continue;
                }
                std::shared_ptr<FailureLogInfoRuntime> failureLogInfoRuntime = nullptr;
                try {
                    failureLogInfoRuntime = std::make_shared<FailureLogInfoRuntime>(fields, logLine);
                } catch (const std::exception &e) {
                    LOG_WARN << e.what();
                    LOG_WARN << "Failed to construct failure log info for runtime log: " << logLine << ", skip...";
                    continue;
                }
                failureLogInfoRuntime->BindFailureMode(subFailureModeId);
                subController.Hit(failureLogInfoRuntime->traceId, failureLogInfoRuntime);
                traceIdToFailureLogInfos_[failureLogInfoRuntime->traceId].push_back(failureLogInfoRuntime);
                break;
            }
            // urma
            if (logLine.find(URMA_LOG_KEYWORD) == std::string::npos) {
                continue;
            }
            for (const std::string &failureModeId : moduleToRootFailureModeIds_[MODULE_URMA]) {
                const auto failureModeIdToControllerIt = failureModeIdToController_.find(failureModeId);
                if (failureModeIdToControllerIt == failureModeIdToController_.end()) {
                    continue;
                }
                const FailureModeController &controller = failureModeIdToControllerIt->second;
                auto failureMode = controller.GetFailureMode();
                auto subFailureModeIds = failureMode->GetSubFailureModes();
                bool matchedSubFailureMode = false;
                for (const std::string &subFailureModeId : subFailureModeIds) {
                    const auto subFailureModeIdToControllerIt = failureModeIdToController_.find(subFailureModeId);
                    if (subFailureModeIdToControllerIt == failureModeIdToController_.end()) {
                        continue;
                    }
                    FailureModeController &subController = subFailureModeIdToControllerIt->second;
                    auto subFailureMode = subController.GetFailureMode();
                    if (!subFailureMode->IsValid(fields)) {
                        continue;
                    }
                    matchedSubFailureMode = true;
                    std::shared_ptr<FailureLogInfoRuntime> failureLogInfoRuntime = nullptr;
                    try {
                        failureLogInfoRuntime = std::make_shared<FailureLogInfoRuntime>(fields, logLine);
                    } catch (const std::exception &e) {
                        LOG_WARN << e.what();
                        LOG_WARN << "Failed to construct failure log info for runtime log: " << logLine << ", skip...";
                        continue;
                    }
                    failureLogInfoRuntime->BindFailureMode(subFailureModeId);
                    subController.Hit(failureLogInfoRuntime->traceId, failureLogInfoRuntime);
                    traceIdToUrmaFailureLogInfos_[failureLogInfoRuntime->traceId].push_back(failureLogInfoRuntime);
                    break;
                }
                if (matchedSubFailureMode) {
                    break;
                }
            }
        }
    }
    // urma部分的日志是倒序的（从后往前写日志），需要手动排序一下，再合并进最终的traceIdToFailureLogInfos_表
    for (auto &[traceId, urmaFailureLogInfos] : traceIdToUrmaFailureLogInfos_) { // 按时间倒序，其实是按上下游正序
        std::sort(urmaFailureLogInfos.begin(), urmaFailureLogInfos.end(),
                  [](const auto &lhs, const auto &rhs) { return lhs->timestamp > rhs->timestamp; });
        auto &failureLogInfos = traceIdToFailureLogInfos_[traceId];
        failureLogInfos.insert(failureLogInfos.end(), std::make_move_iterator(urmaFailureLogInfos.begin()),
                               std::make_move_iterator(urmaFailureLogInfos.end()));
        urmaFailureLogInfos.clear();
    }
    return RACK_OK;
}

RackResult DiagnosisToolModule::MergeFailureModeByTraceId()
{
    for (const auto &[traceId, failureLogInfos] : traceIdToFailureLogInfos_) {
        std::string prevFailureModeId;
        for (const auto &failureLogInfo : failureLogInfos) {
            const std::vector<std::string> &failureModeIds = failureLogInfo->failureModeIds;
            for (const std::string &failureModeId : failureModeIds) {
                if (failureModeId.empty()) {
                    continue;
                }
                traceIdToFailureModeIds_[traceId].push_back(failureModeId);
                if (!prevFailureModeId.empty() && prevFailureModeId != failureModeId) {
                    failureModeIdToController_.at(prevFailureModeId).InsertSubValidFailureModeId(failureModeId);
                }
                prevFailureModeId = failureModeId;
            }
        }
    }
    for (const auto &[traceId, failureModeIds] : traceIdToFailureModeIds_) {
        std::cout << "[" << traceId << "]: ";
        for (int i = 0; i < failureModeIds.size(); i++) {
            std::cout << failureModeIds[i];
            if (i != failureModeIds.size() - 1) {
                std::cout << " -> ";
            }
        }
        std::cout << std::endl;
    }
    return RACK_OK;
}

RackResult DiagnosisToolModule::StoreFailureTraces()
{
    fs::path failureTracesPath = fs::path(mergedLogDir_) / OUTPUT_FILENAME_FAILURE_TRACE;
    std::ofstream ofs(failureTracesPath, std::ios::out | std::ios::trunc);
    if (!ofs.is_open()) {
        LOG_ERROR << "Failed to open " << OUTPUT_FILENAME_FAILURE_TRACE << " for writing: " << failureTracesPath;
        return RACK_FAIL;
    }

    for (const auto &[traceId, failureLogInfos] : traceIdToFailureLogInfos_) {
        for (const auto &failureLogInfo : failureLogInfos) {
            if (failureLogInfo == nullptr || failureLogInfo->rawLog.empty() || failureLogInfo->failureModeIds.empty()) {
                continue;
            }

            std::string failureModeIdsStr;
            for (size_t i = 0; i < failureLogInfo->failureModeIds.size(); i++) {
                if (i > 0) {
                    failureModeIdsStr += ",";
                }
                failureModeIdsStr += failureLogInfo->failureModeIds[i];
            }

            ofs << failureModeIdsStr << " | " << failureLogInfo->rawLog << "\n";
            if (!ofs.good()) {
                LOG_ERROR << "Failed to write failure trace to output file (disk full?): " << failureTracesPath;
                return RACK_FAIL;
            }
        }
    }

    ofs.close();
    if (ofs.fail()) {
        LOG_ERROR << "Failed to close failure trace output file (disk full?): " << failureTracesPath;
        return RACK_FAIL;
    }
    LOG_INFO << "Stored failure traces to: " << failureTracesPath;
    return RACK_OK;
}

RackResult DiagnosisToolModule::GenerateFailureModeView()
{
    FailureModeView view;
    RackResult ret = view.Build(rootValidFailureModeIds_, failureModeIdToController_, traceIdToFailureLogInfos_);
    if (ret != RACK_OK) {
        LOG_ERROR << "failed to build failure mode view";
        return RACK_FAIL;
    }
    ret = view.Dump(mergedLogDir_);
    if (ret != RACK_OK) {
        LOG_ERROR << "failed to dump failure mode view";
    }
    LOG_INFO << "DiagnosisToolModule::Start() - Completed";
    return RACK_OK;
}
} // namespace diag
