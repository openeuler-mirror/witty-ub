#include "urma_1131_bondp_unregister_seg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1131BondpUnregisterSegFunctionFailure> g_urma("urma_1131");

bool Urma1131BondpUnregisterSegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1132", "urma_1133", "urma_1134"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1131BondpUnregisterSegFunctionFailure::GetName() const
{
    return "bondp_unregister_seg 函数故障";
}

std::string Urma1131BondpUnregisterSegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1131BondpUnregisterSegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1131BondpUnregisterSegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1131BondpUnregisterSegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1131BondpUnregisterSegFunctionFailure::GetId() const
{
    return "urma_1131";
}
} // namespace diag
