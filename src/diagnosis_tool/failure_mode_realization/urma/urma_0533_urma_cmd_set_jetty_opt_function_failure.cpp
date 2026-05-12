#include "urma_0533_urma_cmd_set_jetty_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0533UrmaCmdSetJettyOptFunctionFailure> g_urma("urma_0533");

bool Urma0533UrmaCmdSetJettyOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0534", "urma_0535", "urma_0536", "urma_0537",
                                                    "urma_0538", "urma_0539", "urma_0540"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0533UrmaCmdSetJettyOptFunctionFailure::GetName() const
{
    return "urma_cmd_set_jetty_opt 函数故障";
}

std::string Urma0533UrmaCmdSetJettyOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0533UrmaCmdSetJettyOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0533UrmaCmdSetJettyOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0533UrmaCmdSetJettyOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0533UrmaCmdSetJettyOptFunctionFailure::GetId() const
{
    return "urma_0533";
}
} // namespace diag
