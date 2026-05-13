#include "urma_0489_urma_cmd_get_jfs_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0489UrmaCmdGetJfsOptFunctionFailure> g_urma("urma_0489");

bool Urma0489UrmaCmdGetJfsOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0490", "urma_0491", "urma_0492", "urma_0493", "urma_0494"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0489UrmaCmdGetJfsOptFunctionFailure::GetName() const
{
    return "urma_cmd_get_jfs_opt 函数故障";
}

std::string Urma0489UrmaCmdGetJfsOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0489UrmaCmdGetJfsOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0489UrmaCmdGetJfsOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0489UrmaCmdGetJfsOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0489UrmaCmdGetJfsOptFunctionFailure::GetId() const
{
    return "urma_0489";
}
} // namespace diag
