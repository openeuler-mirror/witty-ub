#include "urma_0211_bondp_delete_comp_jfce_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0211BondpDeleteCompJfceFunctionFailure> g_urma("urma_0211");

bool Urma0211BondpDeleteCompJfceFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0212"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0211BondpDeleteCompJfceFunctionFailure::GetName() const
{
    return "bondp_delete_comp_jfce 函数故障";
}

std::string Urma0211BondpDeleteCompJfceFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0211BondpDeleteCompJfceFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0211BondpDeleteCompJfceFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0211BondpDeleteCompJfceFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0211BondpDeleteCompJfceFunctionFailure::GetId() const
{
    return "urma_0211";
}
} // namespace diag
