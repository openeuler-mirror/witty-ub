#include "urma_0713_urma_delete_jetty_grp_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0713UrmaDeleteJettyGrpFunctionFailure> g_urma("urma_0713");

bool Urma0713UrmaDeleteJettyGrpFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0714", "urma_0715", "urma_0716"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0713UrmaDeleteJettyGrpFunctionFailure::GetName() const
{
    return "urma_delete_jetty_grp 函数故障";
}

std::string Urma0713UrmaDeleteJettyGrpFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0713UrmaDeleteJettyGrpFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0713UrmaDeleteJettyGrpFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0713UrmaDeleteJettyGrpFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0713UrmaDeleteJettyGrpFunctionFailure::GetId() const
{
    return "urma_0713";
}
} // namespace diag
