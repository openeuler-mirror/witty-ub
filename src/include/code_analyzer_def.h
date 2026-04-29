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

#ifndef CODE_ANALYZER_DEF_H
#define CODE_ANALYZER_DEF_H

#include <optional>
#include <string>
#include <unordered_map>

namespace code_analyzer {
struct OpencodeConnection {
    std::string url;
    int port;
    std::optional<std::string> username;
    std::optional<std::string> passwd;
};

struct SkillInput {
    std::unordered_map<std::string, std::string> componentsPaths;
    std::unordered_map<std::string, std::string> compileCommandsPaths;
};
} // namespace code_analyzer

#endif // CODE_ANALYZER_DEF_H
