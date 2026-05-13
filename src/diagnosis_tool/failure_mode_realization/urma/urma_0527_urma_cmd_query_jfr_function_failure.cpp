#include "urma_0527_urma_cmd_query_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0527UrmaCmdQueryJfrFunctionFailure> g_urma("urma_0527");

bool Urma0527UrmaCmdQueryJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0528", "urma_0529"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0527UrmaCmdQueryJfrFunctionFailure::GetName() const
{
    return "urma_cmd_query_jfr 函数故障";
}

std::string Urma0527UrmaCmdQueryJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0527UrmaCmdQueryJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0527UrmaCmdQueryJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0527UrmaCmdQueryJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0527UrmaCmdQueryJfrFunctionFailure::GetId() const
{
    return "urma_0527";
}
} // namespace diag
