#include "urma_0121_bondp_create_vjfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0121BondpCreateVjfsFunctionFailure> g_urma("urma_0121");

bool Urma0121BondpCreateVjfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0122"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0121BondpCreateVjfsFunctionFailure::GetName() const
{
    return "bondp_create_vjfs 函数故障";
}

std::string Urma0121BondpCreateVjfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0121BondpCreateVjfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0121BondpCreateVjfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0121BondpCreateVjfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0121BondpCreateVjfsFunctionFailure::GetId() const
{
    return "urma_0121";
}
} // namespace diag
