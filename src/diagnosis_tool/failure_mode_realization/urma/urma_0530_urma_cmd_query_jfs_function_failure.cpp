#include "urma_0530_urma_cmd_query_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0530UrmaCmdQueryJfsFunctionFailure> g_urma("urma_0530");

bool Urma0530UrmaCmdQueryJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0531", "urma_0532"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0530UrmaCmdQueryJfsFunctionFailure::GetName() const
{
    return "urma_cmd_query_jfs 函数故障";
}

std::string Urma0530UrmaCmdQueryJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0530UrmaCmdQueryJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0530UrmaCmdQueryJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0530UrmaCmdQueryJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0530UrmaCmdQueryJfsFunctionFailure::GetId() const
{
    return "urma_0530";
}
} // namespace diag
