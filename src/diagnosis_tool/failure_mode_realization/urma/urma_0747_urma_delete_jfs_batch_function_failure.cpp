#include "urma_0747_urma_delete_jfs_batch_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0747UrmaDeleteJfsBatchFunctionFailure> g_urma("urma_0747");

bool Urma0747UrmaDeleteJfsBatchFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0748", "urma_0749", "urma_0750", "urma_0751", "urma_0752"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0747UrmaDeleteJfsBatchFunctionFailure::GetName() const
{
    return "urma_delete_jfs_batch 函数故障";
}

std::string Urma0747UrmaDeleteJfsBatchFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0747UrmaDeleteJfsBatchFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0747UrmaDeleteJfsBatchFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0747UrmaDeleteJfsBatchFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0747UrmaDeleteJfsBatchFunctionFailure::GetId() const
{
    return "urma_0747";
}
} // namespace diag
