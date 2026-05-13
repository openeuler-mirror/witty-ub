#include "urma_0820_urma_set_jetty_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0820UrmaSetJettyOptFunctionFailure> g_urma("urma_0820");

bool Urma0820UrmaSetJettyOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0821", "urma_0822", "urma_0823", "urma_0824",
                                                    "urma_0825", "urma_0826", "urma_0827"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0820UrmaSetJettyOptFunctionFailure::GetName() const
{
    return "urma_set_jetty_opt 函数故障";
}

std::string Urma0820UrmaSetJettyOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0820UrmaSetJettyOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0820UrmaSetJettyOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0820UrmaSetJettyOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0820UrmaSetJettyOptFunctionFailure::GetId() const
{
    return "urma_0820";
}
} // namespace diag
