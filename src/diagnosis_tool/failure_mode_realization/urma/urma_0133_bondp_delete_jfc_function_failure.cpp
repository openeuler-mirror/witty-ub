#include "urma_0133_bondp_delete_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0133BondpDeleteJfcFunctionFailure> g_urma("urma_0133");

bool Urma0133BondpDeleteJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0134", "urma_0135", "urma_0136"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0133BondpDeleteJfcFunctionFailure::GetName() const
{
    return "bondp_delete_jfc 函数故障";
}

std::string Urma0133BondpDeleteJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0133BondpDeleteJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0133BondpDeleteJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0133BondpDeleteJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0133BondpDeleteJfcFunctionFailure::GetId() const
{
    return "urma_0133";
}
} // namespace diag
