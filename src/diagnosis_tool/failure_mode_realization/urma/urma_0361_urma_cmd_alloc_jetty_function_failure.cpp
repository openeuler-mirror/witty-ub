#include "urma_0361_urma_cmd_alloc_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0361UrmaCmdAllocJettyFunctionFailure> g_urma("urma_0361");

bool Urma0361UrmaCmdAllocJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0362", "urma_0363", "urma_0364"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0361UrmaCmdAllocJettyFunctionFailure::GetName() const
{
    return "urma_cmd_alloc_jetty 函数故障";
}

std::string Urma0361UrmaCmdAllocJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0361UrmaCmdAllocJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0361UrmaCmdAllocJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0361UrmaCmdAllocJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0361UrmaCmdAllocJettyFunctionFailure::GetId() const
{
    return "urma_0361";
}
} // namespace diag
