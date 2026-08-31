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

#include "diagnosis_tool_module.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <limits>
#include <string_view>
#include <unordered_set>

#include <fcntl.h>
#include <re2/re2.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include "failure_def.h"
#include "failure_log_helper.h"
#include "logger.h"
#include "ubse_context.h"

namespace diag {
namespace fs = std::filesystem;
using namespace ubse::context;

namespace {
constexpr const char *LOG_TYPE_ACCESS = "access";
constexpr const char *LOG_TYPE_RUNTIME = "runtime";
constexpr const char *TIME_PATTERN = R"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})";
constexpr const char *DEFAULT_WITTY_DIR = "/var/witty-ub";
constexpr const char *OUTPUT_FILENAME_FAILURE_TRACE = "failure_trace.log";
constexpr const char *WITTY_DIR_ENVIRONMENT = "WITTY_DIR";
constexpr const char *DEFAULT_LOG_DIR_NAME = "log";
constexpr const char *RANDOM_LOG_DIR_PREFIX = "log_";
constexpr const char *ARG_DS_LOG_PATH = "ds-log-path";
constexpr const char *ARG_DS_CLIENT_ACCESS_LOG = "ds-client-access-log-file";
constexpr const char *ARG_DS_CLIENT_INFO_LOG = "ds-client-info-log-file";
constexpr const char *ARG_DS_WORKER_ACCESS_LOG = "ds-worker-access-log-file";
constexpr const char *ARG_DS_WORKER_INFO_LOG = "ds-worker-info-log-file";
constexpr const char *ARG_RESOURCE_LOG = "resource-log-file";
constexpr const char *ARG_START_TIME = "start-time";
constexpr const char *ARG_END_TIME = "end-time";
constexpr const char *ARG_RANDOM_STRING = "random-str";
constexpr std::string_view PATTERN_LIST_DELIMITER = ",";
constexpr std::string_view WILDCARD_MARKER = "*";
constexpr std::string_view FAILURE_TRACE_DELIMITER = " | ";
constexpr char HIDDEN_FILE_PREFIX = '.';
constexpr char WINDOWS_LINE_END = '\r';
constexpr mode_t OUTPUT_DIRECTORY_PERMISSIONS = 0755;
constexpr std::size_t ESTIMATED_LOG_LINE_LENGTH = 128;

bool MatchesAnyPattern(const std::string &patternList, const fs::path &filename)
{
    std::vector<std::string_view> patternViews;
    log_helper::SplitView(patternViews, patternList, PATTERN_LIST_DELIMITER);
    return std::any_of(patternViews.begin(), patternViews.end(), [&](std::string_view pattern) {
        return !pattern.empty() && log_helper::WildcardMatch(std::string(pattern), filename.string());
    });
}
} // namespace

MappedReadFile::MappedReadFile(const std::string &path)
{
    descriptor_ = ::open(path.c_str(), O_RDONLY);
    struct stat status {};
    if (descriptor_ < 0 || ::fstat(descriptor_, &status) != 0 || status.st_size < 0 ||
        static_cast<std::uintmax_t>(status.st_size) > std::numeric_limits<std::size_t>::max()) {
        Close();
        return;
    }
    size_ = static_cast<std::size_t>(status.st_size);
    if (size_ == 0) {
        return;
    }
    void *mapping = ::mmap(nullptr, size_, PROT_READ, MAP_PRIVATE, descriptor_, 0);
    if (mapping == MAP_FAILED) {
        Close();
        return;
    }
    data_ = mapping;
}

MappedReadFile::~MappedReadFile()
{
    if (data_ != nullptr) {
        ::munmap(data_, size_);
    }
    Close();
}

bool MappedReadFile::IsOpen() const
{
    return descriptor_ >= 0;
}

std::string_view MappedReadFile::Content() const
{
    return data_ == nullptr ? std::string_view{} : std::string_view(static_cast<const char *>(data_), size_);
}

void MappedReadFile::Close()
{
    if (descriptor_ >= 0) {
        ::close(descriptor_);
        descriptor_ = -1;
    }
}

DiagnosisToolModule::DiagnosisToolModule() = default;

RackResult DiagnosisToolModule::Initialize()
{
    engine_.reset();
    logTypeToPath_.clear();
    if (ParseDiagArgs() != RACK_OK || ConfigureMergedPath() != RACK_OK) {
        return RACK_FAIL;
    }
    engine_ = DiagnosisEngine::Create(wittyDir_);
    if (!engine_) {
        LOG_ERROR << "failed to initialize data-driven diagnosis engine from: " << wittyDir_;
        return RACK_FAIL;
    }
    engine_->BeginDiagnosis();
    if (ExtractLogsByTimeWindow() != RACK_OK || BuildLogTypeToPathMap() != RACK_OK) {
        return RACK_FAIL;
    }
    engine_->FinishDiagnosis(logTypeToPath_[LOG_TYPE_ACCESS].size(), logTypeToPath_[LOG_TYPE_RUNTIME].size());
    return RACK_OK;
}

void DiagnosisToolModule::UnInitialize()
{
    engine_.reset();
    logTypeToPath_.clear();
    LOG_INFO << "DiagnosisToolModule uninitialized";
}

RackResult DiagnosisToolModule::Start()
{
    if (!engine_) {
        LOG_ERROR << "DiagnosisToolModule is not initialized";
        return RACK_FAIL;
    }
    if (StoreFailureTraces() != RACK_OK) {
        return RACK_FAIL;
    }
    LOG_INFO << "DiagnosisToolModule completed";
    return RACK_OK;
}

void DiagnosisToolModule::Stop()
{
    LOG_INFO << "DiagnosisToolModule stopped";
}

RackResult DiagnosisToolModule::ParseDiagArgs()
{
    const auto &argMap = UbseContext::GetInstance().GetArgMap();
    auto getRequired = [&argMap](const std::string &key, std::string &value) -> RackResult {
        auto iterator = argMap.find(key);
        if (iterator == argMap.end()) {
            LOG_ERROR << "Missing required argument: --" << key;
            return RACK_FAIL;
        }
        value = iterator->second;
        return RACK_OK;
    };
    if (getRequired(ARG_DS_LOG_PATH, dsLogPath_) != RACK_OK || dsLogPath_.empty() || !fs::exists(dsLogPath_) ||
        !fs::is_directory(dsLogPath_)) {
        LOG_ERROR << "--ds-log-path must be an existing directory: " << dsLogPath_;
        return RACK_FAIL;
    }

    auto getOptionalPattern = [&getRequired](const std::string &key, std::string &value) {
        if (getRequired(key, value) != RACK_OK || value.empty()) {
            LOG_WARN << "--" << key << " is empty";
        }
    };
    getOptionalPattern(ARG_DS_CLIENT_ACCESS_LOG, dsClientAccessLogFile_);
    getOptionalPattern(ARG_DS_CLIENT_INFO_LOG, dsClientInfoLogFile_);
    getOptionalPattern(ARG_DS_WORKER_ACCESS_LOG, dsWorkerAccessLogFile_);
    getOptionalPattern(ARG_DS_WORKER_INFO_LOG, dsWorkerInfoLogFile_);
    getOptionalPattern(ARG_RESOURCE_LOG, resourceLogFile_);

    if (getRequired(ARG_START_TIME, startTimeStr_) != RACK_OK || getRequired(ARG_END_TIME, endTimeStr_) != RACK_OK) {
        return RACK_FAIL;
    }
    re2::RE2 timeRegex(TIME_PATTERN);
    if (!re2::RE2::FullMatch(startTimeStr_, timeRegex) || !re2::RE2::FullMatch(endTimeStr_, timeRegex)) {
        LOG_ERROR << "Invalid diagnosis time range format, expected yyyy-mm-dd hh:mm:ss";
        return RACK_FAIL;
    }
    const auto startTimestamp = failure::DatetimeStrToTimestamp(startTimeStr_, true);
    const auto endTimestamp = failure::DatetimeStrToTimestamp(endTimeStr_, true);
    if (!startTimestamp.has_value() || !endTimestamp.has_value() || *startTimestamp >= *endTimestamp) {
        LOG_ERROR << "start-time must be less than end-time";
        return RACK_FAIL;
    }
    auto randomIterator = argMap.find(ARG_RANDOM_STRING);
    if (randomIterator != argMap.end()) {
        randomStr_ = randomIterator->second;
    }
    return RACK_OK;
}

RackResult DiagnosisToolModule::ConfigureMergedPath()
{
    const char *wittyDirEnvironment = std::getenv(WITTY_DIR_ENVIRONMENT);
    wittyDir_ = wittyDirEnvironment ? wittyDirEnvironment : DEFAULT_WITTY_DIR;
    const std::string randomPath = randomStr_.empty() ? DEFAULT_LOG_DIR_NAME : RANDOM_LOG_DIR_PREFIX + randomStr_;
    mergedLogDir_ = (fs::path(wittyDir_) / randomPath).string();

    std::error_code error;
    fs::create_directories(mergedLogDir_, error);
    if (error) {
        LOG_ERROR << "Failed to create extracted log dir: " << mergedLogDir_ << ", error: " << error.message();
        return RACK_FAIL;
    }
    fs::permissions(mergedLogDir_, fs::perms(OUTPUT_DIRECTORY_PERMISSIONS), error);
    for (const auto &entry : fs::directory_iterator(mergedLogDir_, error)) {
        if (error) {
            break;
        }
        fs::remove(entry.path(), error);
        if (error) {
            LOG_ERROR << "Failed to clear output path: " << entry.path() << ", error: " << error.message();
            return RACK_FAIL;
        }
    }
    return RACK_OK;
}

std::vector<std::string> DiagnosisToolModule::FindMatchingFiles(const std::string &dir, const std::string &pattern)
{
    std::vector<std::string> matchedFiles;
    std::vector<std::string_view> patternViews;
    log_helper::SplitView(patternViews, pattern, PATTERN_LIST_DELIMITER);
    const std::vector<std::string> patterns = log_helper::ToStringFields(patternViews);
    std::error_code error;
    for (fs::recursive_directory_iterator iterator(dir, fs::directory_options::skip_permission_denied, error), end;
         iterator != end; iterator.increment(error)) {
        if (error) {
            LOG_WARN << "Failed to iterate log directory: " << dir << ", error: " << error.message();
            break;
        }
        if (!iterator->is_regular_file()) {
            continue;
        }
        const std::string filename = iterator->path().filename().string();
        if (filename.empty() || filename.front() == HIDDEN_FILE_PREFIX) {
            continue;
        }
        const bool matched = std::any_of(patterns.begin(), patterns.end(), [&](const std::string &item) {
            return item.find(WILDCARD_MARKER) == std::string::npos ? filename == item :
                                                                     log_helper::WildcardMatch(item, filename);
        });
        if (matched) {
            matchedFiles.push_back(iterator->path().string());
        }
    }
    std::sort(matchedFiles.begin(), matchedFiles.end());
    return matchedFiles;
}

void DiagnosisToolModule::CollectLogSources(std::unordered_map<std::string, std::vector<std::string>> &outputToSources)
{
    struct LogFilePattern {
        const std::string *pattern;
        const char *argumentName;
    };
    const std::array patterns = {
        LogFilePattern{&dsClientAccessLogFile_, ARG_DS_CLIENT_ACCESS_LOG},
        LogFilePattern{&dsClientInfoLogFile_, ARG_DS_CLIENT_INFO_LOG},
        LogFilePattern{&dsWorkerInfoLogFile_, ARG_DS_WORKER_INFO_LOG},
        LogFilePattern{&dsWorkerAccessLogFile_, ARG_DS_WORKER_ACCESS_LOG},
        LogFilePattern{&resourceLogFile_, ARG_RESOURCE_LOG},
    };

    std::unordered_set<std::string> extractedSourcePaths;
    for (const LogFilePattern &entry : patterns) {
        if (entry.pattern->empty()) {
            continue;
        }
        const std::vector<std::string> files = FindMatchingFiles(dsLogPath_, *entry.pattern);
        if (files.empty()) {
            LOG_WARN << "No files matching --" << entry.argumentName << " '" << *entry.pattern << "' found under "
                     << dsLogPath_;
            continue;
        }
        for (const std::string &sourcePath : files) {
            if (!extractedSourcePaths.insert(sourcePath).second) {
                continue;
            }
            const fs::path outputPath = fs::path(mergedLogDir_) / fs::path(sourcePath).filename();
            outputToSources[outputPath.string()].push_back(sourcePath);
        }
    }
}

void DiagnosisToolModule::ClassifyLogOutputs(
    const std::unordered_map<std::string, std::vector<std::string>> &outputToSources,
    std::vector<std::string> &accessOutputs, std::vector<std::string> &runtimeOutputs,
    std::vector<std::string> &otherOutputs)
{
    for (const auto &[outputPath, sources] : outputToSources) {
        const fs::path filename = fs::path(outputPath).filename();
        const bool access = MatchesAnyPattern(dsClientAccessLogFile_, filename) ||
                            MatchesAnyPattern(dsWorkerAccessLogFile_, filename);
        const bool runtime = MatchesAnyPattern(dsClientInfoLogFile_, filename) ||
                             MatchesAnyPattern(dsWorkerInfoLogFile_, filename);
        if (access) {
            accessOutputs.push_back(outputPath);
        }
        if (runtime) {
            runtimeOutputs.push_back(outputPath);
        }
        if (!access && !runtime) {
            otherOutputs.push_back(outputPath);
        }
    }
    std::sort(accessOutputs.begin(), accessOutputs.end());
    std::sort(runtimeOutputs.begin(), runtimeOutputs.end());
    std::sort(otherOutputs.begin(), otherOutputs.end());
}

RackResult DiagnosisToolModule::ProcessClassifiedOutputs(
    const std::unordered_map<std::string, std::vector<std::string>> &outputToSources,
    const std::vector<std::string> &accessOutputs, const std::vector<std::string> &runtimeOutputs,
    const std::vector<std::string> &otherOutputs)
{
    auto extractOutput = [this, &outputToSources](const std::string &outputPath, LogKind kind) {
        const auto &sources = outputToSources.at(outputPath);
        for (std::size_t index = 0; index < sources.size(); ++index) {
            if (!ExtractLogLinesByTimeWindow(sources[index], outputPath, index != 0, kind)) {
                return false;
            }
        }
        return true;
    };

    std::unordered_set<std::string> extractedOutputs;
    for (const std::string &outputPath : accessOutputs) {
        if (!extractOutput(outputPath, LogKind::ACCESS)) {
            return RACK_FAIL;
        }
        extractedOutputs.insert(outputPath);
    }
    for (const std::string &outputPath : runtimeOutputs) {
        if (extractedOutputs.find(outputPath) != extractedOutputs.end()) {
            if (!FeedExtractedLog(outputPath, LogKind::RUNTIME)) {
                return RACK_FAIL;
            }
        } else {
            if (!extractOutput(outputPath, LogKind::RUNTIME)) {
                return RACK_FAIL;
            }
            extractedOutputs.insert(outputPath);
        }
    }
    for (const std::string &outputPath : otherOutputs) {
        if (!extractOutput(outputPath, LogKind::NONE)) {
            return RACK_FAIL;
        }
    }
    return RACK_OK;
}

RackResult DiagnosisToolModule::ExtractLogsByTimeWindow()
{
    std::unordered_map<std::string, std::vector<std::string>> outputToSources;
    CollectLogSources(outputToSources);
    std::vector<std::string> accessOutputs;
    std::vector<std::string> runtimeOutputs;
    std::vector<std::string> otherOutputs;
    ClassifyLogOutputs(outputToSources, accessOutputs, runtimeOutputs, otherOutputs);
    return ProcessClassifiedOutputs(outputToSources, accessOutputs, runtimeOutputs, otherOutputs);
}

void DiagnosisToolModule::WriteExtractedLine(std::ostream &output, std::string_view line, LogKind kind,
                                             bool useMappedInput, std::vector<std::string_view> &runtimeLines) const
{
    output.write(line.data(), static_cast<std::streamsize>(line.size()));
    output.put('\n');
    if (kind == LogKind::ACCESS) {
        engine_->AnalyzeAccessLine(line);
    } else if (kind == LogKind::RUNTIME) {
        if (useMappedInput) {
            runtimeLines.push_back(line);
        } else {
            engine_->AnalyzeRuntimeLine(line);
        }
    }
}

bool DiagnosisToolModule::ProcessExtractedLine(std::string_view line, LineProcessContext &ctx) const
{
    if (!line.empty() && line.back() == WINDOWS_LINE_END) {
        line.remove_suffix(1);
    }
    const std::string_view timestamp = log_helper::FindTimestampT(line);
    if (timestamp.empty()) {
        if (ctx.inRange) {
            WriteExtractedLine(ctx.output, line, ctx.kind, ctx.useMappedInput, ctx.runtimeLines);
        }
        return true;
    }
    if (timestamp > ctx.endTime) {
        return false;
    }
    if (timestamp < ctx.startTime) {
        ctx.inRange = false;
        return true;
    }
    ctx.inRange = true;
    WriteExtractedLine(ctx.output, line, ctx.kind, ctx.useMappedInput, ctx.runtimeLines);
    return true;
}

bool DiagnosisToolModule::ExtractLogLinesByTimeWindow(const std::string &inputPath, const std::string &outputPath,
                                                      bool append, LogKind kind)
{
    MappedReadFile mappedInput(inputPath);
    std::ifstream fallbackInput;
    if (!mappedInput.IsOpen()) {
        fallbackInput.open(inputPath);
        if (!fallbackInput.is_open()) {
            LOG_ERROR << "Cannot open input file: " << inputPath;
            return false;
        }
    }
    const std::ios_base::openmode mode = std::ios::out | (append ? std::ios::app : std::ios::trunc);
    std::ofstream output(outputPath, mode);
    if (!output.is_open()) {
        LOG_ERROR << "Cannot open output file: " << outputPath;
        return false;
    }
    std::vector<std::string_view> runtimeLines;
    const bool useMappedInput = mappedInput.IsOpen();
    if (kind == LogKind::RUNTIME && useMappedInput) {
        runtimeLines.reserve(mappedInput.Content().size() / ESTIMATED_LOG_LINE_LENGTH);
    }
    const std::string startTime = log_helper::ToTimestampTBound(startTimeStr_);
    const std::string endTime = log_helper::ToTimestampTBound(endTimeStr_);
    bool inRange = false;
    LineProcessContext ctx{startTime, endTime, inRange, output, kind, useMappedInput, runtimeLines};
    if (useMappedInput) {
        const std::string_view content = mappedInput.Content();
        std::size_t offset = 0;
        while (offset < content.size()) {
            const std::size_t end = content.find('\n', offset);
            const std::string_view line = end == std::string_view::npos ? content.substr(offset) :
                                                                          content.substr(offset, end - offset);
            if (!ProcessExtractedLine(line, ctx) || end == std::string_view::npos) {
                break;
            }
            offset = end + 1;
        }
        if (kind == LogKind::RUNTIME) {
            engine_->AnalyzeRuntimeLines(runtimeLines);
        }
    } else {
        std::string line;
        while (std::getline(fallbackInput, line)) {
            if (!ProcessExtractedLine(line, ctx)) {
                break;
            }
        }
    }
    return !fallbackInput.bad() && output.good();
}

bool DiagnosisToolModule::FeedExtractedLog(const std::string &path, LogKind kind)
{
    MappedReadFile mappedInput(path);
    if (mappedInput.IsOpen()) {
        std::vector<std::string_view> lines;
        const std::string_view content = mappedInput.Content();
        lines.reserve(content.size() / ESTIMATED_LOG_LINE_LENGTH);
        std::size_t offset = 0;
        while (offset < content.size()) {
            const std::size_t end = content.find('\n', offset);
            lines.push_back(end == std::string_view::npos ? content.substr(offset) :
                                                            content.substr(offset, end - offset));
            if (end == std::string_view::npos) {
                break;
            }
            offset = end + 1;
        }
        if (kind == LogKind::RUNTIME) {
            engine_->AnalyzeRuntimeLines(lines);
        } else {
            for (std::string_view line : lines) {
                engine_->AnalyzeAccessLine(line);
            }
        }
        return true;
    }

    std::ifstream input(path);
    if (!input.is_open()) {
        LOG_ERROR << "Cannot open extracted log file: " << path;
        return false;
    }
    std::string line;
    while (std::getline(input, line)) {
        if (kind == LogKind::ACCESS) {
            engine_->AnalyzeAccessLine(line);
        } else if (kind == LogKind::RUNTIME) {
            engine_->AnalyzeRuntimeLine(line);
        }
    }
    return !input.bad();
}

RackResult DiagnosisToolModule::BuildLogTypeToPathMap()
{
    logTypeToPath_.clear();
    std::error_code error;
    for (fs::recursive_directory_iterator iterator(mergedLogDir_, fs::directory_options::skip_permission_denied, error),
         end;
         iterator != end; iterator.increment(error)) {
        if (error) {
            LOG_ERROR << "Failed to iterate merged log directory: " << error.message();
            return RACK_FAIL;
        }
        if (!iterator->is_regular_file()) {
            continue;
        }
        const fs::path filename = iterator->path().filename();
        if (MatchesAnyPattern(dsClientAccessLogFile_, filename) ||
            MatchesAnyPattern(dsWorkerAccessLogFile_, filename)) {
            logTypeToPath_[LOG_TYPE_ACCESS].push_back(iterator->path().string());
        }
        if (MatchesAnyPattern(dsClientInfoLogFile_, filename) || MatchesAnyPattern(dsWorkerInfoLogFile_, filename)) {
            logTypeToPath_[LOG_TYPE_RUNTIME].push_back(iterator->path().string());
        }
    }
    for (auto &[type, paths] : logTypeToPath_) {
        std::sort(paths.begin(), paths.end());
        paths.erase(std::unique(paths.begin(), paths.end()), paths.end());
    }
    return RACK_OK;
}

RackResult DiagnosisToolModule::StoreFailureTraces() const
{
    const fs::path outputPath = fs::path(mergedLogDir_) / OUTPUT_FILENAME_FAILURE_TRACE;
    std::ofstream output(outputPath, std::ios::out | std::ios::trunc);
    if (!output.is_open()) {
        LOG_ERROR << "Failed to open failure trace output: " << outputPath;
        return RACK_FAIL;
    }

    std::vector<std::string> traceIds;
    traceIds.reserve(engine_->GetTraceLogs().size());
    for (const auto &[traceId, logs] : engine_->GetTraceLogs()) {
        traceIds.push_back(traceId);
    }
    std::sort(traceIds.begin(), traceIds.end());
    for (const std::string &traceId : traceIds) {
        for (const auto &log : engine_->GetTraceLogs().at(traceId)) {
            if (!log || log->rawLog.empty() || log->failureModeIds.empty()) {
                continue;
            }
            for (std::size_t index = 0; index < log->failureModeIds.size(); ++index) {
                if (index != 0) {
                    output << ',';
                }
                output << log->failureModeIds[index];
            }
            output << FAILURE_TRACE_DELIMITER << log->rawLog << '\n';
        }
    }
    return output.good() ? RACK_OK : RACK_FAIL;
}

} // namespace diag
