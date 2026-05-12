#include "urma_1108_urma_get_async_event_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1108UrmaGetAsyncEventFunctionFailure> g_urma("urma_1108");

bool Urma1108UrmaGetAsyncEventFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1109"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1108UrmaGetAsyncEventFunctionFailure::GetName() const
{
    return "urma_get_async_event 函数故障";
}

std::string Urma1108UrmaGetAsyncEventFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1108UrmaGetAsyncEventFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1108UrmaGetAsyncEventFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1108UrmaGetAsyncEventFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1108UrmaGetAsyncEventFunctionFailure::GetId() const
{
    return "urma_1108";
}
} // namespace diag
