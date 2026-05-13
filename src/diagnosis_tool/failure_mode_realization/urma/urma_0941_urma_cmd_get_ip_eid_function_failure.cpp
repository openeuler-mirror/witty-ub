#include "urma_0941_urma_cmd_get_ip_eid_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0941UrmaCmdGetIpEidFunctionFailure> g_urma("urma_0941");

bool Urma0941UrmaCmdGetIpEidFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0942"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0941UrmaCmdGetIpEidFunctionFailure::GetName() const
{
    return "urma_cmd_get_ip_by_eid 函数故障";
}

std::string Urma0941UrmaCmdGetIpEidFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0941UrmaCmdGetIpEidFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0941UrmaCmdGetIpEidFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0941UrmaCmdGetIpEidFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0941UrmaCmdGetIpEidFunctionFailure::GetId() const
{
    return "urma_0941";
}
} // namespace diag
