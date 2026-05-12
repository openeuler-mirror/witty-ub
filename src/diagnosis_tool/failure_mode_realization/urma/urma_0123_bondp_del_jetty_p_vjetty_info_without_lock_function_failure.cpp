#include "urma_0123_bondp_del_jetty_p_vjetty_info_without_lock_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0123BondpDelJettyPVjettyInfoWithoutLockFunctionFailure> g_urma("urma_0123");

bool Urma0123BondpDelJettyPVjettyInfoWithoutLockFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0124"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0123BondpDelJettyPVjettyInfoWithoutLockFunctionFailure::GetName() const
{
    return "bondp_del_jetty_p_vjetty_info_without_lock 函数故障";
}

std::string Urma0123BondpDelJettyPVjettyInfoWithoutLockFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0123BondpDelJettyPVjettyInfoWithoutLockFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0123BondpDelJettyPVjettyInfoWithoutLockFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0123BondpDelJettyPVjettyInfoWithoutLockFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0123BondpDelJettyPVjettyInfoWithoutLockFunctionFailure::GetId() const
{
    return "urma_0123";
}
} // namespace diag
