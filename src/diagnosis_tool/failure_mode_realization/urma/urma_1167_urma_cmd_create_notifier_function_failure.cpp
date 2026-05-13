#include "urma_1167_urma_cmd_create_notifier_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1167UrmaCmdCreateNotifierFunctionFailure> g_urma("urma_1167");

bool Urma1167UrmaCmdCreateNotifierFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1168", "urma_1169"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1167UrmaCmdCreateNotifierFunctionFailure::GetName() const
{
    return "urma_cmd_create_notifier 函数故障";
}

std::string Urma1167UrmaCmdCreateNotifierFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1167UrmaCmdCreateNotifierFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1167UrmaCmdCreateNotifierFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1167UrmaCmdCreateNotifierFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1167UrmaCmdCreateNotifierFunctionFailure::GetId() const
{
    return "urma_1167";
}
} // namespace diag
