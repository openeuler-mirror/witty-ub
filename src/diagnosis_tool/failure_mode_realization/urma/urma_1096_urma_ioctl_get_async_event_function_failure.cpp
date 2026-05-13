#include "urma_1096_urma_ioctl_get_async_event_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1096UrmaIoctlGetAsyncEventFunctionFailure> g_urma("urma_1096");

bool Urma1096UrmaIoctlGetAsyncEventFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1097"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1096UrmaIoctlGetAsyncEventFunctionFailure::GetName() const
{
    return "urma_ioctl_get_async_event 函数故障";
}

std::string Urma1096UrmaIoctlGetAsyncEventFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1096UrmaIoctlGetAsyncEventFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1096UrmaIoctlGetAsyncEventFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1096UrmaIoctlGetAsyncEventFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1096UrmaIoctlGetAsyncEventFunctionFailure::GetId() const
{
    return "urma_1096";
}
} // namespace diag
