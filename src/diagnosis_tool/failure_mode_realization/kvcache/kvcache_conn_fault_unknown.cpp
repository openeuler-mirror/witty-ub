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

#include "kvcache_conn_fault_unknown.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFaultUnknown> g_kvcacheconnfaultunknown("kvcache_conn_fault_unknown");

bool KvcacheConnFaultUnknown::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = 0;
    try {
        statusCode = std::stoi(fields[7]);
    } catch (...) {
        return false;
    }
    return statusCode != 0;
}

std::string KvcacheConnFaultUnknown::GetName() const
{
    return "未知故障码（兜底模式）。";
}

std::string KvcacheConnFaultUnknown::GetRootCauseDesc() const
{
    return "状态码非零但未匹配到已知故障模式，需要人工分析。";
}

RootCause KvcacheConnFaultUnknown::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFaultUnknown::GetFixSuggDesc() const
{
    return "建议：1. 查询日志上下文确定具体错误；2. 根据业务逻辑分析该错误码含义；"
           "3. 如需长期监控，建议添加具体的故障模式定义。";
}

std::string KvcacheConnFaultUnknown::GetValidationMethodDesc() const
{
    return "通过access log识别：status_code（第8列）非零且未匹配其他已知故障模式。";
}

std::string KvcacheConnFaultUnknown::GetId() const
{
    return "kvcache_conn_fault_unknown";
}

} // namespace diag