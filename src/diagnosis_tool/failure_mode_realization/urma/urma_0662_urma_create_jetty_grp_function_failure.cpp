#include "urma_0662_urma_create_jetty_grp_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0662UrmaCreateJettyGrpFunctionFailure> g_urma("urma_0662");

bool Urma0662UrmaCreateJettyGrpFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0663", "urma_0664", "urma_0665", "urma_0666", "urma_0667"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0662UrmaCreateJettyGrpFunctionFailure::GetName() const
{
    return "urma_create_jetty_grp 函数故障";
}

std::string Urma0662UrmaCreateJettyGrpFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0662UrmaCreateJettyGrpFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0662UrmaCreateJettyGrpFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0662UrmaCreateJettyGrpFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0662UrmaCreateJettyGrpFunctionFailure::GetId() const
{
    return "urma_0662";
}
} // namespace diag
