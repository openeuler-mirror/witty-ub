#include "urma_0137_bondp_delete_jfce_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0137BondpDeleteJfceFunctionFailure> g_urma("urma_0137");

bool Urma0137BondpDeleteJfceFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0138"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0137BondpDeleteJfceFunctionFailure::GetName() const
{
    return "bondp_delete_jfce 函数故障";
}

std::string Urma0137BondpDeleteJfceFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0137BondpDeleteJfceFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0137BondpDeleteJfceFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0137BondpDeleteJfceFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0137BondpDeleteJfceFunctionFailure::GetId() const
{
    return "urma_0137";
}
} // namespace diag
