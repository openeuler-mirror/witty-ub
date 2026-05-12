#include "urma_0519_urma_cmd_modify_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0519UrmaCmdModifyJfsFunctionFailure> g_urma("urma_0519");

bool Urma0519UrmaCmdModifyJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0520", "urma_0521"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0519UrmaCmdModifyJfsFunctionFailure::GetName() const
{
    return "urma_cmd_modify_jfs 函数故障";
}

std::string Urma0519UrmaCmdModifyJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0519UrmaCmdModifyJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0519UrmaCmdModifyJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0519UrmaCmdModifyJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0519UrmaCmdModifyJfsFunctionFailure::GetId() const
{
    return "urma_0519";
}
} // namespace diag
