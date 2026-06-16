#include "urma_log_helper.h"

#include <array>
#include <cctype>
#include <cstdio>
#include <memory>
#include <optional>
#include <sstream>
#include <unordered_map>

#include "failure_def.h"

namespace diag {
namespace urma_log_helper {
namespace {

constexpr const int CMD_LEN = 128;
constexpr const int SEPERATOR_NUM = 7;
constexpr const int TIME_IDX = 0;
constexpr const int LEVEL_IDX = 1;
constexpr const int FILENAME_IDX = 2;
constexpr const int PODNAME_IDX = 3;
constexpr const int PID_TID_IDX = 4;
constexpr const int TRACE_IDX = 5;
constexpr const int CLUSTERNAME_IDX = 6;
constexpr const int PID_TID_SIZE = 2;

struct FileLocation {
    std::string filename;
    int lineNo;
};

struct ProcessIds {
    int pid;
    int tid;
};

struct ParsedLogLineParts {
    std::string rawLog;
    std::vector<std::string> fields;
    std::string message;
    int64_t timestamp;
    LevelOption level;
    FileLocation fileLocation;
    ProcessIds processIds;
};

std::string Trim(const std::string &str)
{
    size_t begin = 0;
    while (begin < str.size() && std::isspace(static_cast<unsigned char>(str[begin]))) {
        begin++;
    }

    size_t end = str.size();
    while (end > begin && std::isspace(static_cast<unsigned char>(str[end - 1]))) {
        end--;
    }
    return str.substr(begin, end - begin);
}

bool ToInt(const std::string &str, int &value)
{
    std::string trimmed = Trim(str);
    if (trimmed.empty()) {
        return false;
    }

    size_t pos = 0;
    try {
        value = std::stoi(trimmed, &pos);
    } catch (...) {
        return false;
    }
    return pos == trimmed.size();
}

std::optional<LevelOption> ParseLevel(const std::string &level)
{
    const std::string trimmed = Trim(level);
    if (trimmed == "I") {
        return LevelOption::INFO;
    }
    if (trimmed == "D") {
        return LevelOption::DEBUG;
    }
    if (trimmed == "W") {
        return LevelOption::WARN;
    }
    if (trimmed == "E") {
        return LevelOption::ERROR;
    }
    return std::nullopt;
}

bool FindLogHeaderSeparators(const std::string &line, std::vector<size_t> &separators)
{
    separators.reserve(SEPERATOR_NUM);
    size_t start = 0;
    while (separators.size() < SEPERATOR_NUM) {
        size_t pos = line.find('|', start);
        if (pos == std::string::npos) {
            return false;
        }
        separators.emplace_back(pos);
        start = pos + 1;
    }
    return true;
}

bool SplitLogHeaderFields(const std::string &line, const std::vector<size_t> &separators,
    std::vector<std::string> &fields)
{
    failure::Split(fields, line.substr(0, separators.back()), '|', true);
    return fields.size() == SEPERATOR_NUM;
}

std::optional<FileLocation> ParseFileLocation(const std::vector<std::string> &fields)
{
    std::string filenameLine = Trim(fields[FILENAME_IDX]);
    size_t lineNoSep = filenameLine.rfind(':');
    if (lineNoSep == std::string::npos) {
        return std::nullopt;
    }

    int lineNo = 0;
    if (!ToInt(filenameLine.substr(lineNoSep + 1), lineNo)) {
        return std::nullopt;
    }

    return FileLocation {Trim(filenameLine.substr(0, lineNoSep)), lineNo};
}

std::optional<ProcessIds> ParseProcessIds(const std::vector<std::string> &fields)
{
    std::vector<std::string> pidTid;
    failure::Split(pidTid, fields[PID_TID_IDX], ':', true);
    if (pidTid.size() != PID_TID_SIZE) {
        return std::nullopt;
    }

    int pid = 0;
    int tid = 0;
    if (!ToInt(pidTid[0], pid) || !ToInt(pidTid[1], tid)) {
        return std::nullopt;
    }

    return ProcessIds {pid, tid};
}

void FillFailureLogInfo(const ParsedLogLineParts &parts, FailureLogInfo &logInfo)
{
    logInfo.rawLog = parts.rawLog;
    logInfo.timestamp = parts.timestamp;
    logInfo.level = parts.level;
    logInfo.filename = parts.fileLocation.filename;
    logInfo.lineNo = parts.fileLocation.lineNo;
    logInfo.podName = Trim(parts.fields[PODNAME_IDX]);
    logInfo.pid = parts.processIds.pid;
    logInfo.tid = parts.processIds.tid;
    logInfo.traceId = Trim(parts.fields[TRACE_IDX]);
    logInfo.clusterName = Trim(parts.fields[CLUSTERNAME_IDX]);
    logInfo.message = parts.message;
}

bool ParseSingleFailureLogLine(std::string &line, FailureLogInfo &logInfo)
{
    std::string rawLog = line;
    std::vector<size_t> separators;
    if (!FindLogHeaderSeparators(line, separators)) {
        return false;
    }

    std::vector<std::string> fields;
    if (!SplitLogHeaderFields(line, separators, fields)) {
        return false;
    }

    auto timestamp = failure::DatetimeStrToTimestamp(Trim(fields[TIME_IDX]));
    auto level = ParseLevel(fields[LEVEL_IDX]);
    if (!timestamp.has_value() || !level.has_value()) {
        return false;
    }

    auto fileLocation = ParseFileLocation(fields);
    auto processIds = ParseProcessIds(fields);
    if (!fileLocation.has_value() || !processIds.has_value()) {
        return false;
    }

    ParsedLogLineParts parts {
        rawLog,
        fields,
        Trim(line.substr(separators.back() + 1)),
        *timestamp,
        *level,
        *fileLocation,
        *processIds,
    };
    FillFailureLogInfo(parts, logInfo);
    return true;
}

std::unordered_map<const FailureLogInfo *, std::vector<FailureLogInfo>> &ParsedFailureLogLines()
{
    static std::unordered_map<const FailureLogInfo *, std::vector<FailureLogInfo>> parsedLogLines;
    return parsedLogLines;
}

} // namespace

std::string RunCommand(const std::string &cmd)
{
    std::array<char, CMD_LEN> buffer;
    std::string result;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd.c_str(), "r"), pclose);
    if (!pipe) {
        return "";
    }
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
}

bool ParseFailureLogLine(const std::string &line, FailureLogInfo &logInfo)
{
    std::vector<FailureLogInfo> parsedLogInfos;
    std::istringstream iss(line);
    std::string currentLine;
    while (std::getline(iss, currentLine)) {
        FailureLogInfo currentLogInfo;
        if (ParseSingleFailureLogLine(currentLine, currentLogInfo)) {
            parsedLogInfos.push_back(currentLogInfo);
        }
    }

    if (parsedLogInfos.empty()) {
        ParsedFailureLogLines().erase(&logInfo);
        return false;
    }

    logInfo = parsedLogInfos.front();
    ParsedFailureLogLines()[&logInfo] = parsedLogInfos;
    return true;
}

const std::vector<FailureLogInfo> &GetParsedFailureLogLines(const FailureLogInfo &logInfo)
{
    static const std::vector<FailureLogInfo> empty;
    auto iter = ParsedFailureLogLines().find(&logInfo);
    if (iter == ParsedFailureLogLines().end()) {
        return empty;
    }
    return iter->second;
}

} // namespace urma_log_helper
} // namespace diag
