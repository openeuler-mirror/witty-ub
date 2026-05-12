#include "urma_0618_urma_alloc_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0618UrmaAllocJfcFunctionFailure> g_urma("urma_0618");

bool Urma0618UrmaAllocJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0619", "urma_0620", "urma_0621"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0618UrmaAllocJfcFunctionFailure::GetName() const
{
    return "urma_alloc_jfc 函数故障";
}

std::string Urma0618UrmaAllocJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0618UrmaAllocJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0618UrmaAllocJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0618UrmaAllocJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0618UrmaAllocJfcFunctionFailure::GetId() const
{
    return "urma_0618";
}
} // namespace diag
