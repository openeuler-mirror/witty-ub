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

#ifndef FAILURE_MODE_CONTROLLER_H
#define FAILURE_MODE_CONTROLLER_H

#include <memory>
#include <unordered_map>
#include <unordered_set>

#include "failure_log_info.h"
#include "failure_mode.h"

namespace diag {
using TraceIdToFailureLogInfoMap = std::unordered_map<std::string, std::shared_ptr<FailureLogInfo>>;

class FailureModeController final {
public:
    explicit FailureModeController(std::shared_ptr<FailureMode> failureMode);
    ~FailureModeController() = default;
    std::shared_ptr<FailureMode> GetFailureMode() const;
    int GetHitCount() const;
    const TraceIdToFailureLogInfoMap &GetTraceIdToFailureLogInfo() const;
    const std::unordered_set<std::string> &GetSubValidFailureModeIds() const;
    void Hit(const std::string &traceId, std::shared_ptr<FailureLogInfo> failureLogInfo);
    void InsertSubValidFailureModeId(const std::string &failureModeId);

private:
    std::shared_ptr<FailureMode> failureMode_;
    int hitCount_;
    TraceIdToFailureLogInfoMap traceIdToFailureLogInfo_;
    std::unordered_set<std::string> subValidFailureModeIds_;
};
} // namespace diag

#endif // FAILURE_MODE_CONTROLLER_H
