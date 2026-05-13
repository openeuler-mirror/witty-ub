#include "urma_0601_urma_add_jetty_grp_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0601UrmaAddJettyGrpFunctionFailure> g_urma("urma_0601");

bool Urma0601UrmaAddJettyGrpFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0602"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0601UrmaAddJettyGrpFunctionFailure::GetName() const
{
    return "urma_add_jetty_to_jetty_grp 函数故障";
}

std::string Urma0601UrmaAddJettyGrpFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0601UrmaAddJettyGrpFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0601UrmaAddJettyGrpFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0601UrmaAddJettyGrpFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0601UrmaAddJettyGrpFunctionFailure::GetId() const
{
    return "urma_0601";
}
} // namespace diag
