#include "urma_1090_urma_cmd_get_async_event_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1090UrmaCmdGetAsyncEventFunctionFailure> g_urma("urma_1090");

bool Urma1090UrmaCmdGetAsyncEventFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1091"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1090UrmaCmdGetAsyncEventFunctionFailure::GetName() const
{
    return "urma_cmd_get_async_event 函数故障";
}

std::string Urma1090UrmaCmdGetAsyncEventFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1090UrmaCmdGetAsyncEventFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1090UrmaCmdGetAsyncEventFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1090UrmaCmdGetAsyncEventFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1090UrmaCmdGetAsyncEventFunctionFailure::GetId() const
{
    return "urma_1090";
}
} // namespace diag
