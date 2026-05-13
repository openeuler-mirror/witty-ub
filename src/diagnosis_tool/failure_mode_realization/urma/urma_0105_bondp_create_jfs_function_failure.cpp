#include "urma_0105_bondp_create_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0105BondpCreateJfsFunctionFailure> g_urma("urma_0105");

bool Urma0105BondpCreateJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0106", "urma_0107", "urma_0108",
                                                    "urma_0109", "urma_0110", "urma_0111"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0105BondpCreateJfsFunctionFailure::GetName() const
{
    return "bondp_create_jfs 函数故障";
}

std::string Urma0105BondpCreateJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0105BondpCreateJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0105BondpCreateJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0105BondpCreateJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0105BondpCreateJfsFunctionFailure::GetId() const
{
    return "urma_0105";
}
} // namespace diag
