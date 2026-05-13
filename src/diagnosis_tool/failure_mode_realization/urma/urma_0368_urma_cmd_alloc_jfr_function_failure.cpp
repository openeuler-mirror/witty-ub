#include "urma_0368_urma_cmd_alloc_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0368UrmaCmdAllocJfrFunctionFailure> g_urma("urma_0368");

bool Urma0368UrmaCmdAllocJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0369", "urma_0370"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0368UrmaCmdAllocJfrFunctionFailure::GetName() const
{
    return "urma_cmd_alloc_jfr 函数故障";
}

std::string Urma0368UrmaCmdAllocJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0368UrmaCmdAllocJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0368UrmaCmdAllocJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0368UrmaCmdAllocJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0368UrmaCmdAllocJfrFunctionFailure::GetId() const
{
    return "urma_0368";
}
} // namespace diag
