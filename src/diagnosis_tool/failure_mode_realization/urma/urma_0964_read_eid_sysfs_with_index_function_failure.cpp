#include "urma_0964_read_eid_sysfs_with_index_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0964ReadEidSysfsWithIndexFunctionFailure> g_urma("urma_0964");

bool Urma0964ReadEidSysfsWithIndexFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0965", "urma_0966", "urma_0967"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0964ReadEidSysfsWithIndexFunctionFailure::GetName() const
{
    return "read_eid_sysfs_with_index 函数故障";
}

std::string Urma0964ReadEidSysfsWithIndexFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0964ReadEidSysfsWithIndexFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0964ReadEidSysfsWithIndexFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0964ReadEidSysfsWithIndexFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0964ReadEidSysfsWithIndexFunctionFailure::GetId() const
{
    return "urma_0964";
}
} // namespace diag
