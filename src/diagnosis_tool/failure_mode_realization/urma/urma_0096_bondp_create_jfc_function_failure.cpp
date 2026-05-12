#include "urma_0096_bondp_create_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0096BondpCreateJfcFunctionFailure> g_urma("urma_0096");

bool Urma0096BondpCreateJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0097", "urma_0098"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0096BondpCreateJfcFunctionFailure::GetName() const
{
    return "bondp_create_jfc 函数故障";
}

std::string Urma0096BondpCreateJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0096BondpCreateJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0096BondpCreateJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0096BondpCreateJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0096BondpCreateJfcFunctionFailure::GetId() const
{
    return "urma_0096";
}
} // namespace diag
