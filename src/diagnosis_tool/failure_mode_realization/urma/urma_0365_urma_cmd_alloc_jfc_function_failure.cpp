#include "urma_0365_urma_cmd_alloc_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0365UrmaCmdAllocJfcFunctionFailure> g_urma("urma_0365");

bool Urma0365UrmaCmdAllocJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0366", "urma_0367"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0365UrmaCmdAllocJfcFunctionFailure::GetName() const
{
    return "urma_cmd_alloc_jfc 函数故障";
}

std::string Urma0365UrmaCmdAllocJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0365UrmaCmdAllocJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0365UrmaCmdAllocJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0365UrmaCmdAllocJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0365UrmaCmdAllocJfcFunctionFailure::GetId() const
{
    return "urma_0365";
}
} // namespace diag
