#include "urma_0578_urma_active_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0578UrmaActiveJettyFunctionFailure> g_urma("urma_0578");

bool Urma0578UrmaActiveJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0579", "urma_0580", "urma_0581",
                                                    "urma_0582", "urma_0583", "urma_0584"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0578UrmaActiveJettyFunctionFailure::GetName() const
{
    return "urma_active_jetty 函数故障";
}

std::string Urma0578UrmaActiveJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0578UrmaActiveJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0578UrmaActiveJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0578UrmaActiveJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0578UrmaActiveJettyFunctionFailure::GetId() const
{
    return "urma_0578";
}
} // namespace diag
