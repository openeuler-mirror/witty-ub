#include "urma_0717_urma_delete_jetty_grp_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0717UrmaDeleteJettyGrpFunctionFailure> g_urma("urma_0717");

bool Urma0717UrmaDeleteJettyGrpFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0718"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0717UrmaDeleteJettyGrpFunctionFailure::GetName() const
{
    return "urma_delete_jetty_to_jetty_grp 函数故障";
}

std::string Urma0717UrmaDeleteJettyGrpFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0717UrmaDeleteJettyGrpFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0717UrmaDeleteJettyGrpFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0717UrmaDeleteJettyGrpFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0717UrmaDeleteJettyGrpFunctionFailure::GetId() const
{
    return "urma_0717";
}
} // namespace diag
