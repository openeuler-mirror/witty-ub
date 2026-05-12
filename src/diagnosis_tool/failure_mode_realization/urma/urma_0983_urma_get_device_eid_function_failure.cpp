#include "urma_0983_urma_get_device_eid_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0983UrmaGetDeviceEidFunctionFailure> g_urma("urma_0983");

bool Urma0983UrmaGetDeviceEidFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0984"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0983UrmaGetDeviceEidFunctionFailure::GetName() const
{
    return "urma_get_device_by_eid 函数故障";
}

std::string Urma0983UrmaGetDeviceEidFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0983UrmaGetDeviceEidFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0983UrmaGetDeviceEidFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0983UrmaGetDeviceEidFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0983UrmaGetDeviceEidFunctionFailure::GetId() const
{
    return "urma_0983";
}
} // namespace diag
