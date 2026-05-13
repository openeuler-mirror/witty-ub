#include "urma_0351_urma_cmd_active_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0351UrmaCmdActiveJfrFunctionFailure> g_urma("urma_0351");

bool Urma0351UrmaCmdActiveJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0352", "urma_0353"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0351UrmaCmdActiveJfrFunctionFailure::GetName() const
{
    return "urma_cmd_active_jfr 函数故障";
}

std::string Urma0351UrmaCmdActiveJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0351UrmaCmdActiveJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0351UrmaCmdActiveJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0351UrmaCmdActiveJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0351UrmaCmdActiveJfrFunctionFailure::GetId() const
{
    return "urma_0351";
}
} // namespace diag
