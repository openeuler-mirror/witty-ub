#include "urma_0972_urma_query_device_attr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0972UrmaQueryDeviceAttrFunctionFailure> g_urma("urma_0972");

bool Urma0972UrmaQueryDeviceAttrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0973", "urma_0974"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0972UrmaQueryDeviceAttrFunctionFailure::GetName() const
{
    return "urma_query_device_attr 函数故障";
}

std::string Urma0972UrmaQueryDeviceAttrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0972UrmaQueryDeviceAttrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0972UrmaQueryDeviceAttrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0972UrmaQueryDeviceAttrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0972UrmaQueryDeviceAttrFunctionFailure::GetId() const
{
    return "urma_0972";
}
} // namespace diag
