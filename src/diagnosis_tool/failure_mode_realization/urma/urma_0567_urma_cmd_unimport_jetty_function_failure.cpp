#include "urma_0567_urma_cmd_unimport_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0567UrmaCmdUnimportJettyFunctionFailure> g_urma("urma_0567");

bool Urma0567UrmaCmdUnimportJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0568"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0567UrmaCmdUnimportJettyFunctionFailure::GetName() const
{
    return "urma_cmd_unimport_jetty 函数故障";
}

std::string Urma0567UrmaCmdUnimportJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0567UrmaCmdUnimportJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0567UrmaCmdUnimportJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0567UrmaCmdUnimportJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0567UrmaCmdUnimportJettyFunctionFailure::GetId() const
{
    return "urma_0567";
}
} // namespace diag
