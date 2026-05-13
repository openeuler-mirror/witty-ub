#include "urma_0503_urma_cmd_import_jetty_async_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0503UrmaCmdImportJettyAsyncFunctionFailure> g_urma("urma_0503");

bool Urma0503UrmaCmdImportJettyAsyncFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0504"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0503UrmaCmdImportJettyAsyncFunctionFailure::GetName() const
{
    return "urma_cmd_import_jetty_async 函数故障";
}

std::string Urma0503UrmaCmdImportJettyAsyncFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0503UrmaCmdImportJettyAsyncFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0503UrmaCmdImportJettyAsyncFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0503UrmaCmdImportJettyAsyncFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0503UrmaCmdImportJettyAsyncFunctionFailure::GetId() const
{
    return "urma_0503";
}
} // namespace diag
