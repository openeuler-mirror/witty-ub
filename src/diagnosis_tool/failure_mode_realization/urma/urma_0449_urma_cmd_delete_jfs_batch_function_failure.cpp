#include "urma_0449_urma_cmd_delete_jfs_batch_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0449UrmaCmdDeleteJfsBatchFunctionFailure> g_urma("urma_0449");

bool Urma0449UrmaCmdDeleteJfsBatchFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0450", "urma_0451", "urma_0452", "urma_0453",
                                                    "urma_0454", "urma_0455", "urma_0456"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0449UrmaCmdDeleteJfsBatchFunctionFailure::GetName() const
{
    return "urma_cmd_delete_jfs_batch 函数故障";
}

std::string Urma0449UrmaCmdDeleteJfsBatchFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0449UrmaCmdDeleteJfsBatchFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0449UrmaCmdDeleteJfsBatchFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0449UrmaCmdDeleteJfsBatchFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0449UrmaCmdDeleteJfsBatchFunctionFailure::GetId() const
{
    return "urma_0449";
}
} // namespace diag
