#include "urma_0635_urma_bind_jetty_async_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0635UrmaBindJettyAsyncFunctionFailure> g_urma("urma_0635");

bool Urma0635UrmaBindJettyAsyncFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0636", "urma_0637", "urma_0638"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0635UrmaBindJettyAsyncFunctionFailure::GetName() const
{
    return "urma_bind_jetty_async 函数故障";
}

std::string Urma0635UrmaBindJettyAsyncFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0635UrmaBindJettyAsyncFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0635UrmaBindJettyAsyncFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0635UrmaBindJettyAsyncFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0635UrmaBindJettyAsyncFunctionFailure::GetId() const
{
    return "urma_0635";
}
} // namespace diag
