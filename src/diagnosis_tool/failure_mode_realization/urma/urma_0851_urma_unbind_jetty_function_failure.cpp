#include "urma_0851_urma_unbind_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0851UrmaUnbindJettyFunctionFailure> g_urma("urma_0851");

bool Urma0851UrmaUnbindJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0852", "urma_0853"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0851UrmaUnbindJettyFunctionFailure::GetName() const
{
    return "urma_unbind_jetty 函数故障";
}

std::string Urma0851UrmaUnbindJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0851UrmaUnbindJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0851UrmaUnbindJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0851UrmaUnbindJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0851UrmaUnbindJettyFunctionFailure::GetId() const
{
    return "urma_0851";
}
} // namespace diag
