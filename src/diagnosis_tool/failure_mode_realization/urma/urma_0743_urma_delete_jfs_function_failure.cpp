#include "urma_0743_urma_delete_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0743UrmaDeleteJfsFunctionFailure> g_urma("urma_0743");

bool Urma0743UrmaDeleteJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0744", "urma_0745", "urma_0746"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0743UrmaDeleteJfsFunctionFailure::GetName() const
{
    return "urma_delete_jfs 函数故障";
}

std::string Urma0743UrmaDeleteJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0743UrmaDeleteJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0743UrmaDeleteJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0743UrmaDeleteJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0743UrmaDeleteJfsFunctionFailure::GetId() const
{
    return "urma_0743";
}
} // namespace diag
