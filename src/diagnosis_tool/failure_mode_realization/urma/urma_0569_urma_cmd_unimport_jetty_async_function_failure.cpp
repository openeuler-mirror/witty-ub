#include "urma_0569_urma_cmd_unimport_jetty_async_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0569UrmaCmdUnimportJettyAsyncFunctionFailure> g_urma("urma_0569");

bool Urma0569UrmaCmdUnimportJettyAsyncFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0570"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0569UrmaCmdUnimportJettyAsyncFunctionFailure::GetName() const
{
    return "urma_cmd_unimport_jetty_async 函数故障";
}

std::string Urma0569UrmaCmdUnimportJettyAsyncFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0569UrmaCmdUnimportJettyAsyncFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0569UrmaCmdUnimportJettyAsyncFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0569UrmaCmdUnimportJettyAsyncFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0569UrmaCmdUnimportJettyAsyncFunctionFailure::GetId() const
{
    return "urma_0569";
}
} // namespace diag
