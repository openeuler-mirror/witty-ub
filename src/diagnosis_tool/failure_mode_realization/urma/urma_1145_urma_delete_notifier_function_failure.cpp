#include "urma_1145_urma_delete_notifier_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1145UrmaDeleteNotifierFunctionFailure> g_urma("urma_1145");

bool Urma1145UrmaDeleteNotifierFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1146", "urma_1147"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1145UrmaDeleteNotifierFunctionFailure::GetName() const
{
    return "urma_delete_notifier 函数故障";
}

std::string Urma1145UrmaDeleteNotifierFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1145UrmaDeleteNotifierFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1145UrmaDeleteNotifierFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1145UrmaDeleteNotifierFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1145UrmaDeleteNotifierFunctionFailure::GetId() const
{
    return "urma_1145";
}
} // namespace diag
