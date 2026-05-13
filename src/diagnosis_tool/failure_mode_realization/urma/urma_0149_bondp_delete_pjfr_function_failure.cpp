#include "urma_0149_bondp_delete_pjfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0149BondpDeletePjfrFunctionFailure> g_urma("urma_0149");

bool Urma0149BondpDeletePjfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0150"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0149BondpDeletePjfrFunctionFailure::GetName() const
{
    return "bondp_delete_pjfr 函数故障";
}

std::string Urma0149BondpDeletePjfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0149BondpDeletePjfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0149BondpDeletePjfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0149BondpDeletePjfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0149BondpDeletePjfrFunctionFailure::GetId() const
{
    return "urma_0149";
}
} // namespace diag
