#include "urma_0985_urma_get_device_name_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0985UrmaGetDeviceNameFunctionFailure> g_urma("urma_0985");

bool Urma0985UrmaGetDeviceNameFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0986", "urma_0987", "urma_0988"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0985UrmaGetDeviceNameFunctionFailure::GetName() const
{
    return "urma_get_device_by_name 函数故障";
}

std::string Urma0985UrmaGetDeviceNameFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0985UrmaGetDeviceNameFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0985UrmaGetDeviceNameFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0985UrmaGetDeviceNameFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0985UrmaGetDeviceNameFunctionFailure::GetId() const
{
    return "urma_0985";
}
} // namespace diag
