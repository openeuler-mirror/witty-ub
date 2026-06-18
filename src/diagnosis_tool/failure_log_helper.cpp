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

#include <fnmatch.h>

namespace diag {
namespace log_helper {
bool WildcardMatch(const std::string &pattern, const std::string &path)
{
    return fnmatch(pattern.c_str(), path.c_str(), 0) == 0;
}

void Split(std::vector<std::string> &out, const std::string &str, std::string_view delim, bool keepEmpty)
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
        if (j == std::string::npos) {
            if (keepEmpty || i < str.size()) {
                out.emplace_back(str, i);
            }
            break;
        }
        if (keepEmpty || j > i) {
            out.emplace_back(str, i, j - i);
        }
        i = j + delim.size();
    }
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