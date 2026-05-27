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
#include <json/json.h>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <fnmatch.h>
#include <fstream>
#include <regex>
#include <sstream>
#include <sys/stat.h>
#include "failure_def.h"
#include "failure_mode.h"
#include "failure_mode_controller.h"
#include "failure_mode_factory.h"
#include "failure_mode_realization/urma/urma_log_helper.h"
#include "failure_mode_view.h"
#include "logger.h"
#include "ubse_context.h"

namespace diag {
using namespace ubse::context;

DiagnosisToolModule::DiagnosisToolModule() {}

bool urmaVisited = false;
constexpr const char *MODULE_KVCACHE = "kvcache_conn";
constexpr const char *MODULE_URMA = "urma";
constexpr const char *DEFAULT_WITTY_DIR = "/var/witty-ub";
constexpr const char *FAILUREMODE_JSON_DIR = "data/failure_mode_tree.json";
constexpr const char *EXTRACTED_LOG_BASE = "/var/witty-ub/log";
constexpr const char *TIME_FORMAT_REGEX = R"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})";
constexpr mode_t DIR_PERM_755 = 0755;
// 读取json文件，获取故障树
void DiagnosisToolModule::InitializeFailureModeTree()
{
    // 1. 清空现有数据
    failureModeJson.clear();
    failureModeInstanceMap.clear();
    subRootFailureModesMap.clear();

    // 2. 尝试打开文件
    const char *wittyDirEnv = std::getenv("WITTY_DIR");
    std::string wittyDir = wittyDirEnv ? wittyDirEnv : DEFAULT_WITTY_DIR;
    std::string path = (std::filesystem::path(wittyDir) / FAILUREMODE_JSON_DIR).string();
    std::ifstream file;
    file.open(path);
    if (!file.is_open()) {
        std::cerr << "Failed to open file: " << path << std::endl;
        return;
    }

    // 3. 解析 JSON
    Json::Value root;
    Json::CharReaderBuilder builder;
    std::string errs;
    if (!Json::parseFromStream(builder, file, &root, &errs)) {
        std::cerr << "Failed to parse JSON: " << errs << std::endl;
        return;
    }

    // 4. 遍历 JSON 并填充到 FailureModeJson
    auto outerKeys = root.getMemberNames();
    for (const auto &outerKey : outerKeys) {
        const Json::Value &innerObj = root[outerKey];
        if (!innerObj.isObject())
            continue;
        std::unordered_map<std::string, std::vector<std::string>> innerMap;
        auto innerKeys = innerObj.getMemberNames();
        std::unordered_set<std::string> allFailureModes, nonSubRootFailureModes;
        std::vector<std::string> subRootFailureModes;
        for (const auto &innerKey : innerKeys) {
            allFailureModes.insert(innerKey);
            std::shared_ptr<FailureMode> failureMode = FailureModeFactory::Instance().Create(innerKey);
            failureModeInstanceMap[innerKey] = failureMode;
            const Json::Value &arrayValue = innerObj[innerKey];
            std::vector<std::string> vec;
            if (arrayValue.isArray()) {
                for (const auto &element : arrayValue) {
                    if (element.isString()) {
                        vec.push_back(element.asString());
                        nonSubRootFailureModes.insert(element.asString());
                        if (failureMode != nullptr) {
                            failureMode->AddSubFailureMode(element.asString());
                        }
                    }
                }
            }
            innerMap[innerKey] = vec;
        }
        for (std::string failureMode : allFailureModes) {
            if (nonSubRootFailureModes.find(failureMode) == nonSubRootFailureModes.end()) {
                subRootFailureModes.push_back(failureMode);
            }
        }
        subRootFailureModesMap[outerKey] = subRootFailureModes;
        failureModeJson[outerKey] = innerMap;
    }

    // 可选：输出成功信息
    std::cout << "Successfully loaded " << failureModeJson.size()
              << " outer keys from failure_mode_tree.json (path: " << path << ")" << std::endl;
}

// 初始化模块
RackResult DiagnosisToolModule::Initialize()
{
    RackResult ret = ParseDiagArgs();
    if (ret != RACK_OK) {
        return ret;
    }
    ret = ExtractLogsByTimeWindow();
    if (ret != RACK_OK) {
        return ret;
    }
    InitializeFailureModeTree();
    return RACK_OK;
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

    if (getRequired("ds-log-path", dsLogPath) != RACK_OK) return RACK_FAIL;
    if (dsLogPath.empty() || !std::filesystem::exists(dsLogPath) ||
        !std::filesystem::is_directory(dsLogPath)) {
        LOG_ERROR << "--ds-log-path must be an existing directory: " << dsLogPath;
        return RACK_FAIL;
    }

    if (getRequired("ds-client-access-log-file", dsClientAccessLogFile) != RACK_OK) return RACK_FAIL;
    if (dsClientAccessLogFile.empty()) {
        LOG_ERROR << "--ds-client-access-log-file cannot be empty";
        return RACK_FAIL;
    }

    if (getRequired("ds-client-info-log-file", dsClientInfoLogFile) != RACK_OK) return RACK_FAIL;
    if (dsClientInfoLogFile.empty()) {
        LOG_ERROR << "--ds-client-info-log-file cannot be empty";
        return RACK_FAIL;
    }

    if (getRequired("ds-worker-info-log-file", dsWorkerInfoLogFile) != RACK_OK) return RACK_FAIL;
    if (dsWorkerInfoLogFile.empty()) {
        LOG_ERROR << "--ds-worker-info-log-file cannot be empty";
        return RACK_FAIL;
    }

    if (getRequired("resource-log-file", resourceLogFile) != RACK_OK) return RACK_FAIL;
    if (resourceLogFile.empty()) {
        LOG_ERROR << "--resource-log-file cannot be empty";
        return RACK_FAIL;
    }

    if (getRequired("start-time", startTimeStr) != RACK_OK) return RACK_FAIL;
    if (getRequired("end-time", endTimeStr) != RACK_OK) return RACK_FAIL;

    std::regex timeRegex(TIME_FORMAT_REGEX);
    if (!std::regex_match(startTimeStr, timeRegex)) {
        LOG_ERROR << "Invalid start-time format, expected yyyy-mm-dd hh:mm:ss: " << startTimeStr;
        return RACK_FAIL;
    }
    if (!std::regex_match(endTimeStr, timeRegex)) {
        LOG_ERROR << "Invalid end-time format, expected yyyy-mm-dd hh:mm:ss: " << endTimeStr;
        return RACK_FAIL;
    }

    auto startTs = failure::DatetimeStrToTimestamp(startTimeStr);
    auto endTs = failure::DatetimeStrToTimestamp(endTimeStr);
    if (!startTs.has_value() || !endTs.has_value()) {
        LOG_ERROR << "Failed to parse start-time or end-time";
        return RACK_FAIL;
    }
    startTimestamp = *startTs;
    endTimestamp = *endTs;

    if (startTimestamp >= endTimestamp) {
        LOG_ERROR << "start-time must be less than end-time";
        return RACK_FAIL;
    }

    LOG_INFO << "Parsed diag args: start=" << startTimeStr << " end=" << endTimeStr;
    return RACK_OK;
}

RackResult DiagnosisToolModule::ExtractLogsByTimeWindow()
{
    const char *wittyDirEnv = std::getenv("WITTY_DIR");
    std::string wittyDir = wittyDirEnv ? wittyDirEnv : DEFAULT_WITTY_DIR;
    std::filesystem::path baseDir = std::filesystem::path(wittyDir) / "log";
    extractedLogDir = baseDir.string();

    std::error_code ec;
    std::filesystem::create_directories(baseDir, ec);
    if (ec) {
        LOG_ERROR << "Failed to create log extraction directory: " << extractedLogDir;
        return RACK_FAIL;
    }
    std::filesystem::permissions(baseDir, std::filesystem::perms(DIR_PERM_755), ec);

    struct LogFileEntry {
        std::string pattern;
        std::string envName;
    };
    std::vector<LogFileEntry> logFiles = {
        {dsClientAccessLogFile, "WITTY_UB_CLIENT_ACCESS_LOG"},
        {dsClientInfoLogFile, "WITTY_UB_CLIENT_INFO_LOG"},
        {dsWorkerInfoLogFile, "WITTY_UB_WORKER_INFO_LOG"},
        {resourceLogFile, "WITTY_UB_RESOURCES_LOG"},
    };

    for (const auto &entry : logFiles) {
        std::vector<std::string> matchedFiles = FindMatchingFiles(dsLogPath, entry.pattern);
        if (matchedFiles.empty()) {
            LOG_ERROR << "No files matching '" << entry.pattern << "' found under " << dsLogPath;
            return RACK_FAIL;
        }
        LOG_INFO << "Found " << matchedFiles.size() << " file(s) matching " << entry.pattern;

        int totalLines = 0;
        for (const auto &srcPath : matchedFiles) {
            std::string filename = std::filesystem::path(srcPath).filename().string();
            std::string outputPath = (baseDir / filename).string();
            LOG_INFO << "Extracting logs: " << srcPath << " -> " << outputPath;
            if (!ExtractLogLines(srcPath, outputPath, startTimestamp, endTimestamp)) {
                LOG_WARN << "Failed to extract log lines from: " << srcPath;
                return RACK_FAIL;
            }
        }

        std::string envValue = (baseDir / entry.pattern).string();
        if (setenv(entry.envName.c_str(), envValue.c_str(), 1) != 0) {
            LOG_ERROR << "Failed to set " << entry.envName << " environment variable";
            return RACK_FAIL;
        }
        LOG_INFO << entry.envName << " set to: " << envValue;
    }

    // Set URMA_LOG_PATH same as WITTY_UB_WORKER_INFO_LOG
    std::string workerLogOutputPath = (baseDir / dsWorkerInfoLogFile).string();
    if (setenv("URMA_LOG_PATH", workerLogOutputPath.c_str(), 1) != 0) {
        LOG_ERROR << "Failed to set URMA_LOG_PATH environment variable";
        return RACK_FAIL;
    }
    LOG_INFO << "URMA_LOG_PATH set to: " << workerLogOutputPath;

    return RACK_OK;
}

void DiagnosisToolModule::ExtractLogLinesCount(const std::string &filePath,
                                               int64_t startTs, int64_t endTs,
                                               std::ofstream &outFile, int &count)
{
    std::ifstream inFile(filePath);
    if (!inFile.is_open()) {
        LOG_WARN << "Cannot open input file: " << filePath;
        return;
    }

    std::string line;
    bool inRange = false;
    std::regex timePattern(R"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})");
    while (std::getline(inFile, line)) {
        std::smatch match;
        if (!std::regex_search(line, match, timePattern)) {
            if (inRange) {
                outFile << line << '\n';
            }
            continue;
        }
        auto ts = failure::DatetimeStrToTimestamp(match.str());
        if (!ts.has_value()) {
            if (inRange) {
                outFile << line << '\n';
            }
            continue;
        }
        if (*ts > endTs) {
            break;
        }
        if (*ts >= startTs) {
            inRange = true;
            count++;
            outFile << line << '\n';
        } else {
            inRange = false;
        }
    }
}

std::vector<std::string> DiagnosisToolModule::FindMatchingFiles(const std::string &dir,
                                                                const std::string &pattern)
{
    std::vector<std::string> result;
    std::error_code ec;

    bool isWildcard = (pattern.find('*') != std::string::npos);
    auto isNotHidden = [](const std::filesystem::path &p) {
        return p.filename().string()[0] != '.';
    };

    for (auto it = std::filesystem::recursive_directory_iterator(dir, ec);
         it != std::filesystem::recursive_directory_iterator(); ++it) {
        if (ec) {
            break;
        }
        if (!it->is_regular_file()) {
            continue;
        }
        if (!isNotHidden(it->path())) {
            continue;
        }

        const std::string &filename = it->path().filename().string();
        if (isWildcard) {
            if (fnmatch(pattern.c_str(), filename.c_str(), 0) == 0) {
                result.push_back(it->path().string());
            }
        } else {
            if (filename == pattern) {
                result.push_back(it->path().string());
            }
        }
    }
    return result;
}

bool DiagnosisToolModule::ExtractLogLines(const std::string &filePath, const std::string &outputPath,
                                          int64_t startTs, int64_t endTs)
{
    std::ifstream inFile(filePath);
    if (!inFile.is_open()) {
        LOG_WARN << "Cannot open input file: " << filePath;
        return false;
    }

    std::ofstream outFile(outputPath, std::ios::out | std::ios::trunc);
    if (!outFile.is_open()) {
        LOG_WARN << "Cannot open output file: " << outputPath;
        return false;
    }

    std::string line;
    int totalLines = 0;
    int matchedLines = 0;
    bool inRange = false;
    std::regex timePattern(R"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})");
    while (std::getline(inFile, line)) {
        totalLines++;
        std::smatch match;
        if (!std::regex_search(line, match, timePattern)) {
            if (inRange) {
                outFile << line << '\n';
            }
            continue;
        }
        auto ts = failure::DatetimeStrToTimestamp(match.str());
        if (!ts.has_value()) {
            if (inRange) {
                outFile << line << '\n';
            }
            continue;
        }
        if (*ts > endTs) {
            break;
        }
        if (*ts >= startTs) {
            inRange = true;
            matchedLines++;
            outFile << line << '\n';
        } else {
            inRange = false;
        }
    }

    LOG_INFO << "Extracted " << matchedLines << " / " << totalLines << " lines from " << filePath;
    return true;
}

void DiagnosisToolModule::UnInitialize()
{
    LOG_INFO << "DiagnosisToolModule uninitialized";
}

// bool DiagnosisToolModule::VisitKvCache(FailureModeController controller)
// {
//     bool isValid = controller.GetFailureMode()->IsValid();
//     if (!isValid) {
//         return false;
//     }
//     visited.push_back(controller);
//     RootCause rootCause = controller.GetFailureMode()->AnalyzeRootCause();
//     if (rootCause.GetIsFinalRootCause()) {
//         validRoutes.push_back(visited);
//     } else {
//         bool childValidFlag = false;
//         std::vector<std::string> urmaFailureModes;
//         for (std::string subFailureMode : controller.GetFailureMode()->GetSubFailureModes()) {
//             // TODO: 加入visit urma的逻辑
//             if (subFailureMode.find(MODULE_URMA) == 0) {
//                 urmaFailureModes.push_back(subFailureMode);
//             }
//             else if (subFailureMode.find(MODULE_URMA) == 0) {
//                 childValidFlag = VisitKvCache(FailureModeController(failureModeInstanceMap[subFailureMode]));
//             }
//         }
//         if (urmaFailureModes.size() > 0) {
//             // TODO: 上方controller，如何把相关信息填进去传递给StartUrma？
//             childValidFlag = StartUrma(urmaFailureModes);
//         }
//         if (!childValidFlag) {
//             validRoutes.push_back(visited);
//         }
//     }
//     visited.pop_back();
//     return true;
// }

bool DiagnosisToolModule::Visit(FailureModeController controller)
{
    // TODO:把VisitUrma的逻辑同时拆给VisitKvcache
    std::shared_ptr<FailureMode> failureMode = controller.GetFailureMode();
    if (failureMode == nullptr) {
        return false;
    }
    std::string failureModeId = failureMode->GetId();
    if (failureMode->IsValid()) {
        std::cout << failureMode -> GetName() << std::endl;
        const std::vector<FailureLogInfo> &logInfos =
            urma_log_helper::GetParsedFailureLogLines(failureMode->GetFailureLogInfoCache());
        for (FailureLogInfo logInfo : logInfos) {
            if (!logInfo.traceId.empty()) {
                controller.AddHitCount();
                logInfo.failureModeId = failureModeId;
                controller.AddLogInfo(logInfo);
                traces[logInfo.traceId].push_back(logInfo);
            }
        }
    }
    allFailureModes.insert(failureModeId);
    failureModeIdToController.emplace(failureModeId, controller);
    RootCause rootCause = failureMode->AnalyzeRootCause();
    if (!rootCause.GetIsFinalRootCause() && (failureModeId.find(MODULE_KVCACHE) != 0 || !urmaVisited)) {
        for (std::string subFailureModeId : failureMode->GetSubFailureModes()) {
            if (subFailureModeId.find(MODULE_URMA) == 0) {
                urmaVisited = true;
            }
            Visit(FailureModeController(failureModeInstanceMap[subFailureModeId]));
        }
    }
    return true;
}

void DiagnosisToolModule::StartKvcache(const std::vector<std::string> &subRootFailureModes)
{
    for (auto subRootFailureModeId : subRootFailureModes) {
        auto iter = failureModeInstanceMap.find(subRootFailureModeId);
        if (iter == failureModeInstanceMap.end()) {
            continue;
        }
        std::shared_ptr<FailureMode> subRootFailureMode = iter->second;
        Visit(FailureModeController(subRootFailureMode));
    }
}

void DiagnosisToolModule::StartUrma(const std::vector<std::string> &subRootFailureModes)
{
    for (auto subRootFailureModeId : subRootFailureModes) {
        auto iter = failureModeInstanceMap.find(subRootFailureModeId);
        if (iter == failureModeInstanceMap.end()) {
            continue;
        }
        std::shared_ptr<FailureMode> subRootFailureMode = iter->second;
        Visit(FailureModeController(subRootFailureMode));
    }
    // 仅对urma的trace排序
    for (auto &[traceId, trace] : traces) {
        std::sort(trace.begin(), trace.end(), [](const FailureLogInfo &left, const FailureLogInfo &right) {
            if (left.failureModeId.find(MODULE_KVCACHE) == 0 || right.failureModeId.find(MODULE_KVCACHE) == 0) {
                return true;
            } else {
                return left.timestamp > right.timestamp;
            }
        });
    }
}

RackResult DiagnosisToolModule::Start()
{
    failureModeIdToController.clear();
    traces.clear();
    allFailureModes.clear();
    childFailureModes.clear();
    rootFailureModes.clear();

    for (auto subRootFailures : subRootFailureModesMap) {
        std::string moduleName = subRootFailures.first;
        if (moduleName == MODULE_KVCACHE) {
            std::cout << "Diagnosing failures in module: " << moduleName << std::endl;
            StartKvcache(subRootFailures.second);
        }
        // 仅调试，正式版本执行上述代码走KVCache判断，删除下述代码
        // if (moduleName == MODULE_URMA) {
        //     std::cout << "Diagnosing failures in module: " << moduleName << std::endl;
        //     StartUrma(subRootFailures.second);
        // }
    }
    // 仅对urma的trace排序
    for (auto &[traceId, trace] : traces) {
        std::sort(trace.begin(), trace.end(), [](const FailureLogInfo &left, const FailureLogInfo &right) {
            if (left.failureModeId.find(MODULE_KVCACHE) == 0 && right.failureModeId.find(MODULE_URMA) == 0) {
                return true;
            } else if (left.failureModeId.find(MODULE_URMA) == 0 && right.failureModeId.find(MODULE_KVCACHE) == 0) {
                return false;
            } else {
                return left.timestamp > right.timestamp;
            }
        });
    }
    for (const auto &[traceId, trace] : traces) {
        int traceLen = trace.size();
        for (int i = 0; i < traceLen - 1; ++i) {
            const std::string &currModeId = trace[i].failureModeId;
            const std::string &nextModeId = trace[i + 1].failureModeId;
            auto &currController = failureModeIdToController.at(currModeId);
            currController.AddSubFailureModeValid(nextModeId);
            childFailureModes.insert(nextModeId);
        }
    }
    for (const auto &failureModeId : allFailureModes) {
        if (childFailureModes.find(failureModeId) == childFailureModes.end()) {
            rootFailureModes.insert(failureModeId);
        }
    }
    for (auto &[traceId, trace] : traces) {
        std::cout << "traceId: " << traceId << std::endl;
        for (const auto& logInfo : trace) {
            std::cout << logInfo.failureModeId << " -> ";
        }
        std::cout << std::endl;
    }
    FailureModeView view;
    RackResult ret = view.Build(rootFailureModes, failureModeIdToController, traces);
    if (ret != RACK_OK) {
        LOG_ERROR << "failed to build failure mode view";
        return RACK_FAIL;
    }
    ret = view.Dump();
    if (ret != RACK_OK) {
        LOG_ERROR << "failed to dump failure mode view";
    }
    LOG_INFO << "DiagnosisToolModule::Start() - Completed";
    return RACK_OK;
}

void DiagnosisToolModule::Stop()
{
    LOG_INFO << "DiagnosisToolModule stopped";
}

} // namespace diag
