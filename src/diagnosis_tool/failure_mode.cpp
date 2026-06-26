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

#include "failure_mode.h"
#include <iostream>
#include <memory>
namespace diag {
bool RootCause::IsFinalRootCause()
{
    return isFinalRootCause;
}

std::string RootCause::GetRootCause()
{
    return rootCause;
}

void FailureMode::PrintDesc()
{
    std::cout << "故障模式: " << GetName() << std::endl;
    std::cout << "故障表现: " << GetValidationMethodDesc() << std::endl;
    std::cout << "故障根因: " << GetRootCauseDesc() << std::endl;
    std::cout << "修复建议: " << GetFixSuggDesc() << std::endl;
}

void FailureMode::AddSubFailureMode(std::string failureModeId)
{
    subFailureModes.push_back(failureModeId);
    return;
}

std::vector<std::string> FailureMode::GetSubFailureModes()
{
    return subFailureModes;
}

RootCause FailureMode::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}
} // namespace diag