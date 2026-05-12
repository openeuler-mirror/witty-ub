#include "urma_0524_urma_cmd_query_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0524UrmaCmdQueryJettyFunctionFailure> g_urma("urma_0524");

bool Urma0524UrmaCmdQueryJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0525", "urma_0526"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0524UrmaCmdQueryJettyFunctionFailure::GetName() const
{
    return "urma_cmd_query_jetty 函数故障";
}

std::string Urma0524UrmaCmdQueryJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0524UrmaCmdQueryJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0524UrmaCmdQueryJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0524UrmaCmdQueryJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0524UrmaCmdQueryJettyFunctionFailure::GetId() const
{
    return "urma_0524";
}
} // namespace diag
