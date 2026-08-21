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

#include "log_collector.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <fstream>
#include <limits>
#include <string_view>
#include <utility>
#include <vector>
#include "logger.h"
#include "time_utils.h"

namespace brpc {

constexpr int NUM_10 = 10;
constexpr int TIME_STR_LENGTH = 24;
constexpr int INDEX_0 = 0;
constexpr int INDEX_1 = 1;
constexpr int INDEX_2 = 2;
constexpr int INDEX_3 = 3;
constexpr int INDEX_4 = 4;
constexpr int INDEX_5 = 5;
constexpr int INDEX_6 = 6;
constexpr int INDEX_8 = 8;
constexpr int INDEX_9 = 9;
constexpr int INDEX_11 = 11;
constexpr int INDEX_12 = 12;
constexpr int INDEX_14 = 14;
constexpr int INDEX_15 = 15;
constexpr int INDEX_17 = 17;
constexpr int INDEX_18 = 18;
constexpr size_t COUNT_2 = 2;
constexpr size_t COUNT_4 = 4;
constexpr size_t COUNT_6 = 6;
constexpr size_t URMA_FIELDS_SIZE = 4;
constexpr size_t BRPC_FIELDS_SIZE = 7;

bool LogCollector::ParseNonnegativeInt(std::string_view value, int &result)
{
    if (value.empty()) {
        return false;
    }
    std::int64_t parsed = 0;
    for (char ch : value) {
        if (ch < '0' || ch > '9') {
            return false;
        }
        parsed = parsed * NUM_10 + ch - '0';
        if (parsed > std::numeric_limits<int>::max()) {
            return false;
        }
    }
    result = static_cast<int>(parsed);
    return true;
}

bool LogCollector::ParseLogTimestamp(std::string_view timestampText, std::int64_t &timestamp)
{
    if (timestampText.size() != TIME_STR_LENGTH || timestampText[INDEX_8] != ' ' || timestampText[INDEX_11] != ':' ||
        timestampText[INDEX_14] != ':' || timestampText[INDEX_17] != '.') {
        return false;
    }
    time::CivilTime parsed;
    if (!time::ParseFixedInt(timestampText, INDEX_0, COUNT_4, parsed.year) ||
        !time::ParseFixedInt(timestampText, INDEX_4, COUNT_2, parsed.month) ||
        !time::ParseFixedInt(timestampText, INDEX_6, COUNT_2, parsed.day) ||
        !time::ParseFixedInt(timestampText, INDEX_9, COUNT_2, parsed.hour) ||
        !time::ParseFixedInt(timestampText, INDEX_12, COUNT_2, parsed.minute) ||
        !time::ParseFixedInt(timestampText, INDEX_15, COUNT_2, parsed.second) ||
        !time::ParseFixedInt(timestampText, INDEX_18, COUNT_6, parsed.microsecond)) {
        return false;
    }
    return time::BuildUtc8Timestamp(parsed, timestamp);
}

template <std::size_t FieldCount>
bool LogCollector::ExtractBracketFields(std::string_view text, std::array<std::string_view, FieldCount> &fields,
                                        std::size_t &offset)
{
    offset = 0;
    for (auto &field : fields) {
        if (offset >= text.size() || text[offset] != '[') {
            return false;
        }
        std::size_t end = text.find(']', offset + 1);
        if (end == std::string_view::npos) {
            return false;
        }
        field = text.substr(offset + 1, end - offset - 1);
        offset = end + 1;
    }
    return true;
}

bool LogCollector::ParseLocation(std::string_view location, std::string &filename, std::string &functionName,
                                 int &lineNo)
{
    const std::size_t firstColon = location.find(':');
    const std::size_t lastColon = location.rfind(':');
    if (firstColon == std::string_view::npos || firstColon == lastColon || firstColon == 0 ||
        lastColon + 1 >= location.size()) {
        return false;
    }
    filename = std::string(location.substr(0, firstColon));
    functionName = std::string(location.substr(firstColon + 1, lastColon - firstColon - 1));
    return !functionName.empty() && ParseNonnegativeInt(location.substr(lastColon + 1), lineNo);
}

bool LogCollector::ParseThreadId(std::string_view value, std::optional<int> &threadId)
{
    if (value == "-") {
        threadId.reset();
        return true;
    }
    int parsedThreadId = 0;
    if (!ParseNonnegativeInt(value, parsedThreadId)) {
        return false;
    }
    threadId = parsedThreadId;
    return true;
}

bool LogCollector::ParseTraceId(std::string_view value, std::optional<std::string> &traceId)
{
    if (value == "-") {
        traceId.reset();
        return true;
    }
    if (value.empty()) {
        return false;
    }
    traceId = std::string(value);
    return true;
}

// 内层 URMA 日志格式：
// [URMA][thread_id=<id>][<trace_id>|-][filename:function_name:line_number]message
bool LogCollector::ParseUrmaLogFields(std::string_view urmaText, UrmaLogFields &result)
{
    std::array<std::string_view, URMA_FIELDS_SIZE> fields;
    std::size_t messageOffset = 0;
    if (!ExtractBracketFields(urmaText, fields, messageOffset)) {
        return false;
    }

    constexpr std::string_view THREAD_ID_PREFIX = "thread_id=";
    if (fields[INDEX_1].substr(0, THREAD_ID_PREFIX.size()) != THREAD_ID_PREFIX ||
        !ParseThreadId(fields[INDEX_1].substr(THREAD_ID_PREFIX.size()), result.threadId) ||
        !result.threadId.has_value()) {
        return false;
    }
    if (!ParseTraceId(fields[INDEX_2], result.traceId) ||
        !ParseLocation(fields[INDEX_3], result.filename, result.functionName, result.lineNo)) {
        return false;
    }
    return true;
}

bool LogCollector::ExtractLogTimestamp(std::string_view text, std::int64_t &timestamp)
{
    constexpr std::size_t timestampLength = 24;
    return text.size() > timestampLength + 1 && text.front() == '[' && text[timestampLength + 1] == ']' &&
           ParseLogTimestamp(text.substr(1, timestampLength), timestamp);
}

LogCollector::LogCollector(std::filesystem::path brpcLogPath) : brpcLogPath_(std::move(brpcLogPath)) {}

std::int64_t LogCollector::CurrentTimestamp()
{
    return std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::system_clock::now().time_since_epoch())
        .count();
}

bool LogCollector::ParseBrpcLogFields(BrpcLog &logEntry)
{
    std::array<std::string_view, BRPC_FIELDS_SIZE> fields;
    std::size_t offset = 0;
    if (!ExtractBracketFields(logEntry.text, fields, offset)) {
        return false;
    }
    std::string filename;
    std::string functionName;
    int lineNo = 0;
    if (!ParseLocation(fields[INDEX_4], filename, functionName, lineNo)) {
        return false;
    }
    std::optional<int> threadId;
    if (!ParseThreadId(fields[INDEX_5], threadId)) {
        return false;
    }
    std::optional<std::string> traceId;
    if (!ParseTraceId(fields[INDEX_6], traceId)) {
        return false;
    }
    std::string component(fields[INDEX_3]);
    std::string message = logEntry.text.substr(offset);

    const std::size_t urmaOffset = message.find(URMA_LOG_PREFIX);
    if (urmaOffset != std::string::npos) {
        UrmaLogFields urmaFields;
        if (!ParseUrmaLogFields(std::string_view(message).substr(urmaOffset), urmaFields)) {
            return false;
        }
        component = std::string(URMA_COMPONENT);
        filename = std::move(urmaFields.filename);
        functionName = std::move(urmaFields.functionName);
        lineNo = urmaFields.lineNo;
        threadId = urmaFields.threadId;
        traceId = std::move(urmaFields.traceId);
    }

    logEntry.podName = std::string(fields[INDEX_1]);
    logEntry.podIp = std::string(fields[INDEX_2]);
    logEntry.component = std::move(component);
    logEntry.filename = std::move(filename);
    logEntry.functionName = std::move(functionName);
    logEntry.lineNo = lineNo;
    logEntry.threadId = threadId;
    logEntry.traceId = std::move(traceId);
    logEntry.message = std::move(message);
    return true;
}

// 流式读取 BRPC 日志并按时间范围交给调用方处理。
// brpcLogPath_ 可以是单个日志文件，也可以是包含多个日志文件的目录。
bool LogCollector::ForEachBrpcLog(std::int64_t startTimestamp, std::int64_t endTimestamp,
                                  const BrpcLogConsumer &consumer) const
{
    std::vector<std::filesystem::path> filePaths;
    if (std::filesystem::is_directory(brpcLogPath_)) {
        for (const auto &entry : std::filesystem::recursive_directory_iterator(brpcLogPath_)) {
            if (entry.is_regular_file()) {
                filePaths.push_back(entry.path());
            }
        }
        std::sort(filePaths.begin(), filePaths.end());
    } else if (std::filesystem::is_regular_file(brpcLogPath_)) {
        filePaths.push_back(brpcLogPath_);
    } else {
        LOG_ERROR << "brpc log path is neither a file nor a directory: " << brpcLogPath_.string();
        return false;
    }

    if (filePaths.empty()) {
        LOG_ERROR << "no files found in brpc log path: " << brpcLogPath_.string();
        return false;
    }

    if (startTimestamp >= endTimestamp) {
        LOG_INFO << "brpc log timestamp range is empty: [" << startTimestamp << ", " << endTimestamp << "]";
        return true;
    }

    std::size_t totalLogCount = 0;
    std::size_t totalInvalidTimestampCount = 0;
    std::size_t totalInvalidFormatCount = 0;
    for (const auto &filePath : filePaths) {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            LOG_ERROR << "failed to open log file: " << filePath.string();
            return false;
        }

        std::size_t logCount = 0;
        std::size_t invalidTimestampCount = 0;
        std::size_t invalidFormatCount = 0;
        std::string line;
        while (std::getline(file, line)) {
            std::int64_t logTimestamp = 0;
            if (!ExtractLogTimestamp(line, logTimestamp)) {
                ++invalidTimestampCount;
                continue;
            }
            if (logTimestamp < startTimestamp || logTimestamp >= endTimestamp) {
                continue;
            }
            BrpcLog logEntry;
            logEntry.text = std::move(line);
            logEntry.timestamp = logTimestamp;
            if (!ParseBrpcLogFields(logEntry)) {
                ++invalidFormatCount;
            }
            consumer(std::move(logEntry));
            ++logCount;
        }
        if (file.bad()) {
            LOG_ERROR << "failed while reading log file: " << filePath.string();
            return false;
        }

        totalLogCount += logCount;
        totalInvalidTimestampCount += invalidTimestampCount;
        totalInvalidFormatCount += invalidFormatCount;

        LOG_INFO << "processed " << logCount << " brpc log entries from " << filePath.string()
                 << " in timestamp range [" << startTimestamp << ", " << endTimestamp
                 << "], skipped " << invalidTimestampCount << " entries with invalid timestamp, retained "
                 << invalidFormatCount << " entries with invalid format as raw text";
    }

    LOG_INFO << "processed total " << totalLogCount << " brpc log entries from " << filePaths.size()
             << " files in timestamp range [" << startTimestamp << ", " << endTimestamp
             << "], skipped " << totalInvalidTimestampCount << " entries with invalid timestamp, retained "
             << totalInvalidFormatCount << " entries with invalid format as raw text";
    return true;
}

} // namespace brpc
