#include "urma_0323_deepcopy_jfs_wr_inner_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0323DeepcopyJfsWrInnerFunctionFailure> g_urma("urma_0323");

bool Urma0323DeepcopyJfsWrInnerFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0324", "urma_0325"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0323DeepcopyJfsWrInnerFunctionFailure::GetName() const
{
    return "deepcopy_jfs_wr_inner 函数故障";
}

std::string Urma0323DeepcopyJfsWrInnerFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0323DeepcopyJfsWrInnerFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0323DeepcopyJfsWrInnerFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0323DeepcopyJfsWrInnerFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0323DeepcopyJfsWrInnerFunctionFailure::GetId() const
{
    return "urma_0323";
}
} // namespace diag
