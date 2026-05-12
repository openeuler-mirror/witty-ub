#include "urma_0794_urma_import_jetty_async_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0794UrmaImportJettyAsyncFunctionFailure> g_urma("urma_0794");

bool Urma0794UrmaImportJettyAsyncFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0795", "urma_0796"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0794UrmaImportJettyAsyncFunctionFailure::GetName() const
{
    return "urma_import_jetty_async 函数故障";
}

std::string Urma0794UrmaImportJettyAsyncFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0794UrmaImportJettyAsyncFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0794UrmaImportJettyAsyncFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0794UrmaImportJettyAsyncFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0794UrmaImportJettyAsyncFunctionFailure::GetId() const
{
    return "urma_0794";
}
} // namespace diag
