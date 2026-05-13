#include "urma_0446_urma_cmd_delete_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0446UrmaCmdDeleteJfsFunctionFailure> g_urma("urma_0446");

bool Urma0446UrmaCmdDeleteJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0447", "urma_0448"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0446UrmaCmdDeleteJfsFunctionFailure::GetName() const
{
    return "urma_cmd_delete_jfs 函数故障";
}

std::string Urma0446UrmaCmdDeleteJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0446UrmaCmdDeleteJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0446UrmaCmdDeleteJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0446UrmaCmdDeleteJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0446UrmaCmdDeleteJfsFunctionFailure::GetId() const
{
    return "urma_0446";
}
} // namespace diag
