#include "urma_0630_urma_bind_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0630UrmaBindJettyFunctionFailure> g_urma("urma_0630");

bool Urma0630UrmaBindJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0631", "urma_0632", "urma_0633", "urma_0634"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0630UrmaBindJettyFunctionFailure::GetName() const
{
    return "urma_bind_jetty 函数故障";
}

std::string Urma0630UrmaBindJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0630UrmaBindJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0630UrmaBindJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0630UrmaBindJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0630UrmaBindJettyFunctionFailure::GetId() const
{
    return "urma_0630";
}
} // namespace diag
