#include "urma_0563_urma_cmd_unbind_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0563UrmaCmdUnbindJettyFunctionFailure> g_urma("urma_0563");

bool Urma0563UrmaCmdUnbindJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0564"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0563UrmaCmdUnbindJettyFunctionFailure::GetName() const
{
    return "urma_cmd_unbind_jetty 函数故障";
}

std::string Urma0563UrmaCmdUnbindJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0563UrmaCmdUnbindJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0563UrmaCmdUnbindJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0563UrmaCmdUnbindJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0563UrmaCmdUnbindJettyFunctionFailure::GetId() const
{
    return "urma_0563";
}
} // namespace diag
