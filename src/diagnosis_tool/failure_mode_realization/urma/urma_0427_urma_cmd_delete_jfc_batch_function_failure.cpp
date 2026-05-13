#include "urma_0427_urma_cmd_delete_jfc_batch_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0427UrmaCmdDeleteJfcBatchFunctionFailure> g_urma("urma_0427");

bool Urma0427UrmaCmdDeleteJfcBatchFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0428", "urma_0429", "urma_0430", "urma_0431",
                                                    "urma_0432", "urma_0433", "urma_0434"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0427UrmaCmdDeleteJfcBatchFunctionFailure::GetName() const
{
    return "urma_cmd_delete_jfc_batch 函数故障";
}

std::string Urma0427UrmaCmdDeleteJfcBatchFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0427UrmaCmdDeleteJfcBatchFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0427UrmaCmdDeleteJfcBatchFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0427UrmaCmdDeleteJfcBatchFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0427UrmaCmdDeleteJfcBatchFunctionFailure::GetId() const
{
    return "urma_0427";
}
} // namespace diag
