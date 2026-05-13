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

#ifndef FAILURE_VIEW_H
#define FAILURE_VIEW_H

#include <unordered_map>

#include <json/json.h>

#include "rack_error.h"
#include "failure_def.h"

namespace failure::log {
class LogView final {
public:
    RackResult Build(const std::vector<FailureMetadata> &metadata, const graph::CallGraph &graph);
    RackResult Dump() const;

private:
    Json::Value root_;
};
} // namespace failure::log

#endif // FAILURE_VIEW_H
