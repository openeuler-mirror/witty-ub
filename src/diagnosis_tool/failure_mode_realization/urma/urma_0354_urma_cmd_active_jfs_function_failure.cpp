#include "urma_0354_urma_cmd_active_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0354UrmaCmdActiveJfsFunctionFailure> g_urma("urma_0354");

bool Urma0354UrmaCmdActiveJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0355", "urma_0356"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0354UrmaCmdActiveJfsFunctionFailure::GetName() const
{
    return "urma_cmd_active_jfs 函数故障";
}

std::string Urma0354UrmaCmdActiveJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0354UrmaCmdActiveJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0354UrmaCmdActiveJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0354UrmaCmdActiveJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0354UrmaCmdActiveJfsFunctionFailure::GetId() const
{
    return "urma_0354";
}
} // namespace diag
