#include "urma_0030_init_general_slave_devices_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0030InitGeneralSlaveDevicesFunctionFailure> g_urma("urma_0030");

bool Urma0030InitGeneralSlaveDevicesFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0031", "urma_0032", "urma_0033"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0030InitGeneralSlaveDevicesFunctionFailure::GetName() const
{
    return "init_general_slave_devices 函数故障";
}

std::string Urma0030InitGeneralSlaveDevicesFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0030InitGeneralSlaveDevicesFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0030InitGeneralSlaveDevicesFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0030InitGeneralSlaveDevicesFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0030InitGeneralSlaveDevicesFunctionFailure::GetId() const
{
    return "urma_0030";
}
} // namespace diag
