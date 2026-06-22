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

#include <charconv>
#include <cctype>
#include <fnmatch.h>
#include <system_error>

namespace diag {
namespace log_helper {
bool WildcardMatch(const std::string &pattern, const std::string &path)
{
    return fnmatch(pattern.c_str(), path.c_str(), 0) == 0;
}

void SplitView(std::vector<std::string_view> &out, std::string_view str, std::string_view delim, bool keepEmpty)
{
    out.clear();
    out.reserve(8);
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

bool ExtractSingleField(std::string_view &out, std::string_view str, std::string_view delim, int idx)
{
    out = {};
    if (idx < 0) {
        return false;
    }
    if (delim.empty()) {
        if (idx != 0) {
            return false;
        }
        out = str;
        return true;
    }

    std::size_t begin = 0;
    for (int i = 0; i < idx; i++) {
        const std::size_t pos = str.find(delim, begin);
        if (pos == std::string::npos) {
            return false;
        }
        begin = pos + delim.size();
    }

    const std::size_t end = str.find(delim, begin);
    out = str.substr(begin, end == std::string::npos ? std::string::npos : end - begin);
    return true;
}

std::string_view TrimView(std::string_view str)
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
} // namespace log_helper
} // namespace diag
