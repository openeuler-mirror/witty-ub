#include "urma_0947_urma_cmd_query_device_attr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0947UrmaCmdQueryDeviceAttrFunctionFailure> g_urma("urma_0947");

bool Urma0947UrmaCmdQueryDeviceAttrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0948"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0947UrmaCmdQueryDeviceAttrFunctionFailure::GetName() const
{
    return "urma_cmd_query_device_attr 函数故障";
}

std::string Urma0947UrmaCmdQueryDeviceAttrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0947UrmaCmdQueryDeviceAttrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0947UrmaCmdQueryDeviceAttrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0947UrmaCmdQueryDeviceAttrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0947UrmaCmdQueryDeviceAttrFunctionFailure::GetId() const
{
    return "urma_0947";
}
} // namespace diag
