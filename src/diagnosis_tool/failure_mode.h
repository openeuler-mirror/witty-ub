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

#ifndef FAILURE_MODE_H
#define FAILURE_MODE_H

#include <optional>
#include <string>

namespace diag {

enum class FailureModeComponent {
    KVCACHE,
    URMA,
};

enum class FailureModeNodeType {
    ACCESS_LOG_ENTRY,
    RUNTIME_LOG,
    URMA_INTERFACE,
    URMA_FAILURE,
};

// 由 failure mode JSON 直接构造的不可变故障模式描述。诊断行为不再由
// 每个故障模式的 C++ 派生类实现，而是由 DiagnosisEngine 统一解释规则。
struct FailureModeDescriptor {
    std::string id;
    std::string name;
    std::string phenomenon;
    std::string cause;
    std::string suggestion;
    std::string filename;
    std::string functionName;
    std::optional<std::string> errorCode;
    FailureModeNodeType nodeType = FailureModeNodeType::URMA_FAILURE;
};

class FailureMode final {
public:
    explicit FailureMode(FailureModeDescriptor desc);

    const std::string &GetId() const;
    const std::string &GetName() const;
    const std::string &GetPhenomenon() const;
    const std::string &GetRootCauseDesc() const;
    const std::string &GetFixSuggDesc() const;
    const std::string &GetValidationMethodDesc() const;
    const std::string &GetFilename() const;
    const std::string &GetFunctionName() const;
    const std::optional<std::string> &GetErrorCode() const;
    FailureModeNodeType GetNodeType() const;
    bool IsPublicInterface() const;
    bool IsAccessEntry() const;

private:
    std::string id_;
    std::string name_;
    std::string phenomenon_;
    std::string cause_;
    std::string suggestion_;
    std::string filename_;
    std::string functionName_;
    std::optional<std::string> errorCode_;
    FailureModeNodeType nodeType_;
};

} // namespace diag

#endif // FAILURE_MODE_H
