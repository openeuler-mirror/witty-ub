#include "urma_0737_urma_delete_jfr_batch_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0737UrmaDeleteJfrBatchFunctionFailure> g_urma("urma_0737");

bool Urma0737UrmaDeleteJfrBatchFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0738", "urma_0739", "urma_0740", "urma_0741", "urma_0742"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0737UrmaDeleteJfrBatchFunctionFailure::GetName() const
{
    return "urma_delete_jfr_batch 函数故障";
}

std::string Urma0737UrmaDeleteJfrBatchFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0737UrmaDeleteJfrBatchFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0737UrmaDeleteJfrBatchFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0737UrmaDeleteJfrBatchFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0737UrmaDeleteJfrBatchFunctionFailure::GetId() const
{
    return "urma_0737";
}
} // namespace diag
