#include "urma_0723_urma_delete_jfc_batch_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0723UrmaDeleteJfcBatchFunctionFailure> g_urma("urma_0723");

bool Urma0723UrmaDeleteJfcBatchFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0724", "urma_0725", "urma_0726", "urma_0727", "urma_0728"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0723UrmaDeleteJfcBatchFunctionFailure::GetName() const
{
    return "urma_delete_jfc_batch 函数故障";
}

std::string Urma0723UrmaDeleteJfcBatchFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0723UrmaDeleteJfcBatchFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0723UrmaDeleteJfcBatchFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0723UrmaDeleteJfcBatchFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0723UrmaDeleteJfcBatchFunctionFailure::GetId() const
{
    return "urma_0723";
}
} // namespace diag
