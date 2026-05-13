#include "urma_0286_set_jfs_wr_ptseg_ptjetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0286SetJfsWrPtsegPtjettyFunctionFailure> g_urma("urma_0286");

bool Urma0286SetJfsWrPtsegPtjettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0287"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0286SetJfsWrPtsegPtjettyFunctionFailure::GetName() const
{
    return "set_jfs_wr_ptseg_ptjetty 函数故障";
}

std::string Urma0286SetJfsWrPtsegPtjettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0286SetJfsWrPtsegPtjettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0286SetJfsWrPtsegPtjettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0286SetJfsWrPtsegPtjettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0286SetJfsWrPtsegPtjettyFunctionFailure::GetId() const
{
    return "urma_0286";
}
} // namespace diag
