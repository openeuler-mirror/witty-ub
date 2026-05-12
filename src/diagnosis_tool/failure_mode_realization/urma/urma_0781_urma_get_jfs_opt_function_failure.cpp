#include "urma_0781_urma_get_jfs_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0781UrmaGetJfsOptFunctionFailure> g_urma("urma_0781");

bool Urma0781UrmaGetJfsOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0782", "urma_0783"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0781UrmaGetJfsOptFunctionFailure::GetName() const
{
    return "urma_get_jfs_opt 函数故障";
}

std::string Urma0781UrmaGetJfsOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0781UrmaGetJfsOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0781UrmaGetJfsOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0781UrmaGetJfsOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0781UrmaGetJfsOptFunctionFailure::GetId() const
{
    return "urma_0781";
}
} // namespace diag
