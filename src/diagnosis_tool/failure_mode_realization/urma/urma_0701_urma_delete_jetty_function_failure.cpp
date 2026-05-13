#include "urma_0701_urma_delete_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0701UrmaDeleteJettyFunctionFailure> g_urma("urma_0701");

bool Urma0701UrmaDeleteJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0702", "urma_0703", "urma_0704", "urma_0705"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0701UrmaDeleteJettyFunctionFailure::GetName() const
{
    return "urma_delete_jetty 函数故障";
}

std::string Urma0701UrmaDeleteJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0701UrmaDeleteJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0701UrmaDeleteJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0701UrmaDeleteJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0701UrmaDeleteJettyFunctionFailure::GetId() const
{
    return "urma_0701";
}
} // namespace diag
