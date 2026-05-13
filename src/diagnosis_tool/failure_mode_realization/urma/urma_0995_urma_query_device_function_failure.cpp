#include "urma_0995_urma_query_device_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0995UrmaQueryDeviceFunctionFailure> g_urma("urma_0995");

bool Urma0995UrmaQueryDeviceFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0996", "urma_0997"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0995UrmaQueryDeviceFunctionFailure::GetName() const
{
    return "urma_query_device 函数故障";
}

std::string Urma0995UrmaQueryDeviceFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0995UrmaQueryDeviceFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0995UrmaQueryDeviceFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0995UrmaQueryDeviceFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0995UrmaQueryDeviceFunctionFailure::GetId() const
{
    return "urma_0995";
}
} // namespace diag
