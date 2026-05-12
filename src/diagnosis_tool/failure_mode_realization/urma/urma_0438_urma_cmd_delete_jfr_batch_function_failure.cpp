#include "urma_0438_urma_cmd_delete_jfr_batch_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0438UrmaCmdDeleteJfrBatchFunctionFailure> g_urma("urma_0438");

bool Urma0438UrmaCmdDeleteJfrBatchFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0439", "urma_0440", "urma_0441", "urma_0442",
                                                    "urma_0443", "urma_0444", "urma_0445"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0438UrmaCmdDeleteJfrBatchFunctionFailure::GetName() const
{
    return "urma_cmd_delete_jfr_batch 函数故障";
}

std::string Urma0438UrmaCmdDeleteJfrBatchFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0438UrmaCmdDeleteJfrBatchFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0438UrmaCmdDeleteJfrBatchFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0438UrmaCmdDeleteJfrBatchFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0438UrmaCmdDeleteJfrBatchFunctionFailure::GetId() const
{
    return "urma_0438";
}
} // namespace diag
