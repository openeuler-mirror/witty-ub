#include "urma_0685_urma_deactive_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0685UrmaDeactiveJettyFunctionFailure> g_urma("urma_0685");

bool Urma0685UrmaDeactiveJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0686", "urma_0687", "urma_0688"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0685UrmaDeactiveJettyFunctionFailure::GetName() const
{
    return "urma_deactive_jetty 函数故障";
}

std::string Urma0685UrmaDeactiveJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0685UrmaDeactiveJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0685UrmaDeactiveJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0685UrmaDeactiveJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0685UrmaDeactiveJettyFunctionFailure::GetId() const
{
    return "urma_0685";
}
} // namespace diag
