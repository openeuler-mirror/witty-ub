#include "urma_0559_urma_cmd_unadvise_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0559UrmaCmdUnadviseJettyFunctionFailure> g_urma("urma_0559");

bool Urma0559UrmaCmdUnadviseJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0560"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0559UrmaCmdUnadviseJettyFunctionFailure::GetName() const
{
    return "urma_cmd_unadvise_jetty 函数故障";
}

std::string Urma0559UrmaCmdUnadviseJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0559UrmaCmdUnadviseJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0559UrmaCmdUnadviseJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0559UrmaCmdUnadviseJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0559UrmaCmdUnadviseJettyFunctionFailure::GetId() const
{
    return "urma_0559";
}
} // namespace diag
