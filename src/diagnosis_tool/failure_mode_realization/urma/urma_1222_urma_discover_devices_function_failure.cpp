#include "urma_1222_urma_discover_devices_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1222UrmaDiscoverDevicesFunctionFailure> g_urma("urma_1222");

bool Urma1222UrmaDiscoverDevicesFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1223", "urma_1224"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1222UrmaDiscoverDevicesFunctionFailure::GetName() const
{
    return "urma_discover_devices 函数故障";
}

std::string Urma1222UrmaDiscoverDevicesFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1222UrmaDiscoverDevicesFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1222UrmaDiscoverDevicesFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1222UrmaDiscoverDevicesFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1222UrmaDiscoverDevicesFunctionFailure::GetId() const
{
    return "urma_1222";
}
} // namespace diag
