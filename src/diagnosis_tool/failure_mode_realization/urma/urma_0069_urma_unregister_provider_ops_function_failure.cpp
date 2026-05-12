#include "urma_0069_urma_unregister_provider_ops_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0069UrmaUnregisterProviderOpsFunctionFailure> g_urma("urma_0069");

bool Urma0069UrmaUnregisterProviderOpsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0070"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0069UrmaUnregisterProviderOpsFunctionFailure::GetName() const
{
    return "urma_unregister_provider_ops 函数故障";
}

std::string Urma0069UrmaUnregisterProviderOpsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0069UrmaUnregisterProviderOpsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0069UrmaUnregisterProviderOpsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0069UrmaUnregisterProviderOpsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0069UrmaUnregisterProviderOpsFunctionFailure::GetId() const
{
    return "urma_0069";
}
} // namespace diag
