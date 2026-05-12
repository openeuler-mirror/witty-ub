#include "urma_0953_urma_get_ip_eid_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0953UrmaGetIpEidFunctionFailure> g_urma("urma_0953");

bool Urma0953UrmaGetIpEidFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0954"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0953UrmaGetIpEidFunctionFailure::GetName() const
{
    return "urma_get_ip_by_eid 函数故障";
}

std::string Urma0953UrmaGetIpEidFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0953UrmaGetIpEidFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0953UrmaGetIpEidFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0953UrmaGetIpEidFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0953UrmaGetIpEidFunctionFailure::GetId() const
{
    return "urma_0953";
}
} // namespace diag
