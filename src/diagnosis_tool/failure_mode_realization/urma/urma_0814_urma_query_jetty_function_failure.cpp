#include "urma_0814_urma_query_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0814UrmaQueryJettyFunctionFailure> g_urma("urma_0814");

bool Urma0814UrmaQueryJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0815"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0814UrmaQueryJettyFunctionFailure::GetName() const
{
    return "urma_query_jetty 函数故障";
}

std::string Urma0814UrmaQueryJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0814UrmaQueryJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0814UrmaQueryJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0814UrmaQueryJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0814UrmaQueryJettyFunctionFailure::GetId() const
{
    return "urma_0814";
}
} // namespace diag
