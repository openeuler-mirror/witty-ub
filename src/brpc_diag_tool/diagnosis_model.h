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

#ifndef DIAGNOSIS_MODEL_H
#define DIAGNOSIS_MODEL_H

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <variant>
#include "log_def.h"

namespace brpc {

enum class DiagnosisComponent {
    UNKNOWN,
    UBSOCKET,
    UMQ,
    URMA,
};

enum class DiagnosisEdgeType {
    INTRA_COMPONENT,
    CROSS_COMPONENT,
};

inline DiagnosisComponent GetDiagnosisComponent(std::string_view id)
{
    if (id.rfind("ubsocket_", 0) == 0) {
        return DiagnosisComponent::UBSOCKET;
    }
    if (id.rfind("umq_", 0) == 0) {
        return DiagnosisComponent::UMQ;
    }
    if (id.rfind("urma4brpc_", 0) == 0) {
        return DiagnosisComponent::URMA;
    }
    return DiagnosisComponent::UNKNOWN;
}

inline const char *ToString(DiagnosisComponent component)
{
    switch (component) {
        case DiagnosisComponent::UBSOCKET:
            return "ubsocket";
        case DiagnosisComponent::UMQ:
            return "umq";
        case DiagnosisComponent::URMA:
            return "urma";
        default:
            return "";
    }
}

inline const char *ToString(DiagnosisEdgeType type)
{
    switch (type) {
        case DiagnosisEdgeType::INTRA_COMPONENT:
            return "intra_component";
        case DiagnosisEdgeType::CROSS_COMPONENT:
            return "cross_component";
    }
    return "";
}

inline bool IsSupportedCrossComponentEdge(DiagnosisComponent source, DiagnosisComponent target)
{
    return (source == DiagnosisComponent::UBSOCKET && target == DiagnosisComponent::UMQ) ||
           (source == DiagnosisComponent::UMQ && target == DiagnosisComponent::URMA);
}

using DiagnosisErrorCode = std::variant<std::int64_t, std::string>;
using DiagnosisLog = BrpcLog;

struct FailureModeInfo {
    std::string id;
    std::string name;
    std::string filename;
    std::string functionName;
    DiagnosisComponent component = DiagnosisComponent::UNKNOWN;
    std::string phenomenon;
    std::string cause;
    std::string solution;
    std::optional<DiagnosisErrorCode> errorCode;
    bool publicApi = false;
};

struct DiagnosisRule {
    FailureModeInfo failureMode;
    std::vector<std::string> keywords; // 由"故障现象"解析得到，空表示"向下级匹配"根节点
    std::vector<std::size_t> localChildIndices;
    std::vector<std::size_t> crossChildIndices;
};

} // namespace brpc

#endif // DIAGNOSIS_MODEL_H