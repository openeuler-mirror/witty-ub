#include "urma_1182_bondp_user_ctl_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1182BondpUserCtlFunctionFailure> g_urma("urma_1182");

bool Urma1182BondpUserCtlFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1183", "urma_1184"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1182BondpUserCtlFunctionFailure::GetName() const
{
    return "bondp_user_ctl 函数故障";
}

std::string Urma1182BondpUserCtlFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1182BondpUserCtlFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1182BondpUserCtlFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1182BondpUserCtlFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1182BondpUserCtlFunctionFailure::GetId() const
{
    return "urma_1182";
}
} // namespace diag
