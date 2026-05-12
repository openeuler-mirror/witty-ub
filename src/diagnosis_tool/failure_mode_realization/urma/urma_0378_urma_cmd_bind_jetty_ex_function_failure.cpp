#include "urma_0378_urma_cmd_bind_jetty_ex_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0378UrmaCmdBindJettyExFunctionFailure> g_urma("urma_0378");

bool Urma0378UrmaCmdBindJettyExFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0379"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0378UrmaCmdBindJettyExFunctionFailure::GetName() const
{
    return "urma_cmd_bind_jetty_ex 函数故障";
}

std::string Urma0378UrmaCmdBindJettyExFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0378UrmaCmdBindJettyExFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0378UrmaCmdBindJettyExFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0378UrmaCmdBindJettyExFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0378UrmaCmdBindJettyExFunctionFailure::GetId() const
{
    return "urma_0378";
}
} // namespace diag
