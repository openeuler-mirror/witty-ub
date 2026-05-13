#include "urma_0264_restore_cr_local_id_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0264RestoreCrLocalIdFunctionFailure> g_urma("urma_0264");

bool Urma0264RestoreCrLocalIdFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0265"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0264RestoreCrLocalIdFunctionFailure::GetName() const
{
    return "restore_cr_local_id 函数故障";
}

std::string Urma0264RestoreCrLocalIdFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0264RestoreCrLocalIdFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0264RestoreCrLocalIdFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0264RestoreCrLocalIdFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0264RestoreCrLocalIdFunctionFailure::GetId() const
{
    return "urma_0264";
}
} // namespace diag
