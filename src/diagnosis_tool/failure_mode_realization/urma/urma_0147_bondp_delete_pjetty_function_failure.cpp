#include "urma_0147_bondp_delete_pjetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0147BondpDeletePjettyFunctionFailure> g_urma("urma_0147");

bool Urma0147BondpDeletePjettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0148"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0147BondpDeletePjettyFunctionFailure::GetName() const
{
    return "bondp_delete_pjetty 函数故障";
}

std::string Urma0147BondpDeletePjettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0147BondpDeletePjettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0147BondpDeletePjettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0147BondpDeletePjettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0147BondpDeletePjettyFunctionFailure::GetId() const
{
    return "urma_0147";
}
} // namespace diag
