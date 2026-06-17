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
#include <fnmatch.h>
#include <json/json.h>
#include <sys/stat.h>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <regex>
#include <sstream>
#include <unordered_set>
#include <unordered_map>
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

std::string JoinPathsForShell(const std::vector<std::string> &paths)
{
    std::ostringstream oss;
    for (size_t i = 0; i < paths.size(); i++) {
        if (i > 0) {
            oss << " ";
        }
        oss << paths[i];
    }
    return oss.str();
}

std::string CombineLogsForQuotedEnv(const std::filesystem::path &baseDir, const std::string &fileName,
                                    const std::vector<std::string> &paths)
{
    if (paths.size() <= 1) {
        return paths.empty() ? "" : paths.front();
    }

    std::filesystem::path combinedDir = baseDir / ".combined_logs";
    std::error_code ec;
    std::filesystem::create_directories(combinedDir, ec);
    if (ec) {
        LOG_WARN << "Failed to create combined log directory: " << combinedDir;
        return JoinPathsForShell(paths);
    }

    std::filesystem::path combinedPath = combinedDir.append(fileName);
    std::ofstream outFile(combinedPath, std::ios::out | std::ios::trunc);
    if (!outFile.is_open()) {
        LOG_WARN << "Cannot open combined log file: " << combinedPath;
        return JoinPathsForShell(paths);
    }

    for (const auto &path : paths) {
        std::ifstream inFile(path);
        if (!inFile.is_open()) {
            LOG_WARN << "Cannot open extracted log file for combine: " << path;
            continue;
        }
        outFile << inFile.rdbuf();
        if (!outFile.good()) {
            LOG_WARN << "Failed to write to combined log file (disk full?): " << combinedPath;
            return JoinPathsForShell(paths);
        }
        if (outFile.tellp() > 0) {
            outFile << '\n';
        }
    }
    outFile.close();
    if (outFile.fail()) {
        LOG_WARN << "Failed to close combined log file (disk full?): " << combinedPath;
        return JoinPathsForShell(paths);
    }
    return combinedPath.string();
}

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
                for (auto &element : arrayValue) {
                    if (element.isString()) {
                        if (childToParentFailureModes.find(element.asString()) == childToParentFailureModes.end()) {
                            std::vector<std::string> vec;
                            childToParentFailureModes[element.asString()] = vec;
                        }
                        childToParentFailureModes[element.asString()].push_back(innerKey);
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
    if (getRequired("ds-log-path", dsLogPath) != RACK_OK) {
        LOG_ERROR << "--ds-log-path must not be empty";
        return RACK_FAIL;
    }
    if (dsLogPath.empty() || !std::filesystem::exists(dsLogPath) || !std::filesystem::is_directory(dsLogPath)) {
        LOG_WARN << "--ds-log-path must be an existing directory: " << dsLogPath;
        return RACK_FAIL;
    }

    if (getRequired("ds-client-access-log-file", dsClientAccessLogFile) != RACK_OK || dsClientAccessLogFile.empty()) {
        LOG_WARN << "--ds-client-access-log-file is empty";
    }

    if (getRequired("ds-client-info-log-file", dsClientInfoLogFile) != RACK_OK || dsClientInfoLogFile.empty()) {
        LOG_WARN << "--ds-client-info-log-file is empty";
    }

    if (getRequired("ds-worker-info-log-file", dsWorkerInfoLogFile) != RACK_OK || dsWorkerInfoLogFile.empty()) {
        LOG_WARN << "--ds-worker-info-log-file is empty";
    }

    if (getRequired("ds-worker-access-log-file", dsWorkerAccessLogFile) != RACK_OK || dsWorkerAccessLogFile.empty()) {
        LOG_WARN << "--ds-worker-access-log-file is empty";
    }

    if (getRequired("resource-log-file", resourceLogFile) != RACK_OK || resourceLogFile.empty()) {
        LOG_WARN << "--resource-log-file is empty";
    }

    if (getRequired("start-time", startTimeStr) != RACK_OK)
        return RACK_FAIL;
    if (getRequired("end-time", endTimeStr) != RACK_OK)
        return RACK_FAIL;

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

    auto it = argMap.find("random-str");
    if (it != argMap.end()) {
        randomStr = it->second;
    }
    return RACK_OK;
}

RackResult DiagnosisToolModule::ExtractLogsByTimeWindow()
{
    const char *wittyDirEnv = std::getenv("WITTY_DIR");
    std::string wittyDir = wittyDirEnv ? wittyDirEnv : DEFAULT_WITTY_DIR;
    std::string randomPathStr = randomStr.empty() ? "log" : "log_" + randomStr;
    std::filesystem::path baseDir = std::filesystem::path(wittyDir) / randomPathStr;
    extractedLogDir = baseDir.string();

    std::error_code ec;
    std::filesystem::create_directories(baseDir, ec);
    if (ec) {
        LOG_ERROR << "Failed to create log extraction directory: " << extractedLogDir;
        return RACK_FAIL;
    }
    std::filesystem::permissions(baseDir, std::filesystem::perms(DIR_PERM_755), ec);

    // 清除已有日志文件，避免新旧日志混合
    for (const auto &entry : std::filesystem::directory_iterator(baseDir, ec)) {
        if (ec)
            break;
        std::filesystem::remove(entry.path(), ec);
    }

    struct LogFileEntry {
        std::string pattern;
        std::string envName;
    };
    std::vector<LogFileEntry> logFiles = {
        {dsClientAccessLogFile, "WITTY_UB_CLIENT_ACCESS_LOG"}, {dsClientInfoLogFile, "WITTY_UB_CLIENT_INFO_LOG"},
        {dsWorkerInfoLogFile, "WITTY_UB_WORKER_INFO_LOG"},     {dsWorkerAccessLogFile, "WITTY_UB_WORKER_ACCESS_LOG"},
        {resourceLogFile, "WITTY_UB_RESOURCES_LOG"},
    };

    std::unordered_map<std::string, std::string> extractedEnvValues;
    std::unordered_map<std::string, std::vector<std::string>> extractedEnvPaths;
    for (const auto &entry : logFiles) {
        std::vector<std::string> matchedFiles = FindMatchingFiles(dsLogPath, entry.pattern);
        if (matchedFiles.empty()) {
            LOG_WARN << "No files matching '" << entry.pattern << "' found under " << dsLogPath;
        }
        LOG_INFO << "Found " << matchedFiles.size() << " file(s) matching " << entry.pattern;

        int totalLines = 0;
        std::vector<std::string> extractedPaths;
        std::unordered_set<std::string> writtenPaths;
        for (const auto &srcPath : matchedFiles) {
            std::string filename = std::filesystem::path(srcPath).filename().string();
            std::string outputPath = (baseDir / filename).string();
            bool append = writtenPaths.find(outputPath) != writtenPaths.end();
            LOG_INFO << "Extracting logs: " << srcPath << " -> " << outputPath
                     << (append ? " (append)" : "");
            if (!ExtractLogLines(srcPath, outputPath, startTimestamp, endTimestamp, append)) {
                LOG_WARN << "Failed to extract log lines from: " << srcPath;
                return RACK_FAIL;
            }
            extractedPaths.push_back(outputPath);
            writtenPaths.insert(outputPath);
        }

        std::string envValue = JoinPathsForShell(extractedPaths);
        extractedEnvValues[entry.envName] = envValue;
        extractedEnvPaths[entry.envName] = extractedPaths;
        if (setenv(entry.envName.c_str(), envValue.c_str(), 1) != 0) {
            LOG_ERROR << "Failed to set " << entry.envName << " environment variable";
            return RACK_FAIL;
        }
        LOG_INFO << entry.envName << " set to: " << envValue;
    }

    // Set URMA_LOG_PATH same as WITTY_UB_WORKER_INFO_LOG
    std::string workerLogOutputPath =
        CombineLogsForQuotedEnv(baseDir, "worker_info.log", extractedEnvPaths["WITTY_UB_WORKER_INFO_LOG"]);
    if (setenv("URMA_LOG_PATH", workerLogOutputPath.c_str(), 1) != 0) {
        LOG_ERROR << "Failed to set URMA_LOG_PATH environment variable";
        return RACK_FAIL;
    }
    LOG_INFO << "URMA_LOG_PATH set to: " << workerLogOutputPath;

    return RACK_OK;
}

void DiagnosisToolModule::ExtractLogLinesCount(const std::string &filePath, int64_t startTs, int64_t endTs,
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
        // 去除 Windows 风格换行符遗留的回车符 (^M)，避免污染最后一列数据
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
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
            if (!outFile.good()) {
                LOG_ERROR << "Failed to write to output file (disk full?): " << filePath;
                return;
            }
        } else {
            inRange = false;
        }
    }
    outFile.close();
    if (outFile.fail()) {
        LOG_ERROR << "Failed to close output file (disk full?): " << filePath;
    }
}

std::vector<std::string> DiagnosisToolModule::FindMatchingFiles(const std::string &dir, const std::string &pattern)
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
                                          int64_t startTs, int64_t endTs, bool append)
{
    std::ifstream inFile(filePath);
    if (!inFile.is_open()) {
        LOG_WARN << "Cannot open input file: " << filePath;
        return false;
    }

    std::ios_base::openmode mode = std::ios::out;
    mode |= append ? std::ios::app : std::ios::trunc;
    std::ofstream outFile(outputPath, mode);
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
        // 去除 Windows 风格换行符遗留的回车符 (^M)，避免污染最后一列数据
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
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
            if (!outFile.good()) {
                LOG_ERROR << "Failed to write extracted log line to output file (disk full?): " << outputPath;
                return false;
            }
        } else {
            inRange = false;
        }
    }

    outFile.close();
    if (outFile.fail()) {
        LOG_ERROR << "Failed to close output file (disk full?): " << outputPath;
        return false;
    }

    LOG_INFO << "Extracted " << matchedLines << " / " << totalLines << " lines from " << filePath;
    return true;
}

void DiagnosisToolModule::UnInitialize()
{
    LOG_INFO << "DiagnosisToolModule uninitialized";
}

void DiagnosisToolModule::AppendLogsToParent(const std::string &failureModeId,
                                             const std::vector<FailureLogInfo> &logInfos)
{
    if (failureModeId.find(MODULE_URMA) != 0 || childToParentFailureModes[failureModeId][0].find(MODULE_URMA) != 0) {
        return;
    }
    std::string parentFailureModeId = childToParentFailureModes[failureModeId][0];
    std::cout << "parent: " << parentFailureModeId << std::endl;
    FailureModeController &parentController = failureModeIdToController.at(parentFailureModeId);
    for (FailureLogInfo logInfo : logInfos) {
        parentController.AddHitCount(logInfo.traceId);
        logInfo.failureModeId = parentFailureModeId;
        parentController.AddLogInfo(logInfo);
        if (traces.find(logInfo.traceId) == traces.end()) {
            std::vector<FailureLogInfo> tmp;
            tmp.clear();
            traces[logInfo.traceId] = tmp;
        }
        traces[logInfo.traceId].push_back(logInfo);
        std::cout << "append second: " << traces[logInfo.traceId].back().failureModeId << std::endl;
    }
}

void DiagnosisToolModule::ProcessLogInfos(FailureModeController &controller, const std::string &failureModeId,
                                          const std::vector<FailureLogInfo> &logInfos)
{
    for (FailureLogInfo logInfo : logInfos) {
        if (!logInfo.traceId.empty()) {
            controller.AddHitCount(logInfo.traceId);
            logInfo.failureModeId = failureModeId;
            controller.AddLogInfo(logInfo);
            traces[logInfo.traceId].push_back(logInfo);
            std::cout << "append: " << traces[logInfo.traceId].back().failureModeId << std::endl;
        }
    }
}

void DiagnosisToolModule::ProcessSubFailureModes(const std::string &failureModeId, FailureMode *failureMode)
{
    RootCause rootCause = failureMode->AnalyzeRootCause();
    if (rootCause.GetIsFinalRootCause()) {
        return;
    }
    bool subFailureModeIsUrma = false;
    for (std::string subFailureModeId : failureMode->GetSubFailureModes()) {
        if (failureModeId.find(MODULE_KVCACHE) == 0 && subFailureModeId.find(MODULE_URMA) == 0 && urmaVisited) {
            break;
        }
        if (failureModeId.find(MODULE_KVCACHE) == 0 && subFailureModeId.find(MODULE_URMA) == 0) {
            subFailureModeIsUrma = true;
        }
        Visit(FailureModeController(failureModeInstanceMap[subFailureModeId]));
    }
    urmaVisited = urmaVisited || subFailureModeIsUrma;
}

void DiagnosisToolModule::Visit(FailureModeController controller)
{
    std::shared_ptr<FailureMode> failureMode = controller.GetFailureMode();
    if (failureMode == nullptr) {
        return;
    }
    std::string failureModeId = failureMode->GetId();
    if (!failureMode->IsValid()) {
        return;
    }
    std::cout << "validFailureMode: " << failureModeId << std::endl;
    const std::vector<FailureLogInfo> &logInfos =
        urma_log_helper::GetParsedFailureLogLines(failureMode->GetFailureLogInfoCache());
    AppendLogsToParent(failureModeId, logInfos);
    ProcessLogInfos(controller, failureModeId, logInfos);
    if (failureModeId.find(MODULE_KVCACHE) == 0 || childToParentFailureModes[failureModeId][0].find(MODULE_URMA) == 0) {
        allFailureModes.insert(failureModeId);
    }
    failureModeIdToController.emplace(failureModeId, controller);
    ProcessSubFailureModes(failureModeId, failureMode.get());
}

void DiagnosisToolModule::StartKvcache(const std::vector<std::string> &subRootFailureModes)
{
    for (auto subRootFailureModeId : subRootFailureModes) {
        auto iter = failureModeInstanceMap.find(subRootFailureModeId);
        if (iter == failureModeInstanceMap.end()) {
            continue;
        }
        std::shared_ptr<FailureMode> subRootFailureMode = iter->second;
        std::cout << "visit " << subRootFailureMode->GetId() << std::endl;
        Visit(FailureModeController(subRootFailureMode));
    }
}

void DiagnosisToolModule::StoreFailureTraces()
{
    const char *wittyDirEnv = std::getenv("WITTY_DIR");
    std::string wittyDir;

    if (wittyDirEnv != nullptr && std::filesystem::exists(wittyDirEnv)) {
        wittyDir = wittyDirEnv;
    } else {
        wittyDir = DEFAULT_WITTY_DIR;
    }

    std::string randomPathStr = randomStr.empty() ? "log" : "log_" + randomStr;
    std::filesystem::path logDir = std::filesystem::path(wittyDir) / randomPathStr;

    std::error_code ec;
    if (!std::filesystem::exists(logDir)) {
        std::filesystem::create_directories(logDir, ec);
        if (ec) {
            LOG_ERROR << "Failed to create log directory: " << logDir;
            return;
        }
    }

    std::string fileName = "failure_trace.log";
    std::filesystem::path tracesFile = logDir / fileName;
    std::ofstream outFile(tracesFile, std::ios::out | std::ios::trunc);

    if (!outFile.is_open()) {
        LOG_ERROR << "Failed to open " << fileName << " for writing: " << tracesFile;
        return;
    }

    for (const auto &[traceId, logInfos] : traces) {
        std::vector<std::pair<FailureLogInfo, std::vector<std::string>>> logInfoToFailureModeIds;

        for (const auto &logInfo : logInfos) {
            if (!logInfo.rawLog.empty() && !logInfo.failureModeId.empty()) {
                auto it = std::find_if(logInfoToFailureModeIds.begin(), logInfoToFailureModeIds.end(),
                    [&logInfo](const auto &pair) { return pair.first == logInfo; });
                if (it != logInfoToFailureModeIds.end()) {
                    it->second.push_back(logInfo.failureModeId);
                } else {
                    logInfoToFailureModeIds.push_back({logInfo, {logInfo.failureModeId}});
                }
            }
        }

        for (const auto &[logInfo, failureModeIds] : logInfoToFailureModeIds) {
            std::string failureModeIdsStr;
            for (size_t i = 0; i < failureModeIds.size(); i++) {
                if (i > 0) {
                    failureModeIdsStr += ",";
                }
                failureModeIdsStr += failureModeIds[i];
            }

            outFile << failureModeIdsStr << " | " << logInfo.rawLog << "\n";
            if (!outFile.good()) {
                LOG_ERROR << "Failed to write failure trace to output file (disk full?): " << tracesFile;
                return;
            }
        }
    }

    outFile.close();
    if (outFile.fail()) {
        LOG_ERROR << "Failed to close failure trace output file (disk full?): " << tracesFile;
        return;
    }
    LOG_INFO << "Stored failure traces to: " << tracesFile;
}

RackResult DiagnosisToolModule::GenerateView()
{
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

RackResult DiagnosisToolModule::Start()
{
    failureModeIdToController.clear();
    traces.clear();
    allFailureModes.clear();
    rootFailureModes.clear();

    for (auto subRootFailures : subRootFailureModesMap) {
        std::string moduleName = subRootFailures.first;
        if (moduleName == MODULE_KVCACHE) {
            std::cout << "Diagnosing failures in module: " << moduleName << std::endl;
            StartKvcache(subRootFailures.second);
        }
    }
    // 仅对urma的trace排序
    for (auto &[traceId, trace] : traces) {
        for (auto &info : trace) {
            std::cout << "info id" << info.failureModeId << std::endl;
        }
    }
    for (auto &[traceId, trace] : traces) {
        std::vector<FailureLogInfo> sortedTrace = trace; // 深拷贝一份
        std::sort(sortedTrace.begin(), sortedTrace.end(), [](const FailureLogInfo &left, const FailureLogInfo &right) {
            bool leftKv = left.failureModeId.find(MODULE_KVCACHE) == 0;
            bool rightKv = right.failureModeId.find(MODULE_KVCACHE) == 0;
            bool leftUrma = left.failureModeId.find(MODULE_URMA) == 0;
            bool rightUrma = right.failureModeId.find(MODULE_URMA) == 0;
            if (leftKv && rightUrma) {
                return true;
            }
            if (leftUrma && rightKv) {
                return false;
            }
            if (left.timestamp != right.timestamp) {
                return left.timestamp > right.timestamp; // 降序，注意是 > 不是 >=
            }
            return left.failureModeId < right.failureModeId; // 可选：保证同时间排序稳定
        });
        trace = std::move(sortedTrace); // 用排好序的副本替换原容器
    }
    // 对trace进行后处理
    std::cout << "post treat " << std::endl;
    for (const auto &[traceId, trace] : traces) {
        std::unordered_set<std::string> allFailureModeIds;
        std::vector<FailureLogInfo> newTrace;
        std::unordered_set<std::string> traceFailureModeIds;
        int traceLen = trace.size();
        for (int i = 0; i < traceLen; i++) {
            allFailureModeIds.insert(trace[i].failureModeId);
        }
        // 首先删除没有父节点的子节点
        for (int i = 0; i < traceLen; i++) {
            std::string currFailureModeId = trace[i].failureModeId;
            bool valid = true;
            // 如果KVCache的某一级父节点不在当前列表中，说明该节点无效
            while (currFailureModeId.find(MODULE_KVCACHE) == 0 &&
                   childToParentFailureModes.find(currFailureModeId) != childToParentFailureModes.end()) {
                if (allFailureModeIds.find(childToParentFailureModes[currFailureModeId][0]) ==
                    allFailureModeIds.end()) {
                    valid = false;
                    break;
                }
                currFailureModeId = childToParentFailureModes[currFailureModeId][0];
            }
            if (valid) {
                newTrace.push_back(trace[i]);
                traceFailureModeIds.insert(trace[i].failureModeId);
            }
        }
        traces[traceId] = newTrace;
        // 将子节点加入父节点FailureModeController中
        std::vector<std::string> historyUrmaFailureModeIds;
        for (int i = 0; i < newTrace.size(); i++) {
            FailureLogInfo currTrace = newTrace[i];
            std::string currId = currTrace.failureModeId;
            if (childToParentFailureModes.find(currId) == childToParentFailureModes.end()) {
                continue;
            }
            // 若是urma二级节点，判断之前是否有上级的一级节点。若有，则上级为前一个二级节点；若无，则上级为一级节点。需避免循环。
            if (currId.find(MODULE_URMA) == 0 && childToParentFailureModes[currId][0].find(MODULE_URMA) == 0) {
                if (std::find(historyUrmaFailureModeIds.begin(), historyUrmaFailureModeIds.end(), currId) !=
                    historyUrmaFailureModeIds.end()) {
                    continue;
                } else if (std::find(historyUrmaFailureModeIds.begin(), historyUrmaFailureModeIds.end(),
                                     childToParentFailureModes[currId][0]) == historyUrmaFailureModeIds.end()) {
                    historyUrmaFailureModeIds.push_back(childToParentFailureModes[currId][0]);
                    historyUrmaFailureModeIds.push_back(currId);
                } else {
                    FailureModeController &parentFailureModeController =
                        failureModeIdToController.at(historyUrmaFailureModeIds.back());
                    parentFailureModeController.AddSubFailureModeValid(currId);
                    historyUrmaFailureModeIds.push_back(currId);
                    continue;
                }
            }
            for (std::string parentFailureModeId : childToParentFailureModes[currId]) {
                if (traceFailureModeIds.find(parentFailureModeId) != traceFailureModeIds.end()) {
                    FailureModeController &parentFailureModeController =
                        failureModeIdToController.at(parentFailureModeId);
                    parentFailureModeController.AddSubFailureModeValid(currId);
                }
            }
        }
    }
    // 获取根节点
    for (const auto &failureModeId : allFailureModes) {
        if (childToParentFailureModes.find(failureModeId) == childToParentFailureModes.end()) {
            rootFailureModes.insert(failureModeId);
        }
    }
    // 打印故障Traces的结果
    for (auto &[traceId, trace] : traces) {
        std::cout << "traceId: " << traceId << ": ";
        for (const auto &logInfo : trace) {
            std::cout << logInfo.failureModeId << " -> ";
        }
        std::cout << std::endl;
    }
    // 保存故障Traces的结果
    StoreFailureTraces();
    GenerateView();
    return RACK_OK;
}

void DiagnosisToolModule::Stop()
{
    LOG_INFO << "DiagnosisToolModule stopped";
}

} // namespace diag
