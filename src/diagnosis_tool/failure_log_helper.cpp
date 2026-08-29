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

#include "failure_log_helper.h"

#include <cctype>
#include <charconv>
#include <system_error>

#include <fnmatch.h>

namespace diag {
namespace log_helper {
namespace {
constexpr std::string_view TIMESTAMP_T_PATTERN = "dddd-dd-ddTdd:dd:dd";
constexpr char TIMESTAMP_DIGIT_PLACEHOLDER = 'd';
constexpr char TIMESTAMP_T_SEPARATOR = 'T';
constexpr char TIMESTAMP_BOUND_SEPARATOR = ' ';
constexpr std::size_t TIMESTAMP_DATE_SIZE = 10;
constexpr std::size_t DEFAULT_FIELD_CAPACITY = 8;
constexpr int FNMATCH_FLAGS = 0;
} // namespace

bool WildcardMatch(const std::string &pattern, const std::string &path)
{
    return fnmatch(pattern.c_str(), path.c_str(), FNMATCH_FLAGS) == 0;
}

void SplitView(std::vector<std::string_view> &out, std::string_view str, std::string_view delim, bool keepEmpty)
{
    out.clear();
    out.reserve(DEFAULT_FIELD_CAPACITY);
    if (delim.empty()) {
        if (keepEmpty || !str.empty()) {
            out.emplace_back(str);
        }
        return;
    }
    std::size_t i = 0;
    while (true) {
        const std::size_t j = str.find(delim, i);
        if (j == std::string_view::npos) {
            if (keepEmpty || i < str.size()) {
                out.emplace_back(str.substr(i));
            }
            break;
        }
        if (keepEmpty || j > i) {
            out.emplace_back(str.substr(i, j - i));
        }
        i = j + delim.size();
    }
}

bool IsDigit(char ch)
{
    return ch >= '0' && ch <= '9';
}

bool IsTimestampTAt(std::string_view line, std::size_t pos)
{
    if (pos + TIMESTAMP_T_PATTERN.size() > line.size()) {
        return false;
    }
    for (std::size_t index = 0; index < TIMESTAMP_T_PATTERN.size(); ++index) {
        const char expected = TIMESTAMP_T_PATTERN[index];
        const bool matches = expected == TIMESTAMP_DIGIT_PLACEHOLDER ? IsDigit(line[pos + index]) :
                                                                       line[pos + index] == expected;
        if (!matches) {
            return false;
        }
    }
    return true;
}

std::string_view FindTimestampT(std::string_view line)
{
    std::size_t searchPos = 0;
    while (true) {
        const std::size_t tPos = line.find(TIMESTAMP_T_SEPARATOR, searchPos);
        if (tPos == std::string_view::npos) {
            return {};
        }
        if (tPos >= TIMESTAMP_DATE_SIZE) {
            const std::size_t timestampPos = tPos - TIMESTAMP_DATE_SIZE;
            if (IsTimestampTAt(line, timestampPos)) {
                return line.substr(timestampPos, TIMESTAMP_T_PATTERN.size());
            }
        }
        searchPos = tPos + 1;
    }
}

std::string ToTimestampTBound(std::string timestamp)
{
    if (timestamp.size() > TIMESTAMP_DATE_SIZE && timestamp[TIMESTAMP_DATE_SIZE] == TIMESTAMP_BOUND_SEPARATOR) {
        timestamp[TIMESTAMP_DATE_SIZE] = TIMESTAMP_T_SEPARATOR;
    }
    return timestamp;
}

std::string_view TrimView(std::string_view str)
{
    std::size_t begin = 0;
    while (begin < str.size() && std::isspace(static_cast<unsigned char>(str[begin]))) {
        begin++;
    }
    std::size_t end = str.size();
    while (end > begin && std::isspace(static_cast<unsigned char>(str[end - 1]))) {
        end--;
    }
    return str.substr(begin, end - begin);
}

bool ParseInt(std::string_view str, int &value)
{
    str = TrimView(str);
    if (str.empty()) {
        return false;
    }
    int parsed = 0;
    const auto *begin = str.data();
    const auto *end = str.data() + str.size();
    const auto [ptr, ec] = std::from_chars(begin, end, parsed);
    if (ec != std::errc() || ptr != end) {
        return false;
    }
    value = parsed;
    return true;
}

std::vector<std::string> ToStringFields(const std::vector<std::string_view> &fieldViews)
{
    std::vector<std::string> fields;
    fields.reserve(fieldViews.size());
    for (std::string_view field : fieldViews) {
        fields.emplace_back(field);
    }
    return fields;
}

std::string Trim(const std::string &str)
{
    std::size_t begin = 0;
    while (begin < str.size() && std::isspace(static_cast<unsigned char>(str[begin]))) {
        begin++;
    }
    std::size_t end = str.size();
    while (end > begin && std::isspace(static_cast<unsigned char>(str[end - 1]))) {
        end--;
    }
    return str.substr(begin, end - begin);
}
} // namespace log_helper
} // namespace diag
