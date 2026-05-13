#include "urma_0398_urma_cmd_deactive_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0398UrmaCmdDeactiveJettyFunctionFailure> g_urma("urma_0398");

bool Urma0398UrmaCmdDeactiveJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0399", "urma_0400"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0398UrmaCmdDeactiveJettyFunctionFailure::GetName() const
{
    return "urma_cmd_deactive_jetty 函数故障";
}

std::string Urma0398UrmaCmdDeactiveJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0398UrmaCmdDeactiveJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0398UrmaCmdDeactiveJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0398UrmaCmdDeactiveJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0398UrmaCmdDeactiveJettyFunctionFailure::GetId() const
{
    return "urma_0398";
}
} // namespace diag
