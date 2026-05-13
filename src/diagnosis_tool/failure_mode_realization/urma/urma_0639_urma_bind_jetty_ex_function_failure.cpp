#include "urma_0639_urma_bind_jetty_ex_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0639UrmaBindJettyExFunctionFailure> g_urma("urma_0639");

bool Urma0639UrmaBindJettyExFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0640", "urma_0641", "urma_0642"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0639UrmaBindJettyExFunctionFailure::GetName() const
{
    return "urma_bind_jetty_ex 函数故障";
}

std::string Urma0639UrmaBindJettyExFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0639UrmaBindJettyExFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0639UrmaBindJettyExFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0639UrmaBindJettyExFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0639UrmaBindJettyExFunctionFailure::GetId() const
{
    return "urma_0639";
}
} // namespace diag
