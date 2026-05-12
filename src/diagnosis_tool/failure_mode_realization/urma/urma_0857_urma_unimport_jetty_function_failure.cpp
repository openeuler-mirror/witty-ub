#include "urma_0857_urma_unimport_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0857UrmaUnimportJettyFunctionFailure> g_urma("urma_0857");

bool Urma0857UrmaUnimportJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0858"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0857UrmaUnimportJettyFunctionFailure::GetName() const
{
    return "urma_unimport_jetty 函数故障";
}

std::string Urma0857UrmaUnimportJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0857UrmaUnimportJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0857UrmaUnimportJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0857UrmaUnimportJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0857UrmaUnimportJettyFunctionFailure::GetId() const
{
    return "urma_0857";
}
} // namespace diag
