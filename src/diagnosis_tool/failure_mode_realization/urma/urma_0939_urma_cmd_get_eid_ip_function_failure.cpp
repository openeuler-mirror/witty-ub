#include "urma_0939_urma_cmd_get_eid_ip_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0939UrmaCmdGetEidIpFunctionFailure> g_urma("urma_0939");

bool Urma0939UrmaCmdGetEidIpFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0940"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0939UrmaCmdGetEidIpFunctionFailure::GetName() const
{
    return "urma_cmd_get_eid_by_ip 函数故障";
}

std::string Urma0939UrmaCmdGetEidIpFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0939UrmaCmdGetEidIpFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0939UrmaCmdGetEidIpFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0939UrmaCmdGetEidIpFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0939UrmaCmdGetEidIpFunctionFailure::GetId() const
{
    return "urma_0939";
}
} // namespace diag
