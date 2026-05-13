#include "urma_0143_bondp_delete_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0143BondpDeleteJfsFunctionFailure> g_urma("urma_0143");

bool Urma0143BondpDeleteJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0144", "urma_0145", "urma_0146"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0143BondpDeleteJfsFunctionFailure::GetName() const
{
    return "bondp_delete_jfs 函数故障";
}

std::string Urma0143BondpDeleteJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0143BondpDeleteJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0143BondpDeleteJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0143BondpDeleteJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0143BondpDeleteJfsFunctionFailure::GetId() const
{
    return "urma_0143";
}
} // namespace diag
