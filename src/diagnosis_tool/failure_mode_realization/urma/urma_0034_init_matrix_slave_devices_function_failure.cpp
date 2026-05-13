#include "urma_0034_init_matrix_slave_devices_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0034InitMatrixSlaveDevicesFunctionFailure> g_urma("urma_0034");

bool Urma0034InitMatrixSlaveDevicesFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0035", "urma_0036", "urma_0037", "urma_0038", "urma_0039"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0034InitMatrixSlaveDevicesFunctionFailure::GetName() const
{
    return "init_matrix_slave_devices 函数故障";
}

std::string Urma0034InitMatrixSlaveDevicesFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0034InitMatrixSlaveDevicesFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0034InitMatrixSlaveDevicesFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0034InitMatrixSlaveDevicesFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0034InitMatrixSlaveDevicesFunctionFailure::GetId() const
{
    return "urma_0034";
}
} // namespace diag
