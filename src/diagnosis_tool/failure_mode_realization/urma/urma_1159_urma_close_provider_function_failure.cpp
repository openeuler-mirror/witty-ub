#include "urma_1159_urma_close_provider_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1159UrmaCloseProviderFunctionFailure> g_urma("urma_1159");

bool Urma1159UrmaCloseProviderFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1160"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1159UrmaCloseProviderFunctionFailure::GetName() const
{
    return "urma_close_provider 函数故障";
}

std::string Urma1159UrmaCloseProviderFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1159UrmaCloseProviderFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1159UrmaCloseProviderFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1159UrmaCloseProviderFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1159UrmaCloseProviderFunctionFailure::GetId() const
{
    return "urma_1159";
}
} // namespace diag
