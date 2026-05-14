#pragma once

#include <array>
#include <cctype>
#include <cstdio>
#include <memory>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

#include "../../failure_log_info.h"
#include "failure_def.h"

namespace diag {
namespace urma_log_helper {

inline std::string Trim(const std::string &str)
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

inline bool ToInt(const std::string &str, int &value)
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

inline std::optional<LevelOption> ParseLevel(const std::string &level)
{
    const std::string trimmed = Trim(level);
    if (trimmed == "I") {
        return INFO;
    }
    if (trimmed == "D") {
        return DEBUG;
    }
    if (trimmed == "W") {
        return WARN;
    }
    if (trimmed == "E") {
        return ERROR;
    }
    return std::nullopt;
}

inline std::string RunCommand(const std::string &cmd)
{
    std::array<char, 128> buffer;
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

inline bool ParseFailureLogLine(const std::string &line, FailureLogInfo &logInfo)
{
    std::vector<size_t> separators;
    separators.reserve(7);

    size_t start = 0;
    while (separators.size() < 7) {
        size_t pos = line.find('|', start);
        if (pos == std::string::npos) {
            return false;
        }
        separators.emplace_back(pos);
        start = pos + 1;
    }

    std::vector<std::string> fields;
    failure::Split(fields, line.substr(0, separators.back()), '|', true);
    if (fields.size() != 7) {
        return false;
    }

    auto timestamp = failure::DatetimeStrToTimestamp(Trim(fields[0]));
    auto level = ParseLevel(fields[1]);
    if (!timestamp.has_value() || !level.has_value()) {
        return false;
    }

    std::string filenameLine = Trim(fields[2]);
    size_t lineNoSep = filenameLine.rfind(':');
    if (lineNoSep == std::string::npos) {
        return false;
    }

    int lineNo = 0;
    if (!ToInt(filenameLine.substr(lineNoSep + 1), lineNo)) {
        return false;
    }

    std::vector<std::string> pidTid;
    failure::Split(pidTid, fields[4], ':', true);
    if (pidTid.size() != 2) {
        return false;
    }

    int pid = 0;
    int tid = 0;
    if (!ToInt(pidTid[0], pid) || !ToInt(pidTid[1], tid)) {
        return false;
    }

    logInfo.timestamp = *timestamp;
    logInfo.level = *level;
    logInfo.filename = Trim(filenameLine.substr(0, lineNoSep));
    logInfo.lineNo = lineNo;
    logInfo.podName = Trim(fields[3]);
    logInfo.pid = pid;
    logInfo.tid = tid;
    logInfo.traceId = Trim(fields[5]);
    logInfo.clusterName = Trim(fields[6]);
    logInfo.message = Trim(line.substr(separators.back() + 1));
    return true;
}

} // namespace urma_log_helper
} // namespace diag
