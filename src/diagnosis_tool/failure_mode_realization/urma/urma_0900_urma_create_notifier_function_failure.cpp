#include "urma_0900_urma_create_notifier_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0900UrmaCreateNotifierFunctionFailure> g_urma("urma_0900");

bool Urma0900UrmaCreateNotifierFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0901", "urma_0902"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0900UrmaCreateNotifierFunctionFailure::GetName() const
{
    return "urma_create_notifier 函数故障";
}

std::string Urma0900UrmaCreateNotifierFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0900UrmaCreateNotifierFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0900UrmaCreateNotifierFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0900UrmaCreateNotifierFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0900UrmaCreateNotifierFunctionFailure::GetId() const
{
    return "urma_0900";
}
} // namespace diag
