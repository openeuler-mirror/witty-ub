#include "urma_0371_urma_cmd_alloc_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0371UrmaCmdAllocJfsFunctionFailure> g_urma("urma_0371");

bool Urma0371UrmaCmdAllocJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0372", "urma_0373"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0371UrmaCmdAllocJfsFunctionFailure::GetName() const
{
    return "urma_cmd_alloc_jfs 函数故障";
}

std::string Urma0371UrmaCmdAllocJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0371UrmaCmdAllocJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0371UrmaCmdAllocJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0371UrmaCmdAllocJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0371UrmaCmdAllocJfsFunctionFailure::GetId() const
{
    return "urma_0371";
}
} // namespace diag
