#include "urma_0151_bondp_delete_pjfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0151BondpDeletePjfsFunctionFailure> g_urma("urma_0151");

bool Urma0151BondpDeletePjfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0152"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0151BondpDeletePjfsFunctionFailure::GetName() const
{
    return "bondp_delete_pjfs 函数故障";
}

std::string Urma0151BondpDeletePjfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0151BondpDeletePjfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0151BondpDeletePjfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0151BondpDeletePjfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0151BondpDeletePjfsFunctionFailure::GetId() const
{
    return "urma_0151";
}
} // namespace diag
