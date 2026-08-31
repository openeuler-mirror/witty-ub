/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of the Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#include "failure_mode.h"

#include <utility>

namespace diag {

FailureMode::FailureMode(FailureModeDescriptor desc)
    : id_(std::move(desc.id)),
      name_(std::move(desc.name)),
      phenomenon_(std::move(desc.phenomenon)),
      cause_(std::move(desc.cause)),
      suggestion_(std::move(desc.suggestion)),
      filename_(std::move(desc.filename)),
      functionName_(std::move(desc.functionName)),
      errorCode_(std::move(desc.errorCode)),
      nodeType_(desc.nodeType)
{
}

const std::string &FailureMode::GetId() const
{
    return id_;
}
const std::string &FailureMode::GetName() const
{
    return name_;
}
const std::string &FailureMode::GetPhenomenon() const
{
    return phenomenon_;
}
const std::string &FailureMode::GetRootCauseDesc() const
{
    return cause_;
}
const std::string &FailureMode::GetFixSuggDesc() const
{
    return suggestion_;
}
const std::string &FailureMode::GetValidationMethodDesc() const
{
    return phenomenon_;
}
const std::string &FailureMode::GetFilename() const
{
    return filename_;
}
const std::string &FailureMode::GetFunctionName() const
{
    return functionName_;
}
const std::optional<std::string> &FailureMode::GetErrorCode() const
{
    return errorCode_;
}
FailureModeNodeType FailureMode::GetNodeType() const
{
    return nodeType_;
}
bool FailureMode::IsPublicInterface() const
{
    return nodeType_ == FailureModeNodeType::URMA_INTERFACE;
}
bool FailureMode::IsAccessEntry() const
{
    return nodeType_ == FailureModeNodeType::ACCESS_LOG_ENTRY;
}

} // namespace diag
