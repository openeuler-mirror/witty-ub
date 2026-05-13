#include "urma_0076_bondp_add_jetty_p_vjetty_id_info_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0076BondpAddJettyPVjettyIdInfoFunctionFailure> g_urma("urma_0076");

bool Urma0076BondpAddJettyPVjettyIdInfoFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0077"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0076BondpAddJettyPVjettyIdInfoFunctionFailure::GetName() const
{
    return "bondp_add_jetty_p_vjetty_id_info 函数故障";
}

std::string Urma0076BondpAddJettyPVjettyIdInfoFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0076BondpAddJettyPVjettyIdInfoFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0076BondpAddJettyPVjettyIdInfoFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0076BondpAddJettyPVjettyIdInfoFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0076BondpAddJettyPVjettyIdInfoFunctionFailure::GetId() const
{
    return "urma_0076";
}
} // namespace diag
