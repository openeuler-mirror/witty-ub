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

#ifndef FAILURE_LOG_HELPER_H
#define FAILURE_LOG_HELPER_H

#include <string>
#include <string_view>
#include <vector>

namespace diag {
namespace log_helper {
inline constexpr std::string_view DELIM = " | ";

bool WildcardMatch(const std::string &pattern, const std::string &path);
void SplitView(std::vector<std::string_view> &out, std::string_view str, std::string_view delim,
               bool keepEmpty = false);
bool ExtractSingleField(std::string_view &out, std::string_view str, std::string_view delim, int idx);
bool IsDigit(char ch);
bool IsTimestampTAt(std::string_view line, size_t pos);
std::string_view FindTimestampT(std::string_view line);
std::string ToTimestampTBound(std::string timestamp);
std::string_view TrimView(std::string_view str);
bool ParseInt(std::string_view str, int &value);
std::vector<std::string> ToStringFields(const std::vector<std::string_view> &fieldViews);
std::string Trim(const std::string &str);
} // namespace log_helper
} // namespace diag

#endif // FAILURE_LOG_HELPER_H
