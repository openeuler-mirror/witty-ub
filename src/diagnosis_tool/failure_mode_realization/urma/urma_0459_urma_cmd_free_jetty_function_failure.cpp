#include "urma_0459_urma_cmd_free_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0459UrmaCmdFreeJettyFunctionFailure> g_urma("urma_0459");

bool Urma0459UrmaCmdFreeJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0460", "urma_0461"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0459UrmaCmdFreeJettyFunctionFailure::GetName() const
{
    return "urma_cmd_free_jetty 函数故障";
}

std::string Urma0459UrmaCmdFreeJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0459UrmaCmdFreeJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0459UrmaCmdFreeJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0459UrmaCmdFreeJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0459UrmaCmdFreeJettyFunctionFailure::GetId() const
{
    return "urma_0459";
}
} // namespace diag
