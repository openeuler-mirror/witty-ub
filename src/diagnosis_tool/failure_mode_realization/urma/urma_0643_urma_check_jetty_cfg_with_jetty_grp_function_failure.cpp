#include "urma_0643_urma_check_jetty_cfg_with_jetty_grp_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0643UrmaCheckJettyCfgWithJettyGrpFunctionFailure> g_urma("urma_0643");

bool Urma0643UrmaCheckJettyCfgWithJettyGrpFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0644", "urma_0645"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0643UrmaCheckJettyCfgWithJettyGrpFunctionFailure::GetName() const
{
    return "urma_check_jetty_cfg_with_jetty_grp 函数故障";
}

std::string Urma0643UrmaCheckJettyCfgWithJettyGrpFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0643UrmaCheckJettyCfgWithJettyGrpFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0643UrmaCheckJettyCfgWithJettyGrpFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0643UrmaCheckJettyCfgWithJettyGrpFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0643UrmaCheckJettyCfgWithJettyGrpFunctionFailure::GetId() const
{
    return "urma_0643";
}
} // namespace diag
