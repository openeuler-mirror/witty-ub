#include "urma_0845_urma_unadvise_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0845UrmaUnadviseJettyFunctionFailure> g_urma("urma_0845");

bool Urma0845UrmaUnadviseJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0846", "urma_0847"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0845UrmaUnadviseJettyFunctionFailure::GetName() const
{
    return "urma_unadvise_jetty 函数故障";
}

std::string Urma0845UrmaUnadviseJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0845UrmaUnadviseJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0845UrmaUnadviseJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0845UrmaUnadviseJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0845UrmaUnadviseJettyFunctionFailure::GetId() const
{
    return "urma_0845";
}
} // namespace diag
