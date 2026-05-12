#include "urma_1052_bondp_delete_comp_default_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1052BondpDeleteCompDefaultFunctionFailure> g_urma("urma_1052");

bool Urma1052BondpDeleteCompDefaultFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1053", "urma_1054"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1052BondpDeleteCompDefaultFunctionFailure::GetName() const
{
    return "bondp_delete_comp_default 函数故障";
}

std::string Urma1052BondpDeleteCompDefaultFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1052BondpDeleteCompDefaultFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1052BondpDeleteCompDefaultFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1052BondpDeleteCompDefaultFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1052BondpDeleteCompDefaultFunctionFailure::GetId() const
{
    return "urma_1052";
}
} // namespace diag
