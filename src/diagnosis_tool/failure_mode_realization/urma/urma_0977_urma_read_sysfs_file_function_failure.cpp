#include "urma_0977_urma_read_sysfs_file_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0977UrmaReadSysfsFileFunctionFailure> g_urma("urma_0977");

bool Urma0977UrmaReadSysfsFileFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0978", "urma_0979", "urma_0980"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0977UrmaReadSysfsFileFunctionFailure::GetName() const
{
    return "urma_read_sysfs_file 函数故障";
}

std::string Urma0977UrmaReadSysfsFileFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0977UrmaReadSysfsFileFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0977UrmaReadSysfsFileFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0977UrmaReadSysfsFileFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0977UrmaReadSysfsFileFunctionFailure::GetId() const
{
    return "urma_0977";
}
} // namespace diag
