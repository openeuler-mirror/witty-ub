#include "urma_0565_urma_cmd_unbind_jetty_async_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0565UrmaCmdUnbindJettyAsyncFunctionFailure> g_urma("urma_0565");

bool Urma0565UrmaCmdUnbindJettyAsyncFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0566"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0565UrmaCmdUnbindJettyAsyncFunctionFailure::GetName() const
{
    return "urma_cmd_unbind_jetty_async 函数故障";
}

std::string Urma0565UrmaCmdUnbindJettyAsyncFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0565UrmaCmdUnbindJettyAsyncFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0565UrmaCmdUnbindJettyAsyncFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0565UrmaCmdUnbindJettyAsyncFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0565UrmaCmdUnbindJettyAsyncFunctionFailure::GetId() const
{
    return "urma_0565";
}
} // namespace diag
