#include "urma_0576_urma_ioctl_wait_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0576UrmaIoctlWaitJfcFunctionFailure> g_urma("urma_0576");

bool Urma0576UrmaIoctlWaitJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0577"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0576UrmaIoctlWaitJfcFunctionFailure::GetName() const
{
    return "urma_ioctl_wait_jfc 函数故障";
}

std::string Urma0576UrmaIoctlWaitJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0576UrmaIoctlWaitJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0576UrmaIoctlWaitJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0576UrmaIoctlWaitJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0576UrmaIoctlWaitJfcFunctionFailure::GetId() const
{
    return "urma_0576";
}
} // namespace diag
