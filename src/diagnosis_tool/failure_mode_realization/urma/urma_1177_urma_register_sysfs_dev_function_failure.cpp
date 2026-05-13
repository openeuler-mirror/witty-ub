#include "urma_1177_urma_register_sysfs_dev_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1177UrmaRegisterSysfsDevFunctionFailure> g_urma("urma_1177");

bool Urma1177UrmaRegisterSysfsDevFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1178"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1177UrmaRegisterSysfsDevFunctionFailure::GetName() const
{
    return "urma_register_sysfs_dev 函数故障";
}

std::string Urma1177UrmaRegisterSysfsDevFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1177UrmaRegisterSysfsDevFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1177UrmaRegisterSysfsDevFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1177UrmaRegisterSysfsDevFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1177UrmaRegisterSysfsDevFunctionFailure::GetId() const
{
    return "urma_1177";
}
} // namespace diag
