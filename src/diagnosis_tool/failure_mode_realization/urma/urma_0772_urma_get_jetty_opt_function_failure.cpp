#include "urma_0772_urma_get_jetty_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0772UrmaGetJettyOptFunctionFailure> g_urma("urma_0772");

bool Urma0772UrmaGetJettyOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0773", "urma_0774"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0772UrmaGetJettyOptFunctionFailure::GetName() const
{
    return "urma_get_jetty_opt 函数故障";
}

std::string Urma0772UrmaGetJettyOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0772UrmaGetJettyOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0772UrmaGetJettyOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0772UrmaGetJettyOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0772UrmaGetJettyOptFunctionFailure::GetId() const
{
    return "urma_0772";
}
} // namespace diag
