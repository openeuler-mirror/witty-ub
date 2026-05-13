#include "urma_0407_urma_cmd_deactive_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0407UrmaCmdDeactiveJfsFunctionFailure> g_urma("urma_0407");

bool Urma0407UrmaCmdDeactiveJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0408", "urma_0409"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0407UrmaCmdDeactiveJfsFunctionFailure::GetName() const
{
    return "urma_cmd_deactive_jfs 函数故障";
}

std::string Urma0407UrmaCmdDeactiveJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0407UrmaCmdDeactiveJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0407UrmaCmdDeactiveJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0407UrmaCmdDeactiveJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0407UrmaCmdDeactiveJfsFunctionFailure::GetId() const
{
    return "urma_0407";
}
} // namespace diag
