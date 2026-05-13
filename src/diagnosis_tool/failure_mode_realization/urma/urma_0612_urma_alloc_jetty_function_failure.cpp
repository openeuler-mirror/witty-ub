#include "urma_0612_urma_alloc_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0612UrmaAllocJettyFunctionFailure> g_urma("urma_0612");

bool Urma0612UrmaAllocJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0613", "urma_0614", "urma_0615", "urma_0616", "urma_0617"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0612UrmaAllocJettyFunctionFailure::GetName() const
{
    return "urma_alloc_jetty 函数故障";
}

std::string Urma0612UrmaAllocJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0612UrmaAllocJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0612UrmaAllocJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0612UrmaAllocJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0612UrmaAllocJettyFunctionFailure::GetId() const
{
    return "urma_0612";
}
} // namespace diag
