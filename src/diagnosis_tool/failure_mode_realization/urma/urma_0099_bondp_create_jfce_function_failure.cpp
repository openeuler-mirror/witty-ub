#include "urma_0099_bondp_create_jfce_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0099BondpCreateJfceFunctionFailure> g_urma("urma_0099");

bool Urma0099BondpCreateJfceFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0100"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0099BondpCreateJfceFunctionFailure::GetName() const
{
    return "bondp_create_jfce 函数故障";
}

std::string Urma0099BondpCreateJfceFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0099BondpCreateJfceFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0099BondpCreateJfceFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0099BondpCreateJfceFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0099BondpCreateJfceFunctionFailure::GetId() const
{
    return "urma_0099";
}
} // namespace diag
