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

#include "failure_mode_controller.h"

namespace diag {
FailureModeController::FailureModeController(std::shared_ptr<FailureMode> failureMode)
    : failureMode_(failureMode),
      hitCount_(0)
{
}

std::shared_ptr<FailureMode> FailureModeController::GetFailureMode() const
{
    return failureMode_;
}

int FailureModeController::GetHitCount() const
{
    return hitCount_;
}

const std::unordered_map<std::string, std::shared_ptr<FailureLogInfo>> &
FailureModeController::GetTraceIdToFailureLogInfo() const
{
    return traceIdToFailureLogInfo_;
}

const std::unordered_set<std::string> &FailureModeController::GetSubValidFailureModeIds() const
{
    return subValidFailureModeIds_;
}

void FailureModeController::Hit(const std::string &traceId, std::shared_ptr<FailureLogInfo> failureLogInfo)
{
    if (traceIdToFailureLogInfo_.find(traceId) == traceIdToFailureLogInfo_.end()) {
        ++hitCount_;
        traceIdToFailureLogInfo_[traceId] = failureLogInfo;
    }
}
void FailureModeController::InsertSubValidFailureModeId(const std::string &failureModeId)
{
    subValidFailureModeIds_.insert(failureModeId);
}
} // namespace diag
