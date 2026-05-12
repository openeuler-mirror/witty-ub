#include "urma_0344_urma_cmd_active_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0344UrmaCmdActiveJettyFunctionFailure> g_urma("urma_0344");

bool Urma0344UrmaCmdActiveJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0345", "urma_0346", "urma_0347"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0344UrmaCmdActiveJettyFunctionFailure::GetName() const
{
    return "urma_cmd_active_jetty 函数故障";
}

std::string Urma0344UrmaCmdActiveJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0344UrmaCmdActiveJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0344UrmaCmdActiveJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0344UrmaCmdActiveJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0344UrmaCmdActiveJettyFunctionFailure::GetId() const
{
    return "urma_0344";
}
} // namespace diag
