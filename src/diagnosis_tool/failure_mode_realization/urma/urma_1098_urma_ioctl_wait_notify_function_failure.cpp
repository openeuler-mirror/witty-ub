#include "urma_1098_urma_ioctl_wait_notify_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1098UrmaIoctlWaitNotifyFunctionFailure> g_urma("urma_1098");

bool Urma1098UrmaIoctlWaitNotifyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1099"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1098UrmaIoctlWaitNotifyFunctionFailure::GetName() const
{
    return "urma_ioctl_wait_notify 函数故障";
}

std::string Urma1098UrmaIoctlWaitNotifyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1098UrmaIoctlWaitNotifyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1098UrmaIoctlWaitNotifyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1098UrmaIoctlWaitNotifyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1098UrmaIoctlWaitNotifyFunctionFailure::GetId() const
{
    return "urma_1098";
}
} // namespace diag
