#include "urma_0117_bondp_create_pjfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0117BondpCreatePjfsFunctionFailure> g_urma("urma_0117");

bool Urma0117BondpCreatePjfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0118"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0117BondpCreatePjfsFunctionFailure::GetName() const
{
    return "bondp_create_pjfs 函数故障";
}

std::string Urma0117BondpCreatePjfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0117BondpCreatePjfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0117BondpCreatePjfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0117BondpCreatePjfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0117BondpCreatePjfsFunctionFailure::GetId() const
{
    return "urma_0117";
}
} // namespace diag
