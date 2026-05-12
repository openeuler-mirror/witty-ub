#include "urma_0380_urma_cmd_create_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0380UrmaCmdCreateJettyFunctionFailure> g_urma("urma_0380");

bool Urma0380UrmaCmdCreateJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0381", "urma_0382", "urma_0383"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0380UrmaCmdCreateJettyFunctionFailure::GetName() const
{
    return "urma_cmd_create_jetty 函数故障";
}

std::string Urma0380UrmaCmdCreateJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0380UrmaCmdCreateJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0380UrmaCmdCreateJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0380UrmaCmdCreateJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0380UrmaCmdCreateJettyFunctionFailure::GetId() const
{
    return "urma_0380";
}
} // namespace diag
