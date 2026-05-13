#include "urma_0190_bondp_wait_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0190BondpWaitJfcFunctionFailure> g_urma("urma_0190");

bool Urma0190BondpWaitJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0191", "urma_0192", "urma_0193"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0190BondpWaitJfcFunctionFailure::GetName() const
{
    return "bondp_wait_jfc 函数故障";
}

std::string Urma0190BondpWaitJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0190BondpWaitJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0190BondpWaitJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0190BondpWaitJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0190BondpWaitJfcFunctionFailure::GetId() const
{
    return "urma_0190";
}
} // namespace diag
