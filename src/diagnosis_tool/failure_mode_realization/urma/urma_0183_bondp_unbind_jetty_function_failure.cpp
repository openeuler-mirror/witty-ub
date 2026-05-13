#include "urma_0183_bondp_unbind_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0183BondpUnbindJettyFunctionFailure> g_urma("urma_0183");

bool Urma0183BondpUnbindJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0184", "urma_0185"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0183BondpUnbindJettyFunctionFailure::GetName() const
{
    return "bondp_unbind_jetty 函数故障";
}

std::string Urma0183BondpUnbindJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0183BondpUnbindJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0183BondpUnbindJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0183BondpUnbindJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0183BondpUnbindJettyFunctionFailure::GetId() const
{
    return "urma_0183";
}
} // namespace diag
