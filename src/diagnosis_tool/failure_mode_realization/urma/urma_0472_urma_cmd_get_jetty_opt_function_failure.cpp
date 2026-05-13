#include "urma_0472_urma_cmd_get_jetty_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0472UrmaCmdGetJettyOptFunctionFailure> g_urma("urma_0472");

bool Urma0472UrmaCmdGetJettyOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0473", "urma_0474", "urma_0475", "urma_0476"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0472UrmaCmdGetJettyOptFunctionFailure::GetName() const
{
    return "urma_cmd_get_jetty_opt 函数故障";
}

std::string Urma0472UrmaCmdGetJettyOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0472UrmaCmdGetJettyOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0472UrmaCmdGetJettyOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0472UrmaCmdGetJettyOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0472UrmaCmdGetJettyOptFunctionFailure::GetId() const
{
    return "urma_0472";
}
} // namespace diag
