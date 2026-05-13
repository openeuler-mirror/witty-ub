#include "urma_0545_urma_cmd_set_jfr_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0545UrmaCmdSetJfrOptFunctionFailure> g_urma("urma_0545");

bool Urma0545UrmaCmdSetJfrOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0546", "urma_0547", "urma_0548", "urma_0549"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0545UrmaCmdSetJfrOptFunctionFailure::GetName() const
{
    return "urma_cmd_set_jfr_opt 函数故障";
}

std::string Urma0545UrmaCmdSetJfrOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0545UrmaCmdSetJfrOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0545UrmaCmdSetJfrOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0545UrmaCmdSetJfrOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0545UrmaCmdSetJfrOptFunctionFailure::GetId() const
{
    return "urma_0545";
}
} // namespace diag
