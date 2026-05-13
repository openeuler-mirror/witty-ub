#include "urma_1219_urma_user_ctl_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1219UrmaUserCtlFunctionFailure> g_urma("urma_1219");

bool Urma1219UrmaUserCtlFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1220", "urma_1221"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1219UrmaUserCtlFunctionFailure::GetName() const
{
    return "urma_user_ctl 函数故障";
}

std::string Urma1219UrmaUserCtlFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1219UrmaUserCtlFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1219UrmaUserCtlFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1219UrmaUserCtlFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1219UrmaUserCtlFunctionFailure::GetId() const
{
    return "urma_1219";
}
} // namespace diag
