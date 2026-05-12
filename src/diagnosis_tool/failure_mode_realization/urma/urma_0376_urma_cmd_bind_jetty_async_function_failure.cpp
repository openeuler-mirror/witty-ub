#include "urma_0376_urma_cmd_bind_jetty_async_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0376UrmaCmdBindJettyAsyncFunctionFailure> g_urma("urma_0376");

bool Urma0376UrmaCmdBindJettyAsyncFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0377"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0376UrmaCmdBindJettyAsyncFunctionFailure::GetName() const
{
    return "urma_cmd_bind_jetty_async 函数故障";
}

std::string Urma0376UrmaCmdBindJettyAsyncFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0376UrmaCmdBindJettyAsyncFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0376UrmaCmdBindJettyAsyncFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0376UrmaCmdBindJettyAsyncFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0376UrmaCmdBindJettyAsyncFunctionFailure::GetId() const
{
    return "urma_0376";
}
} // namespace diag
